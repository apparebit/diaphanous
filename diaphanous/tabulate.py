from argparse import ArgumentParser
from collections.abc import Iterator, Sequence
import datetime as dt
from io import StringIO
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, cast, Literal, Self

import altair as alt
import great_tables as gt
import polars as pl

from .chart import (
    plot_cdf_grid, plot_crime_rate_by_age, plot_sex_by_age_grid, plot_sex_by_age_detailed
)
from .color import Palette
from .mosaic import (
    make_contingencies,  make_mosaic_frame, plot_mosaic_grid, compute_odds_ratios,
    plot_odds_ratio_grid, test_chi2_independence,
)
from .nibrs.model import Id
from .nibrs.reader import analyze_offender_anomalies, combine_offenders_and_arrestees
from .platform.data import REPORTS_PER_PLATFORM
from .util import compute_age_cdfs

import diaphanous.aunz as aunz
import diaphanous.de as de
import diaphanous.crimestat as crimestat
import diaphanous.nibrs as nibrs


_INDEX = ("source", "target", "year")
_METRICS = ("pieces", "reports")


def tabulate() -> pl.DataFrame:
    """
    Ingest the platform data from the `diaphanous.platform.data` module into a
    single tidy data frame.

    The frame has columns for the `source` organization, the  `target`
    organization, and the `year`, which serve as index, as well as `variable`
    and `value`, which contain the counts of `pieces` and `reports`. It
    aggregates the two metrics by corporation and year, including an observation
    only if at least one brand has disclosed the metric for the full year
    through any combination of yearly, semiannual, or quarterly disclosures.
    Rows marked as redundant are ignored.
    """
    frames = []

    for platform, data in cast(Iterator[tuple[str, Any]], REPORTS_PER_PLATFORM.items()):
        if platform == "@" or data is None or data.get("rows") is None:
            continue

        frame = _ingest_frame(platform, data["rows"], data["columns"])
        frame = _extract_pieces_and_reports(frame, data.get("sums", {}))
        if not _is_empty(frame):
            frames.append(frame)

    return _merge_frames(frames)


def _ingest_frame(
    platform: str,
    rows: Sequence[Any],
    column_names: Sequence[str],
) -> pl.DataFrame:
    """
    Convert the per-platform row and column data into a data frame.

    This function prefixes the raw row data with columns for the `source` and
    `target` organizations—i.e., twice the platform name for data originating
    with platforms and `"NCMEC"` and the platform name for data originating from
    NCMEC—as well as the `year` and `period` derived from the row label.

    This function ignores rows marked as redundant.
    """
    is_ncmec = platform == "NCMEC"
    just_rows = []

    for row in rows:
        if row.get("redundant"):
            continue
        (label,) = row.keys()

        if is_ncmec:
            just_rows.append([
                platform,
                row[label][0],
                *_to_year_and_period(label),
                *row[label][1:],
            ])
        else:
            just_rows.append([
                platform,
                platform,
                *_to_year_and_period(label),
                *row[label],
            ])

    if is_ncmec:
        column_names = column_names[1:]

    return pl.DataFrame(
        [*zip(*just_rows)], [*_INDEX, "period", *column_names]
    )


_Period = Literal["Q1", "Q2", "Q3", "Q4", "H1", "H2", "Y1"]

def _to_year_and_period(label: str) -> tuple[int, _Period]:
    """Convert a row label into year and period."""
    length = len(label)
    if length == 4:
        return int(label), "Y1"

    assert length == 7
    return int(label[:4]), cast(_Period, label[5:])


def _extract_pieces_and_reports(
    frame: pl.DataFrame,
    sums: dict[str, Sequence[str]]
) -> pl.DataFrame:
    """
    Convert the data frame with the row and column data into a data frame with
    just the pieces and reports.
    """
    exprs = []

    for metric in _METRICS:
        if metric in sums:
            exprs.append(_add_if_non_null(sums[metric]).alias(metric))
        elif metric in frame.columns:
            exprs.append(pl.col(metric).cast(pl.Int64))
        else:
            exprs.append(
                pl.lit(None, dtype=pl.Int64).alias(metric)
            )

    return frame.select(pl.col(*_INDEX, "period"), *exprs)


def _add_if_non_null(columns: Sequence[str]) -> pl.Expr:
    """
    Build a Pola.rs expression that, for each row, adds the non-null values in
    the given columns. A row's result is null only if all values in the row also
    are null.
    """
    cond = pl.col(columns[0]).is_null()
    for column in columns[1:]:
        cond = cond.and_(pl.col(column).is_null())

    return pl.when(
        cond
    ).then(
        pl.lit(None, dtype=pl.Int64)
    ).otherwise(
        pl.sum_horizontal(*columns).cast(pl.Int64)
    )


def _is_empty(frame: pl.DataFrame) -> bool:
    """
    Determine whether the data frame contains any non-null values for pieces or
    reports.
    """
    piece_count, report_count = frame.select(
        *(pl.col(metric).is_not_null().sum() for metric in _METRICS),
    ).row(0)
    return piece_count + report_count == 0


def _merge_frames(frames: Sequence[pl.DataFrame]) -> pl.DataFrame:
    """Merge per-platform frames and aggregate full years."""
    replacements = _extract_replacements()

    return pl.concat(frames).lazy().with_columns(
        pl.col("source").replace(replacements),
        pl.col("target").replace(replacements),
    ).group_by(
        pl.col(*_INDEX)
    ).agg(
        *(_sum_if_whole_year(metric) for metric in _METRICS)
    ).unpivot(
        on=_METRICS,
        index=_INDEX,
    ).sort(
        *_INDEX, "variable"
    ).filter(
        pl.col("value").is_not_null()
    ).collect()


def _extract_replacements() -> dict[str, str]:
    """Build a mapping from brands to their platforms."""
    replacements = {"Alphabet": "Google", "YouTube": "Google"}

    for platform, data in cast(Iterator[tuple[str, Any]], REPORTS_PER_PLATFORM.items()):
        if platform in ("@", "Alphabet") or data is None:
            continue

        for aka in data.get("aka", []):
            replacements[aka] = platform
        for brand in data.get("brands", []):
            replacements[brand] = platform

    return replacements


def _sum_if_whole_year(metric: str) -> pl.Expr:
    """
    Build Pola.rs expression that sums up the metric column if the rows cover an
    entire year. This function assumes that the data has been grouped by year.
    """
    return pl.when(
        # Consider only rows with non-null values
        pl.when(
            pl.col(metric).is_not_null()
        ).then(
            pl.col("period").replace_strict({
                    "Y1": 0b1111,
                    "H1": 0b0011,
                    "H2": 0b1100,
                    "Q1": 0b0001,
                    "Q2": 0b0010,
                    "Q3": 0b0100,
                    "Q4": 0b1000,
                },
                return_dtype=pl.Int8,
            )
        ).otherwise(
            pl.lit(0, dtype=pl.Int8)
        ).bitwise_or().eq(0b1111)
    ).then(
        pl.col(metric).sum()
    ).otherwise(
        pl.lit(None, dtype=pl.Int64)
    )

# ======================================================================================

HEIGHT_ATTR = re.compile(r'height="\d+[a-z]*"')
WIDTH_ATTR = re.compile(r'width="\d+[a-z]*"')
XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>'

class Analyzer:

    def __init__(
        self,
        path: str | Path,
        with_icc: bool = False,
        with_reports: bool = False,
        with_platforms: bool = False,
        with_crimes: bool = False,
    ) -> None:
        self._path = Path(path)
        self._file: Any = None
        self._data = tabulate()
        self._diffs = _distill_differences(self._data)
        self._with_icc = with_icc
        self._figure_count = 0
        self._secno = [0, 0, 0]
        self._with_reports = with_reports
        self._with_platforms = with_platforms
        self._with_crimes = with_crimes

    def has_content(self) -> bool:
        return self._with_reports or self._with_platforms or self._with_crimes

    def __enter__(self) -> Self:
        if not self.has_content():
            raise ValueError("nothing to report")
        self._file = open(self._path, mode="w", encoding="utf8")
        self._file.write(_HEAD)
        return self

    def __exit__(self, _, __, ___) -> None:
        self._file.write("</main>\n</body>\n")
        self._file.close()
        self._file = None

    def run(self) -> None:
        if self._file is None:
            raise ValueError("invoke `run()` in `with Analyzer():` block only")

        if self._with_reports:
            self.h2("A Decade of Seemingly Linear Growth")
            self.emit_regression_models()

        if self._with_platforms:
            self.h2("Platforms' vs NCMEC's Disclosures")

            self.html("""
                <p>The analysis assumes that counting errors accumulate with the
                magnitude of counts. Hence, for each pair of report counts
                disclosed by a platform and NCMEC, the difference of report
                counts is scaled by the mean of report counts, resulting in
                Δ%.</p>
            """)

            self.h3("The Data")
            diffs = self._diffs.sort(
                pl.col("pct_diff"), descending=True
            )

            self.html(f"""
                <ul>
                <li>{len(self._diffs.select(
                    pl.col("platform").unique()
                ))} out of {len(self._data.select(
                    pl.col("target").unique()
                )) - 2} surveyed platforms make necessary disclosures
                </li><li>{len(self._diffs)} data pairs
                    <ul>
                    <li>{len(self._diffs.filter(pl.col("pct_diff").abs().le(0.20)))}
                        differ by less than 20%
                    <li>{len(self._diffs.filter(pl.col("pct_diff").abs().le(0.10)))}
                        differ by less than 10%
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").abs().le(0.01)))}
                        differ by less than 1%
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().eq(0)))}
                        with no difference
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().gt(0)))}
                        positive differences
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().lt(0)))}
                        negative differences
                    </li><li>{self._diffs.select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.3f}%
                        mean difference
                    </li><li>{diffs.tail(-1).select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.3f}% mean difference, discounting top 1 outlier
                    </li><li><strong>{diffs.tail(-2).select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.3f}% mean difference, discounting top 2 outliers
                    </strong></li><li>{diffs.tail(-3).select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.3f}% mean difference, discounting top 3 outliers
                    </li></ul></li>
                </ul>
            """)

            comparison = juxtapose(self._data)
            self.html(
                format_juxtaposition(comparison, with_highlights=True).as_raw_html()
            )
            self._see_path()

            fig = plot_reports_per_provider()
            path = "figure/reports-per-provider.svg"
            fig.save(path)
            self.svg(path)

            self.h3("A Histogram of Percent Differences")
            self.chart(
                alt.Chart(
                    self._diffs.with_columns(
                        pl.col("pct_diff").mul(100)
                    )
                ).mark_bar().encode(
                    alt.X("pct_diff:Q", bin=alt.Bin(step=10)),
                    alt.Y("count()"),
                ).properties(
                    width=500,
                )
            )
            self._see_path()

            self.h3("Mean Difference Plots")
            self.emit_mean_difference_plots()

            if self._with_icc:
                self.h3("Intraclass Correlation Coefficient")
                self.emit_icc()

            self.h3("Sign of Differences")
            self.emit_sign_test()

            self.h3("Reddit vs Other Platforms")
            self.emit_reddit_vs_others()

        if self._with_crimes:
            self.h2("Crime Statistics About CSAM")
            self.html(f"""
                <p>The following <strong>13 countries</strong> and <strong>one
                supranational organization</strong> do not appear to publish
                crime statistics that are sufficiently granular to relate
                particular offenses to age and sex of offenders:</p>

                <ul>
                <li>Brazil
                <li>Canada
                <li>Czech Republic
                <li>European Union
                <li>France
                <li>India
                <li>Japan
                <li>Mexico
                <li>Phillipines
                <li>Poland
                <li>Singapore
                <li>Thailand
                <li>United Arab Emirates
                <li>United Kingdom
                </ul>

                <p>Meanwhile the following <strong>7 countries</strong> do
                publish the data necessary for building the contingency tables
                relating offenses involving CSAM with offender age and sex:</p>

                <ul>
                <li>Australia
                <li>Finland
                <li>Germany
                <li>Italy
                <li>New Zealand
                <li>Spain
                <li>United States
                </ul>

                <p>Yearly coverage and age-group resolution differ substantially
                amongst countries. At the same time, all but Australia and Spain
                capture additional information beyond offense, offender age, and
                offender sex:</p>

                <ul>
                <li>Finland: coarse nationality of offenders
                <li>Germany: producers v consumers
                <li>Italy: Italians vs foreigners
                <li>New Zealand: ethnicity, producers v consumers
                <li>United States: ethnicity, producers v consumers
                </ul>

                <p>In fact, the United States' National Incident-Based Reporting
                System (NIBRS) goes well beyond the above listed information
                because it is the only country publishing case data instead of
                frequency data.</p>

                <p>In addition to being case-based, the United States' NIBRS
                also captures many more statistics at much finer granularity.
                Notably, age is captured in individual years from 0-99, whereas
                other countries use buckets; except for New Zealand, buckets
                have varying sizes.</p>

                <p>The chart below illustrates the age resolution for surveyed
                countries. Age ranges before the age of criminal responsibility,
                i.e., when minors are not held criminally liable, are shown in
                yellow. Age ranges between the age of criminal responsibility
                and the age of majority, i.e., when minors face limited or
                reduced criminal liability, are shown in red. Age ranges after
                the age of majority during which young adults may still be
                treated as minors are shown in purple.</p>
            """)

            self.emit_age_buckets()

            self.h3("Backfilling Suspects for Unsolved Incidents")

            stats = de.ingest_incidents().filter(
                pl.col("activity").is_not_null(),
            ).group_by(
                Id.YEAR,
            ).agg(
                pl.col("incidents", "solved", "suspects").sum()
            ).with_columns(
                pl.col("suspects").truediv(pl.col("solved")).alias("suspects_per_incident"),
            ).select(
                pl.col("suspects_per_incident").min().alias("minimum"),
                pl.col("suspects_per_incident").mean().alias("mean"),
                pl.col("suspects_per_incident").max().alias("maximum"),
            ).row(0)

            self.html(f"""
                <p>The offender statistics for Germany (and very likely also
                Finland, Italy, and Spain) are misleading in that they do not
                include incidents with unknown offenders. But accounting for
                those incidents is critical to determine to what degree offender
                demographics are representative.</p>

                <p>For <strong>Germany</strong>, the number of suspects per
                solved incident ranges from {stats[0]:.3f} to {stats[2]:.3f},
                with a mean of {stats[1]:.3f}. The reciprocal incidents per
                suspect ranges from {1/stats[2]:.3f} to {1/stats[0]:.3f}, with a
                mean of {1/stats[1]:.3f}. Assuming that this relationship also
                holds for unsolved incidents, we then backfill the suspects
                table for Germany by counting one suspect for each unsolved
                incident. Since these suspects are unknown, their age and sex
                must remain <code>null</code>. However, since Germany publishes
                incident data, just like suspect data, broken down by law, we
                can still backfill the activity, i.e., distinguish between
                consumers and producers.</p>
            """)

            self.emit_age_distributions()

        now = dt.datetime.now(dt.UTC)
        date = now.date().isoformat()
        time = now.time().isoformat("seconds")
        self.html(
            '<p style="font-size: 0.8em;"><i>This report was generated'
            f' on {date} at {time} UTC.</i></p>'
        )

    def emit_mean_difference_plots(self) -> None:
        self._runr(self._diffs.with_columns(
            pl.col("pct_diff").mul(100)
        ), """
library(tidyverse)
library(patchwork)
library(scales)

COLORS <- c(
    "2019" = "#0d067e",
    "2020" = "#470498",
    "2021" = "#7f079c",
    "2022" = "#b13688",
    "2023" = "#dd2467",
    "2024" = "#f94b3b",
    "2025" = "#fc9506"
)

format_mean_zero <- number_format()
format_mean_kilo <- number_format(scale=0.001, suffix="k")
format_mean_mega <- number_format(scale=0.000001, suffix="M")
format_mean <- function(x) {{
    dplyr::case_when(
        is.na(x) ~ "",
        x == 0 ~ format_mean_zero(x),
        x < 1000000 ~ format_mean_kilo(x),
        TRUE ~ format_mean_mega(x)
    )
}}

format_all_means <- function(xs) map(xs, format_mean)

plot_pct_diff_over_mean <- function(platform, data, all.platforms = FALSE) {{
    xmin <- min(data$mean)
    xmax <- max(data$mean)
    xrange <- ifelse(xmin == xmax, 2 * xmin, xmax - xmin)
    if (all.platforms) {{
        xlimits <- c(xmin - 50, xmax + 0.05 * xrange)
    }} else {{
        xlimits <- c(xmin - 0.05 * xrange, xmax + 0.05 * xrange)
    }}

    ymin <- min(data$pct_diff, 0)
    ymean <- mean(data$pct_diff)
    ymax <- max(data$pct_diff)
    yrange <- ymax - ymin
    ylimits <- c(ymin - 0.05 * yrange, ymax + 0.05 * yrange)

    graph <- ggplot(data = data, aes(x = mean, y = pct_diff, color = year)) +
        geom_hline(yintercept = 0) +
        geom_hline(yintercept = ymean, linetype = "dashed") +
        geom_point(size=2.5) +
        ylim(ylimits) +
        xlab(ifelse(all.platforms, "log(Mean of Report Counts)", "Mean of Report Counts")) +
        ylab("Δ%(Report Counts)") +
        labs(title = platform)

    if (platform == "Reddit") {{
        # Reddit is the only provider with data for all seven years.
        # Hence we enable the legend for this graph.
        graph <- graph + scale_color_manual(values = COLORS, name = "Year")
    }} else {{
        graph <- graph + scale_color_manual(guide = "none", values = COLORS)
    }}

    graph <- graph + scale_x_continuous(
        labels = format_all_means,
        transform = ifelse(all.platforms, 'log10', 'identity'),
        limits = xlimits,
    )

    graph <- graph + theme_light() + theme(
        axis.title.y = element_text(
            face = "italic",
            margin = margin(t = 0, r = 10, b = 0, l = 0)
        ),
        axis.title.x = element_text(
            face = "italic",
            margin = margin(t = 10, r = 0, b = 0, l = 0)
        )
    )
    return(graph)
}}

difference.data <- read.csv(text = "{CSV_DATA}")
platforms <- unique(difference.data$platform)
plots <- vector("list", length(platforms) + 1)

index <- 0
for (platform.name in platforms) {{
    index <- index + 1
    plots[[index]] <- plot_pct_diff_over_mean(
        platform.name,
        difference.data |>
            filter(platform == platform.name) |>
            mutate(year = as.character(year))
    )
}}

plots[[length(platforms) + 1]] <- plot_pct_diff_over_mean(
    "All Platforms",
    difference.data |> mutate(year = as.character(year)),
    all.platforms = TRUE
)

design <- "AABBCCDDEE
           FFGGHHIIJJ
           #KKKKKKKK#"

plot.grid <- wrap_plots(
    plots,
    ncol=10,
    guides="collect",
    design=design,
    axis_titles = "collect"
)
ggsave("figure/comparable-reports.svg", plot.grid, width=11, height=7)
printr()
        """)
        self.svg(
            Path("figure/comparable-reports.svg"),
            "Percentage Differences vs Mean Differences"
        )

    def emit_icc(self) -> None:
        print("This may take a while...")
        frame = self._diffs.select(
            pl.col("provider").alias("y"),
            pl.format("{}{}", pl.col("platform"), pl.col("year")).alias("id"),
            pl.lit("platform", dtype=pl.String).alias("observer"),
        ).vstack(
            self._diffs.select(
                pl.col("ncmec").alias("y"),
                pl.format("{}{}", pl.col("platform"), pl.col("year")).alias("id"),
                pl.lit("ncmec", dtype=pl.String).alias("observer"),
            )
        )

        self._runr(frame, """
library(iccCounts)
library(ggplot2)

data <- read.csv(text="{CSV_DATA}")
data.icc <- icc_counts(
    data,
    y="y",
    id="id",
    met="observer",
    type="con",
    fam="nbinom2"
)
printr(ICC(data.icc))
printr(VarComp(data.icc))

data.gof <- GOF_check(data.icc)
printr(DispersionTest(data.gof))

data.plot <- data.gof$plot_env + geom_point(size=2) + theme_linedraw()
ggsave("figure/comparable-reports-icc-gof.svg", data.plot)
        """)

        self.svg(
            "figure/comparable-reports-icc-gof.svg",
            caption="Goodness of Fit"
        )

    def emit_reddit_vs_others(self) -> None:
        counts = self._diffs.select(
            pl.when(
                pl.col("diff").eq(0)
            ).then(
                pl.lit("yes")
            ).otherwise(
                pl.lit("no")
            ).alias("matches"),
            pl.when(
                pl.col("platform").eq("Reddit")
            ).then(
                pl.lit("Reddit")
            ).otherwise(
                pl.lit("Other")
            ).alias("platform")
        ).group_by(
            "platform", "matches"
        ).agg(
            pl.len().alias("count")
        ).sort(
            "platform", "matches", descending=True
        ).select(
            pl.col("count")
        )

        self._runr(counts, """
dt.ftable <- data.frame(
    platform = c("Reddit", "Reddit", "Other", "Other"),
    has_match = c("yes", "no", "yes", "no"),
    freq = c({VECTOR_DATA})
)
dt.contab <- xtabs(freq ~ platform + has_match, data = dt.ftable)
printr(fisher.test(dt.contab))
        """)

    def emit_sign_test(self) -> None:
        counts = self._diffs.select(
            pl.col("diff").sign()
        ).group_by(
            pl.col("diff")
        ).agg(
            pl.len()
        ).filter(
            pl.col("diff").ne(0)
        ).select(
            pl.col("diff").alias("sign"),
            pl.col("len").alias("count"),
        ).sort(
            pl.col("sign"), descending=True
        ).select(
            pl.col("count")
        )

        self._runr(counts, """
result <- binom.test(
    c({VECTOR_DATA}),
    p = 0.5,
    alternative = "two.sided",
)
printr(result)
        """)

    def emit_regression_models(self) -> None:
        frame = pl.read_csv("data/ocse-reports-per-year.csv").filter(
            pl.col("year").ge(2014).and_(pl.col("year").lt(2024))
        ).join(
            pl.read_csv("data/social-accounts.csv"),
            on="year",
            how="left",
        )

        self.h3("Poisson Regression")
        self._runr(frame, """
data <- read.csv(text="{CSV_DATA}")

data.poisson <- glm(reports ~ year, family = "poisson", data = data)
printr(data.poisson)
printr(confint(data.poisson))
printr(exp(confint(data.poisson)))

svg("figure/mod-poisson.svg")
par(mfrow = c(3, 2))
plot(data.poisson, which = 1:6)
dev.off()
        """)

        self.svg("figure/mod-poisson.svg")

        self.h3("Negative Binomial Regression")
        self._runr(frame, """
library(MASS)
data <- read.csv(text="{CSV_DATA}")
data.nbinom <- glm.nb(reports ~ year, data = data)

printr(data.nbinom)
printr(confint(data.nbinom))
printr(exp(confint(data.nbinom)))

svg("figure/mod-nbinom.svg")
par(mfrow = c(3, 2))
plot(data.nbinom, which = 1:6)
dev.off()
        """)

        self.svg("figure/mod-nbinom.svg")

    def emit_mosaics(self) -> None:
        self.h3("Australia")
        frame = aunz.au_age_distribution().collect().group_by(
            "data_year", "age_group", "sex", maintain_order=True,
        ).agg(
            pl.col("count").sum()
        )

        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
au.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(age_group = factor(age_group, levels=c("Juvenile", "Adult")))
au.contab <- xtabs(count ~ age_group + sex, data = au.yearly)
print(au.contab)

svg(paste0("figure/au-age-sex-2022-23.svg"))
vcd::mosaic(
    ~ age_group + sex,
    data = au.contab,
    direction = c("v", "h"),
    shade = TRUE,
    margins = c(2.5, 0.3, 0, 2.5),
    main = paste0("Offenders by Sex and Age (Australia, 2022/23)")
)
dev.off()
printr()
        """)
        self.col(2)
        self.svg("figure/au-age-sex-2022-23.svg")
        self.end_col()

        self.h3("Germany")
        frame = de.de_age_distribution().collect().group_by(
            "data_year", "age_group", "sex", "activity", maintain_order=True
        ).agg(
            pl.col("count").sum()
        )
        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
de.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(age_group = factor(age_group, levels=c("Child", "Juvenile", "Adult")))

for (year in 2023:2024) {{
    de.data <- de.yearly |> filter(data_year == year)

    de.contab <- xtabs(count ~ age_group + sex, data = de.data)
    print(de.contab)
    svg(paste0("figure/de-age-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + sex,
        data = de.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Sex and Age (Germany, ", year, ")")
    )
    dev.off()

    de.contab <- xtabs(count ~ age_group + activity, data = de.data)
    print(de.contab)
    svg(paste0("figure/de-age-activity-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + activity,
        data = de.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Age and Activity (Germany, ", year, ")")
    )
    dev.off()
}}
printr()
        """)
        self.col(2)
        self.svg("figure/de-age-sex-2023.svg")
        self.svg("figure/de-age-sex-2024.svg")
        self.end_col()

        self.hr()

        self.col(2)
        self.svg("figure/de-age-activity-2023.svg")
        self.svg("figure/de-age-activity-2024.svg")
        self.end_col()

        self.h3("New Zealand")
        frame = aunz.nz_age_distribution().collect().drop_nulls(
            ["age_group", "sex"]
        ).group_by(
            "data_year", "age_group", "sex", "activity", maintain_order=True
        ).agg(
            pl.col("count").sum()
        )
        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
nz.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(age_group = factor(age_group, levels=c("Juvenile", "Adult")))

for (year in 2023:2024) {{
    nz.data <- nz.yearly |> filter(data_year == year)
    nz.contab <- xtabs(count ~ age_group + sex, data = nz.data)
    print(nz.contab)

    svg(paste0("figure/nz-age-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + sex,
        data = nz.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Sex and Age (New Zealand, ", year, ")")
    )
    dev.off()

    nz.contab <- xtabs(count ~ age_group + activity, data = nz.data)
    print(nz.contab)
    svg(paste0("figure/nz-age-activity-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + activity,
        data = nz.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Age and Activity (New Zealand, ", year, ")")
    )
    dev.off()
}}
printr()
        """)
        self.col(2)
        self.svg("figure/nz-age-sex-2023.svg")
        self.svg("figure/nz-age-sex-2024.svg")
        self.end_col()

        self.hr()

        self.col(2)
        self.svg("figure/nz-age-activity-2023.svg")
        self.svg("figure/nz-age-activity-2024.svg")
        self.end_col()

        self.h3("Spain")
        frame = crimestat.es_age_distribution().collect().group_by(
            pl.col("data_year", "age_group", "sex")
        ).agg(
            pl.col("count").sum()
        )
        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
es.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(age_group = factor(age_group, levels=c("Juvenile", "Adult")))

for (year in 2023:2024) {{
    es.data <- es.yearly |> filter(data_year == year)
    es.contab <- xtabs(count ~ age_group + sex, data = es.data)
    print(es.contab)

    svg(paste0("figure/es-age-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + sex,
        data = es.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Sex and Age (Spain, ", year, ")")
    )
    dev.off()
}}
printr()
        """)
        self.col(2)
        self.svg("figure/es-age-sex-2023.svg")
        self.svg("figure/es-age-sex-2024.svg")
        self.end_col()

        self.h3("United States")
        frame = nibrs.us_age_distributions().filter(
            pl.col("metric").eq("United States CSAM Offenders")
        )
        frame = frame.drop_nulls(
            ["age_group", "sex"],
        ).group_by(
            "data_year", "age_group", "ethnicity", "sex", "activity",
            maintain_order=True
        ).agg(
            pl.col("count").sum()
        )
        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
us.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(
        age_group = factor(age_group, levels=c("Child", "Juvenile", "Adult")),
        ethnicity = factor(ethnicity, levels=c("White", "Black", "Hispanic", "Other"))
    )

for (year in 2023:2024) {{
    us.data <- us.yearly |> filter(data_year == year)

    us.contab <- xtabs(count ~ age_group + sex, data = us.data)
    print(us.contab)
    svg(paste0("figure/us-age-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + sex,
        data = us.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Sex and Age (United States, ", year, ")")
    )
    dev.off()

    us.contab <- xtabs(count ~ age_group + ethnicity + sex, data = us.data)
    print(us.contab)
    svg(paste0("figure/us-age-race-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + ethnicity + sex, data = us.contab, direction = c("v", "h", "v"),
        shade = TRUE,
        main = paste0("Offenders by Sex, Race, and Age (United States, ", year, ")"),
        rot_labels = c(0, 0, 45, 0),
        offset_labels = c(0, 0, -0.5, -0.5),
        just_labels = c("center", "left", "right", "right"),
        offset_varnames = c(0.2, 0, 0.2, 0.2),
        margins = c(3, 0.3, 3, 4)
    )
    dev.off()

    us.contab <- xtabs(count ~ age_group + activity, data = us.data)
    print(us.contab)
    svg(paste0("figure/us-age-activity-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + activity,
        data = us.contab,
        direction = c("v", "h"),
        shade = TRUE,
        margins = c(2.5, 0.3, 0, 2.5),
        main = paste0("Offenders by Age and Activity (United States, ", year, ")")
    )
    dev.off()
}}
printr()
        """)
        self.col(2)
        self.svg("figure/us-age-sex-2023.svg")
        self.svg("figure/us-age-sex-2024.svg")
        self.end_col()

        self.hr()

        self.col(2)
        self.svg("figure/us-age-race-sex-2023.svg")
        self.svg("figure/us-age-race-sex-2024.svg")
        self.end_col()

        self.hr()

        self.col(2)
        self.svg("figure/us-age-activity-2023.svg")
        self.svg("figure/us-age-activity-2024.svg")
        self.end_col()

    DETAIL_YEARS = (2021, 2024)
    THUMB_YEARS = (2015, 2025)
    THUMB_GAP = 20
    THUMB_WIDTH = 3_000

    def filter_years(
        self, distributions: dict[str, pl.DataFrame], first: int, last: int
    ) -> dict[str, pl.DataFrame]:
        filtered = {}
        for key in distributions:
            filtered[key] = distributions[key].filter(
                pl.col("data_year").ge(first).and_(pl.col("data_year").le(last))
            )
        return filtered

    def emit_age_distribution_detail(self) -> None:
        self.html("<div class=wide>\n")
        self.h3("Age Distribution of Offenders: The Last Two Years")

        distributions = crimestat.load_all_age_distributions(verbose=True)
        data = self.filter_years(distributions, *self.DETAIL_YEARS)

        fig = alt.vconcat(
            plot_sex_by_age_detailed(data["au"], "Australia", "CSAM", "Offender"),
            plot_sex_by_age_detailed(data["fi"], "Finland", "CSAM", "Suspect"),
            plot_sex_by_age_detailed(data["de"], "Germany", "CSAM", "Suspect"),
            plot_sex_by_age_detailed(data["it"], "Italy", "CSAM", "Offender"),
            plot_sex_by_age_detailed(data["nz"], "New Zealand", "CSAM", "Offenders"),
            plot_sex_by_age_detailed(data["es"], "Spain", "CSAM", "Suspect"),
            plot_sex_by_age_detailed(
                data["us_csam_offenders"], "United States", "CSAM", "Offender"),
            plot_sex_by_age_detailed(
                data["us_csam_arrestees"], "United States", "CSAM", "Arrestee"),
            plot_sex_by_age_detailed(
                data["us_porn_offenders"], "United States", "Porn", "Offender"),
            plot_sex_by_age_detailed(
                data["us_porn_arrestees"], "United States", "Porn", "Arrestee"),
        ).resolve_scale(x="shared")

        path = "figure/age-distributions.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

    def emit_age_distributions(self, with_chi2: bool = False) -> None:
        self.h3("Perpetrators by Country, Year, Sex, and Age")
        self.h4("Suspect Age Distributions")

        distributions = crimestat.load_all_age_distributions(verbose=True)
        full_data = pl.concat(
            self.filter_years(distributions, *self.THUMB_YEARS).values()
        )

        # All distributions
        self.html("<div class=extra-wide>\n")
        fig = plot_sex_by_age_grid(full_data)
        path = "figure/age-sex-pyramids.svg"
        fig.save(path)
        self.svg(path)

        # Understanding the surprisingly high prevalence of 58-year-old
        # offenders without a known sex
        self.h4("United States: 58-Year-Old CSAM Offenders Without Known Sex")

        detail_data = self.filter_years(distributions, *self.DETAIL_YEARS)
        fig = plot_sex_by_age_detailed(
            detail_data["us_csam_offenders"], "US", "CSAM", "Offender"
        )
        path = "figure/us-age-sex-detail.svg"
        fig.save(path)
        self.svg(path)

        agencies, age_ranges = analyze_offender_anomalies()

        agency_count = agencies.select(
            pl.col("count").sum()
        ).item()
        top_agency = agencies.select(
            pl.col("agency").first()
        ).item()
        top_share = agencies.select(
            pl.col("fraction").first().mul(100)
        ).item()

        def apply_style(table: gt.GT) -> gt.GT:
            return table.tab_style(
            style=gt.style.text(size="small"),
            locations=gt.loc.body(),
        ).tab_style(
            style=gt.style.text(size="small", weight="bold"),
            locations=gt.loc.column_labels(),
        ).tab_style(
            style=gt.style.text(size="medium"),
            locations=gt.loc.title(),
        ).opt_vertical_padding(
            scale=0.8,
        )

        age_ranges_display = apply_style(gt.GT(age_ranges).tab_header(
            title="Age Ranges Reducing to 58-Years-Old",
        ).cols_label(
            min_age="Min Age",
            max_age="Max Age",
            trunc_mean_age="Truncated Mean Age",
            count="Count",
        ).fmt_integer(
            columns=[
                "min_age",
                "max_age",
                "trunc_mean_age",
                "count"],
            sep_mark=",",
        ))

        self.html(f"""
            </div>

            <p>In the above, enlarged age distributions for CSAM offenders in
            the United States, the number of 58-year-old offenders with unknown
            sex is rather noticeable. Over a span of four years, there are
            {agency_count:,} of them. When looking at the reporting police
            departments, the agency recording the most is {top_agency} with
            {top_share:.1f}%. Besides that one agency, the distribution is
            heavy-tailed, with a total of {len(agencies):,} different
            departments.</p>

            <p>A closer look at the complete offender table reveals that these
            agencies did not code the age of an unknown offender as unavailable.
            Instead, they abused an age range covering (almost) all adult years,
            even though age ranges should cover at most 10 years. The different
            ranges are shown below.</p>

            {age_ranges_display.as_raw_html()}

            <div class=extra-wide>
        """)

        # Mosaics I: Highlight minors
        self.h4("Sex Ratios Amongst Minors and Adults")
        frame = make_mosaic_frame(
            full_data,
            x_axis="age_group",
            y_axis="sex",
            index={
                "age_group": ["Minor", None, "Adult"],
                "sex": ["Female", None, "Male"],
            },
            highlights={
                "Minor": {
                    "Male": Palette.LIGHT_BLUE,
                    "Female": Palette.PINK,
                },
            },
            use_minor=True,
            include_null=True,
            show_counts=True,
            show_percent=True,
        )

        fig = plot_mosaic_grid(
            frame,
            x_label="Age Group",
            y_label="Sex",
            # subtitle=(
            #     "Male and female minors are shown in blue and red (respectively), "
            #     "people with unknown age or sex in light gray, and those with unknown "
            #     "sex and age in white."
            # ),
        )
        path = "figure/age-sex-mosaics.svg"
        fig.save(path)
        self.svg(path)

        # Mosaics II: Highlight large residuals
        if with_chi2:
            frame = make_mosaic_frame(
                full_data,
                x_axis="age_group",
                y_axis="sex",
                index={"age_group": ["Minor", None, "Adult"]},
                use_residuals=True,
                use_minor=True,
                include_null=True,
                show_counts=True,
            )

            frame = test_chi2_independence(
                frame,
                x_axis="age_group",
                y_axis="sex",
                x_order="x_order",
                y_order="y_order",
            )

            fig = plot_mosaic_grid(
                frame,
                x_label="Age Group",
                y_label="Sex",
                # subtitle=(
                #     "Male and female minors are shown in blue and red (respectively), "
                #     "people with unknown age or sex in light gray, and those with unknown "
                #     "sex and age in white."
                # ),
            )
            path = "figure/age-sex-residual-mosaics.svg"
            fig.save(path)
            self.svg(path)

        fig = plot_odds_ratio_grid(
            compute_odds_ratios(
                full_data.with_columns(
                    pl.col("sex_order").mul(-1)
                ),
                "age_group",
                "sex",
                x_order="age_group_order",
                y_order="sex_order",
                use_minor=True
            )
        )
        path = "figure/age-sex-odds-ratios.svg"
        fig.save(path)
        self.svg(path)

        cdfs = compute_age_cdfs(full_data)
        fig = plot_cdf_grid(cdfs)
        path = "figure/age-sex-cdfs.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

        self.html("<div class=wide>\n")
        self.emit_contingency_tables(
            full_data,
            x_axis="age_group",
            y_axis="sex",
            index={
                "age_group": ["Minor", None, "Adult"],
                "sex": ["Male", None, "Female"],
            },
            include_null=True,
            use_minor=True,
        )
        self.html("</div>\n")

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        self.h3("Perpetrators by Country, Year, Activity, and Age Group")
        self.html("<div class=extra-wide>\n")

        activity_data = full_data.filter(
            pl.col("metric").is_in([
                "Germany CSAM Offenders",
                "New Zealand CSAM Offenders",
                "United States CSAM Offenders",
                "United States CSAM Arrestees",
            ])
        )

        frame = make_mosaic_frame(
            activity_data,
            x_axis="age_group",
            y_axis="activity",
            index={
                "age_group": ["Minor", None, "Adult"],
                "activity": ["Producer", None, "Consumer"],
            },
            highlights={
                "Minor": {
                    "Producer": Palette.RED,
                    "Consumer": Palette.ORANGE,
                },
            },
            use_minor=True,
            include_null=True,
            show_counts=True,
            show_percent=True,
        )

        fig = plot_mosaic_grid(
            frame,
            x_label="Age Group",
            y_label="Activity",
        )
        path = "figure/age-activity-mosaics.svg"
        fig.save(path)
        self.svg(path)

        fig = plot_odds_ratio_grid(
            compute_odds_ratios(
                activity_data.with_columns(
                    pl.col("activity_order").mul(-1)
                ),
                "age_group",
                "activity",
                x_order="age_group_order",
                y_order="activity_order",
                use_minor=True,
            ),
            second_variable="Activity",
        )
        path = "figure/age-activity-odds-ratios.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

        self.html("<div class=wide>\n")
        self.emit_contingency_tables(
            activity_data,
            x_axis="age_group",
            y_axis="activity",
            index={
                "age_group": ["Minor", None, "Adult"],
                "activity": ["Consumer", None, "Producer"],
            },
            include_null=True,
            use_minor=True,
        )
        self.html("</div>\n")

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        self.h3("Outcomes in Germany and the US")
        self.html("""
            <p>This section approximates outcomes for both Germany and the
            US.</p>

            <p>For <strong>Germany</strong>, it uses separate statistics about
            prosecutions, <a
            href="https://www.statistischebibliothek.de/mir/receive/DESerie_mods_00000107">one
            until and including 2021</a> and <a
            href="https://www.statistischebibliothek.de/mir/receive/DESerie_mods_00008081">the
            other starting with 2022</a>, released by Germany's federal
            statistics agency. That data distinguishes between
            <em>adjudications</em>, which include all formal proceedings
            including prosecutors dismissing charges, and <em>convictions</em>,
            which include educational measures, disciplinary measures, and jail
            for minors based on Germany's three-tier juvenile justice
            system.</p>

            <p>The integration of this data is based on the assumption that
            police-recorded incidents and statistics-agency-recorded
            prosecutions coincide within the same year. That assumption is not
            entirely realistic and may distort shifts in the agressiveness of
            prosecutions over time. Alas, it is necessary without additional
            information.</p>

            <p>For the <strong>United States</strong>, it uses the arrestee
            table of NIBRS.</p>

            <p><strong>Independent of country</strong>, this section partitions
            offenders into three age groups based on Germany's ages of criminal
            responsibility and majority:</p>

            <dl>
            <dt>Children</dt>
            <dd>younger than 14</dd>
            <dt>Juveniles</dt>
            <dd>at least 14 and younger than 18</dd>
            <dt>Adults</dt>
            <dd>at least 18</dd>
            </dl>

            <p>When combining tables, the default outcome for offenders, even
            for those with null attributes, is <em>No Sanction</em> (and not
            null).</p>
        """)

        de_outcomes = de.ingest_outcomes()
        de_outcomes = de.combine_offenders_and_outcomes(
            full_data, de_outcomes
        ).filter(
            # TODO: Remove when outcomes data for 2025 in Germany becomes available
            pl.col("data_year").le(2024)
        )
        de_highlights: dict[str | None, str] = {
            "No Sanction": Palette.GREEN,
            "Adjudication": Palette.ORANGE,
            "Conviction": Palette.RED,
        }
        de_frame = make_mosaic_frame(
            de_outcomes,
            x_axis="age_group",
            y_axis="outcome",
            index={
                "age_group": ["Child", "Juvenile", None, "Adult"],
                "outcome": [
                    "No Sanction", None, "Adjudication", "Conviction"
                ],
            },
            highlights={
                "Child": de_highlights,
                "Juvenile": de_highlights,
            },
            include_null=True,
        )

        us_outcomes = combine_offenders_and_arrestees(full_data)
        us_highlights: dict[str | None, str] = {
            "No Sanction": Palette.GREEN,
            "Arrest": Palette.ORANGE,
        }
        us_frame = make_mosaic_frame(
            us_outcomes,
            x_axis="age_group",
            y_axis="outcome",
            index={
                "age_group": ["Child", "Juvenile", None, "Adult"],
                "outcome": [
                    "No Sanction", None, "Arrest"
                ],
            },
            highlights={
                "Child": us_highlights,
                "Juvenile": us_highlights,
            },
            include_null=True,
        )

        # self.html("<div class=extra-wide>\n")

        # fig = plot_mosaic_grid(
        #     de_frame,
        #     x_label="Age Group",
        #     y_label="Outcome",
        # )
        # path = "figure/de-age-outcome-mosaics.svg"
        # fig.save(path)
        # self.svg(path)

        # fig = plot_mosaic_grid(
        #     us_frame,
        #     x_label="Age Group",
        #     y_label="Outcome",
        # )
        # path = "figure/us-age-outcome-mosaics.svg"
        # fig.save(path)
        # self.svg(path)

        # self.html("</div>\n")

        fig = plot_mosaic_grid(
            de_frame,
            x_label="Age Group",
            y_label="Outcome",
            narrow_rows=True,
        )
        path = "figure/de-age-outcome-mosaics-narrow.svg"
        fig.save(path)
        self.svg(path)

        fig = plot_mosaic_grid(
            us_frame,
            x_label="Age Group",
            y_label="Outcome",
            narrow_rows=True,
        )
        path = "figure/us-age-outcome-mosaics-narrow.svg"
        fig.save(path)
        self.svg(path)

        self.html("<div class=wide>\n")
        self.emit_contingency_tables(
            de_outcomes,
            x_axis="age_group",
            y_axis="outcome",
            index={
                "age_group": ["Child", "Juvenile", None, "Adult"],
                "outcome": ["Conviction", "Adjudication", None, "No Sanction"],
            },
            include_null=True,
        )
        self.emit_contingency_tables(
            us_outcomes,
            x_axis="age_group",
            y_axis="outcome",
            index={
                "age_group": ["Child", "Juvenile", None, "Adult"],
                "outcome": ["Arrest", None, "No Sanction"],
            },
            include_null=True,
        )
        self.html("</div>\n")

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        self.h3("Cross-Sectional Age-Crime-Curves for Germany and the U.S.")
        self.html("""
            <p>The age-crime-curves for Germany show offenders per 100,000
            capita for men and women based on the "<a
            href="https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/PolizeilicheKriminalstatistik/2025/Sonst_Tabellen/01-BU-BV-TVBZ-ins-ab-2009_xls.xlsx?__blob=publicationFile&v=4">Wohnbevölkerung
            insgesamt</a>," that is, total resident population, as republished
            by federal police. Since these statistics start at age 8, the
            corresponding age-crime-curves also omit ages 0 through 7. By
            definition, they also omit unresolved incidents and their
            offenders.</p>
        """)

        self.html("<div class=wide>\n")

        de_curves = de.age_crime_curves(full_data)
        fig = plot_crime_rate_by_age(de_curves, "Germany (All Offenders)")
        path = "figure/de-age-crime-curves.svg"
        fig.save(path)
        self.svg(path)

        self.html("</div>\n")

        self.html("""
            <p>Somewhat surprisingly, the age-crime-curves for German men in
            2020, 2023, and 2024 are bimodal, with a minor second peak starting
            at age 60. More generally, the normalized age distributions
            corresponding to the age-crime-curves have the following
            characteristics:</p>
        """)

        self.emit_age_crime_curve_statistics(
            de_curves,
            "Germany: Normalized Age Distributions (All Offenders)"
        )

        self.html("""
            <p><strong>TODO: Compute age-crime-curves based on offenders in
            counties, where all police agencies have been reporting statistics
            to NIBRS for entire years, and the corresponding per-county census
            estimates for population broken down by age and sex.</strong></p>
        """)

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        self.h3("German Age-Crime-Curves After Restricting Offenders")
        self.html("""
            <p>German law and crime statistics alike distinguish between child
            (0–13) and youth (14–17) pornography. We can leverage this
            distinction as a coarse indicator for victim age and combine it with
            offender age to identify two offender subgroups whose conduct may
            not rise to the same level of exploitation as for other
            offenders:</p>

            <ul>

            <li>The first subgroup are children (0–13) suspected of youth
            (14–17) pornography, since differences in age and maturity favor the
            presumed victims and get in the way of their exploitation.</li>

            <li>The second subgroup are youth (14–17) suspected of youth (14–17)
            pornography, since they come close to being peers in terms of
            age/maturity and may very well be sexting.</li>

            </ul>

            <p>The potentially huge age and maturity range of zero to thirteen
            year-olds argues against treating children (0–13) suspected of child
            (0–13) pornography as peers with their victims. Furthermore, any
            sexualization of prepubescent children seems highly
            inappropriate.</p>

            <p>When <em>omitting</em> the above two groups from offender counts
            for Germany, the age-crime-curves change substantially:</p>
        """)

        restricted_curves = de.age_crime_curves(
            de.restrict_offenders(
                de.de_age_distribution(with_material=True).collect()
            )
        )

        self.html("<div class=wide>\n")
        fig = plot_crime_rate_by_age(
            restricted_curves,
            "Germany (Restricted Offenders)"
        )
        path = "figure/de-restricted-curves.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

        self.emit_age_crime_curve_statistics(
            restricted_curves,
            "Germany: Normalized Age Distributions (Restricted Offenders)"
        )

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        self.h3("Notes")
        self.html("""
        <p>In the above age distributions, a <em>child</em> is younger than the
        <a
        href="https://en.wikipedia.org/wiki/Age_of_criminal_responsibility">age
        of criminal responsibility</a> for each jurisdiction, a
        <em>juvenile</em> has passed the age of criminal responsibility but is
        younger than the <a
        href="https://en.wikipedia.org/wiki/Age_of_majority">age of legal
        majority</a>, and an <em>adult</em> has passed the age of legal
        majority. The per-country thresholds are:</p>

        <table class=mytable>
        <thead>
        <tr><th scope=col></th><th scope=col>Age of Criminal</th><th scope=col></th></tr>
        <tr><th scope=col>Country</th>
            <th scope=col>Responsibility</th>
            <th scope=col>Age of Majority</th></tr>
        </thead>
        <tbody>
        <tr><th scope=row>Australia</th> <td>10 (Not in VIC, ACT)</td> <td>18</td></tr>
        <tr><th scope=row>Finland</th> <td>15</td> <td>18</td></tr>
        <tr><th scope=row>Germany</th> <td>14</td> <td>18</td></tr>
        <tr><th scope=row>Italy</th> <td>14</td> <td>18</td></tr>
        <tr><th scope=row>New Zealand</th> <td>10</td> <td>20</td></tr>
        <tr><th scope=row>Spain</th> <td>14</td> <td>18</td></tr>
        <tr><th scope=row>United States</th> <td>11 (Federal Law)</td> <td>18</td></tr>
        </tbody>
        </table>

        <p>Age thresholds for criminal responsibility are 12 in Victoria (VIC)
        and 14 in the Australian Capital Territory (ACT). They vary widely
        amongst U.S. states, with 24 of them not having one.</p>

        <p>The per-country data sources are:</p>
        <ul>

        <li><strong>Australia</strong>: <a
        href="https://www.aic.gov.au">Australian Institute of Criminology</a>,
        notably <a href="https://www.aic.gov.au/publications/sr/sr51">sr 51</a>

        <li><strong>Finland</strong>: Statistics Finland's <a
        href="https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__rpk/statfin_rpk_pxt_13kr.px/">StatFin
        table 13kr</a> with the "Persons suspected of solved offences by the
        International Classification of Crime for Statistical Purposes (ICCS),
        year of solving, age, sex and nationality, 2006-2024."

        <li><strong>Germany</strong>: The Bundeskriminalamt's <a
        href="https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/pks_node.html">polizeiliche
        Kriminalstatistik</a>, notably tables on suspects and incidents. Those
        statistics are supplemented with statistics about prosecutions covering
        <a
        href="https://www.statistischebibliothek.de/mir/receive/DESerie_mods_00000107">years
        up to and including 2021</a> and <a
        href="https://www.statistischebibliothek.de/mir/receive/DESerie_mods_00008081">years
        from 2022 onward</a>, released by Germany's federal
        statistics agency.

        <li><strong>Italy</strong>: Istat's table on <a
        href="https://esploradati.istat.it/databrowser/#/en/dw/categories/IT1,Z0840JUS,1.0/JUS_CRIMINAL/DCCV_AUTVITTPS/IT1,73_230_DF_DCCV_AUTVITTPS_1,1.0">alleged
        offenders reported by the police forces to the judicial authority</a>
        organized by gender, age, and citizenship.

        <li><strong>New Zealand</strong>: <a
        href="https://www.police.govt.nz/about-us/publications-statistics/data-and-statistics/policedatanz">policedata.nz</a>,
        notably <a
        href="https://www.police.govt.nz/about-us/publications-statistics/data-and-statistics/policedatanz/proceedings-offender-demographics">proceedings
        (offender demographics)</a>

        <li><strong>Spain</strong>: The Ministerio del Interior's <a
        href="https://estadisticasdecriminalidad.ses.mir.es/publico/portalestadistico/en/datos.html?type=jaxi&title=Arrests%20/%20Investigated&path=/Datos3/">annual
        series on crime</a>, arrests/investigated

        <li><strong>United States</strong>: The FBI's <a
        href="https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads#nibrs-downloads">National
        Incident-Based Reporting System (NIBRS)</a>

        </ul>

        <p>It may be nearly impossible to access Germany's police statistics
        from outside the EU, with requests simply timing out due to a likely
        network misconfiguration by that country's federal police agency.

        <p>US statisticstics are <em>not</em> representative of the entire
        country, with NIBRS' coverage of the US population growing from 35.6% in
        2014 to 86.4% in 2024 according to the FBI's <a
        href="https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend">Crime
        Data Explorer</a>.
        """)

    def emit_contingency_tables(
        self,
        data: pl.DataFrame,
        x_axis: str,
        y_axis: str,
        index: None | dict[str, Sequence[None | str]] = None,
        include_null: bool = False,
        use_minor: bool = False,
    ) -> None:
        # Prepare index
        x_class = x_axis.lower().replace("_", "-")
        y_class = y_axis.lower().replace("_", "-")

        contingencies, index = make_contingencies(
            data,
            x_axis,
            y_axis,
            include_null=include_null,
            use_minor=use_minor,
            index=index,
        )

        markup = []
        metric = None
        row_size = len(index[x_axis])

        def do_emit_cells(group, row_offset: int = 0):
            counts = (
                "&nbsp;" if c == 0 else f"{c:,}"
                for c in group.get_column("count")
            )
            fractions = (
                "&nbsp;" if f == 0 else f"({f:.1f}%)"
                for f in group.get_column("fraction")
            )

            previous_row = None
            for index, (count, fraction) in enumerate(zip(counts, fractions)):
                current_row = 1 + index // row_size + row_offset

                if current_row != previous_row:
                    if previous_row is not None:
                        markup.append("  </tr>\n")
                    markup.append(f"  <tr class=row{current_row}>\n")
                    previous_row = current_row

                markup.append(
                    f"    <td class=col{1 + index % row_size}>"
                    f"<span class=count>{count}</span>"
                    f"<span class=fraction>{fraction}</span>"
                    "</td>\n"
                )
            markup.append("  </tr>\n")

        for selectors, group in contingencies.group_by(
            "country", "material", "role", "metric", "metric_order", "data_year",
            maintain_order=True,
        ):
            # Skip years without data
            total = group.select(pl.col("total")).item(0, 0)
            if total == 0:
                continue

            # Separate different metrics
            if metric != selectors[3]:
                if metric is not None:
                    markup.append("</div>\n")
                    self.html("".join(markup))
                    markup = []

                metric = selectors[3]
                self.h4(f"Contingency Tables for {metric}")

                classes = f"{y_class}-vs-{x_class}"
                if y_class == "outcome":
                    if metric.startswith("Germany"):
                        classes += " de"
                    elif metric.startswith("United States"):
                        classes += " us"
                    else:
                        raise ValueError(f"outcome with unsupported metric {metric}")
                markup.append(
                    f'<div class="contingency-tables {classes}">\n'
                )

            # Build table
            markup.append("<table class=contingency>\n")
            markup.append(f"<caption>{selectors[5]}: N={total:,d}</caption>\n")
            markup.append("<tbody>\n")
            do_emit_cells(group)
            markup.append("</tbody>\n")

            x_group = group.group_by(
                x_axis, maintain_order=True
            ).agg(
                pl.col("count", "fraction").sum()
            )

            markup.append("<tfoot>\n")
            do_emit_cells(x_group, row_offset=3)
            markup.append("</tfoot>\n")

            markup.append("</table>\n")

        markup.append("</div>\n")
        self.html("".join(markup))

    def emit_age_crime_curve_statistics(
        self,
        data: pl.DataFrame,
        title: str,
    ) -> None:
        raw_stats = {
            "data_year": [],
            "sex": [],
            "variable": [],
            "value": [],
        }

        def record(variable: str, value: None | float | str) -> None:
            if value is None:
                v = ""
            elif isinstance(value, float):
                v = f"{value:.1f}"
            else:
                v = str(value)

            raw_stats["data_year"].append(year)
            raw_stats["sex"].append(sex)
            raw_stats["variable"].append(variable)
            raw_stats["value"].append(v)

        for (year, sex), group in data.group_by(
            pl.col(Id.YEAR, "sex"),
            maintain_order=True
        ):
            rate = group.select(
                pl.col("rate").max()
            ).item()

            if rate is None:
                record("Peak Age", None)
                record("Rate at Peak", None)
                record("First Age ≥ ½ Peak Rate", None)
                record("Last Age ≥ ½ Peak Rate", None)
            else:
                age_column = group.get_column("age")
                first_peak = age_column[
                    group.select(
                        pl.col("rate").index_of(rate)
                    ).item()
                ]

                last_peak = age_column[
                    group.select(
                        pl.col("rate").len().sub(
                            pl.col("rate").reverse().index_of(rate)
                        ).sub(1)
                    ).item()
                ]

                if first_peak == last_peak:
                    record("Peak Age", first_peak)
                else:
                    record("Peak Age", f"{first_peak}–{last_peak}")
                record("Rate at Peak", rate)

                at_least_half_peak_rate = pl.col("rate").gt(rate / 2).arg_true()
                first_half_peak = age_column[
                    group.select(at_least_half_peak_rate.first()).item()
                ]
                last_half_peak = age_column[
                    group.select(at_least_half_peak_rate.last()).item()
                ]

                record("First Age ≥ ½ Peak Rate", first_half_peak)
                record("Last Age ≥ ½ Peak Rate", last_half_peak)

            ages = group.select(
                pl.col("age").repeat_by(
                    pl.col("rate").round()
                ).explode()
            ).to_series()

            # TODO: Add 25th and 75th percentile, age at half peaks
            record("Median Age", cast(None | float, ages.median()))
            record("Mean Age", cast(None | float, ages.mean()))
            record("Stdev", cast(None | float, ages.std()))
            record("Skew", ages.skew())
            record("Kurtosis", ages.kurtosis())

        stats = pl.DataFrame(
            raw_stats,
            schema={
                "data_year": pl.Int16,
                "sex": pl.String,
                "variable": pl.String,
                "value": pl.String,
            }
        ).pivot(
            on=Id.YEAR,
            index=["sex", "variable"],
            values=["value"],
        )

        years = [str(y) for y in data.select(
            pl.col(Id.YEAR).unique()
        ).to_series()]

        self.html(
            gt.GT(
                stats
            ).tab_header(
                title=title,
            ).tab_stub(
                rowname_col="variable",
                groupname_col="sex",
            ).tab_style(
                style=gt.style.text(weight="bold"),
                locations=gt.loc.column_header(),
            ).sub_missing(
                missing_text="",
            ).cols_align(
                align="right",
                columns=years,
            ).opt_table_font(
                stack="neo-grotesque",
            ).opt_all_caps(
                locations=gt.loc.row_groups,
            ).opt_vertical_padding(
                scale=0.8,
            ).as_raw_html()
        )

    def emit_age_buckets(self) -> None:
        data = pl.read_csv("data/age-groupings.csv")

        rule_data = data.group_by(
            "country", "liability",
            maintain_order=True
        ).agg(
            pl.col("start_age").min()
        ).with_columns(
            pl.col("start_age").shift(-1, fill_value=100).over(
                pl.col("country")
            ).alias("stop_age")
        )
        tick_data = data.filter(
            pl.col("start_age").lt(100)
        )

        x = alt.X("start_age:Q").scale(domain=(0, 100)).axis(tickCount=11).title("Age")
        y = alt.Y("country:N").axis(
            ticks=False, domain=False, labelPadding=5,
        ).title(None)
        color = alt.Color("liability:N").scale(
            domain=("none", "limited", "full-or-limited", "full"),
            range=(Palette.ORANGE, Palette.RED, Palette.PURPLE, Palette.GRAY),
        ).legend(None)

        fig = (
            alt.Chart(rule_data).mark_rule(
                strokeWidth=3
            ).encode(
                x, alt.X2("stop_age:Q"), y, color
            )
            +
            alt.Chart(tick_data).mark_tick(
                thickness=1.5,
                size=12,
            ).encode(
                x, y, color
            )
        ).properties(
            width=270,
            height=120,
        )

        self.html(
            '<div style="max-width: 34em; margin-left: auto; margin-right: auto">\n'
        )
        path = "figure/age-groupings.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

    # ==================================================================================

    def hr(self) -> None:
        self.html("<hr>\n")

    def h2(self, title: str) -> None:
        self._secno[0] += 1
        self._secno[1] = 0
        self._secno[2] = 0
        secno = f"{self._secno[0]}."

        s = f"{secno} {title}"
        _print_heading(s)
        self._section(s, level=2)

    def h3(self, title: str) -> None:
        self._secno[1] += 1
        self._secno[2] = 0
        secno = f"{self._secno[0]}.{self._secno[1]}"

        s = f"{secno} {title}"
        _print_heading(s, weight="heavy")
        self._section(s, level=3)

    def h4(self, title: str) -> None:
        self._secno[2] += 1
        secno = f"{self._secno[0]}.{self._secno[1]}.{self._secno[2]}"

        s = f"{secno} {title}"
        _print_heading(s, weight="light")
        self._section(s, level=4)

    def _section(self, title: str, level: Literal[2, 3, 4] = 2) -> None:
        self.html(f"\n\n<h{level}><span>{title}</span></h{level}>\n")

    def col(self, num: int) -> None:
        self.html(
            '<div style="display: grid; grid-template-columns:'
            f'{" 1fr" * num}; gap: 2rem;">\n'
        )

    def end_col(self) -> None:
        self.html("</div>\n")

    def _runr(self, frame: pl.DataFrame, template: str, is_html: bool = False) -> None:
        fragments = _runr(frame, template)

        skip_hr = not _IS_DEBUG
        printed = False
        for fragment in fragments:
            if fragment.strip() == "":
                continue

            if not skip_hr:
                _print_heading(weight="light")
                printed = True
            skip_hr = False
            print(fragment)
            printed = True

            if is_html:
                self.html(fragment)
            else:
                self.html(f"<pre><code>\n{fragment}\n</code></pre>\n")

        if not printed:
            self._see_path()

    def html(self, html: str) -> None:
        self._file.write(html)

    def chart(self, chart: Any, caption: None | str = None) -> None:
        buffer = StringIO()
        chart.save(buffer, format="svg")
        self._figure(buffer.getvalue(), caption)

    def svg(self, path: str | Path, caption: None | str = None) -> None:
        svg = Path(path).read_text("utf8")

        # Make sure that the id attributes have, in fact, unique values by
        # prefixing them with a figure-specific marker. Otherwise, the SVGs
        # won't render correctly.
        self._figure_count += 1
        prefix = f"fig{self._figure_count}"
        svg = (
            svg
            .replace('id="', f'id="{prefix}-')
            .replace('href="#', f'href="#{prefix}-')
            .replace('url(#', f'url(#{prefix}-')
        )

        if svg.startswith(XML_DECL):
            svg = svg[len(XML_DECL):].strip()
        if svg.startswith("<svg"):
            decl, _, body = svg.partition(">")
            decl = WIDTH_ATTR.sub("", decl)
            decl = HEIGHT_ATTR.sub("", decl)
            svg = f"{decl}>{body}"

        self._figure(svg, caption)

    def _figure(self, html: str, caption: None | str = None) -> None:
        self._file.write("<figure>\n")
        self._file.write(html)
        self._file.write("\n")
        if caption is not None:
            self._file.write(f"<figcaption>{caption}</figcaption>\n")
        self._file.write("</figure>\n")

    def _see_path(self) -> None:
        print(f'See "{self._path.name}"')


def _distill_differences(pieces_and_reports: pl.DataFrame) -> pl.DataFrame:
    return pieces_and_reports.lazy().filter(
        pl.col("source").ne("NCMEC")
    ).select(
        pl.col("target", "year", "variable", "value"),
    ).join(
        pieces_and_reports.lazy().filter(
            pl.col("source").eq("NCMEC")
        ).select(
            pl.col("target", "year", "variable", "value"),
        ),
        on=["target", "year", "variable"],
        how="inner",
    ).select(
        pl.col("target").alias("platform"),
        pl.col("year"),
        pl.col("value").alias("provider"),
        pl.col("value").add(pl.col("value_right")).truediv(2).alias("mean"),
        pl.col("value_right").sub(pl.col("value")).alias("diff"),
        pl.col("value_right").alias("ncmec"),
    ).with_columns(
        pl.col("diff").truediv(pl.col("mean")).alias("pct_diff")
    ).collect()


_HEAD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>The CyberTipline Reporting System</title>

<style>
/* ----------------------------------- General ----------------------------------- */
*::before, *, *::after {
    box-sizing: inherit;
}
:root {
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, avenir next, avenir, segoe ui,
        helvetica neue, Cantarell, Ubuntu, roboto, noto, helvetica, arial, sans-serif;
    line-height: 1.5;
    --black: #1d1d20;
    --white: #f5f5f8;
    --xl: 3rem;
}
body {
    margin: var(--xl) 0.5rem;
}

svg {
    display: block;
}
.vega-embed {
    display: block !important;
}
figure {
    margin: var(--xl) 0;
}

main > * {
    max-width: 80rch;
    margin-left: auto;
    margin-right: auto;
}

main > .wide {
    max-width: 950px;
}

main > .extra-wide {
    max-width: 1200px;
}

h2, h3 {
    margin-top: var(--xl);
    max-width: none;
    margin-left: 0;
    margin-right: 0;
    background-color: #e8e8e8;
}

h2 > span, h3 > span {
    display: block;
    max-width: 80rch;
    margin-left: auto;
    margin-right: auto;
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}

h2 {
    border-bottom: 0.3rem solid #000;
}

h4 {
    margin-top: 2rem;
    border-bottom: 0.2rem solid #000;
}

figure svg {
    margin-left: auto;
    margin-right: auto;
    max-width: 100%;
}

figcaption {
    text-align: right;
    font-style: italic;
    font-weight: 500;
}

hr {
    margin-top: 3rem;
    margin-bottom: 2rem;
}

.years {
    padding-left: 0;
}

.years li {
    list-style: none;
}

.years li::before {
    content: counter(list-item) ": "
}

dt {
    font-style: italic;
}

dt::after {
    content: ": ";
    font-style: normal;
}

/* ----------------------------------- Table ----------------------------------- */

.mytable {
    border-collapse: separate;
    border-spacing: 0;
    line-height: 1.2;
    margin-top: 1.5rem;
    margin-bottom: 1.5rem;
}
.mytable caption {
    font-size: 1.2em;
    text-align: left;
    font-style: italic;
    padding: 0.45em 0;
}
.mytable caption > :where(cite, dfn, em, i) {
    font-style: normal;
}
.mytable th {
    font-weight: normal;
}
.mytable thead th {
    font-weight: bold;
}
.mytable :where(th, td) {
    padding: 0.25em 0.5em;
}
.mytable thead > tr:first-of-type {
    background: #e0e0e0;
}
.mytable thead > tr {
    background: #f0f0f0;
}
.mytable thead > tr:last-of-type > :where(th, td) {
    padding-bottom: 0.35em;
    border-bottom: solid 0.15em var(--black);
}
.mytable tbody > tr:first-of-type > :where(th, td) {
    padding-top: 0.35em;
}
.mytable tbody > tr:nth-child(even) {
    background: #f0f0f0
}
.mytable td {
    font-variant-numeric: tabular-nums;
}
.mytable :where(.left-except-2) :where(th, td) {
    text-align: left;
}
.mytable :where(.left-except-2) :where(th, td):nth-child(2) {
    text-align: right;
}
.mytable :where(.right-except-2, .right-except-2-3) :where(th, td) {
    text-align: right;
}
.mytable :where(.right-except-2, .right-except-2-3) :where(th, td):nth-child(2) {
    text-align: left;
}
.mytable :where(.right-except-2-3) :where(th, td):nth-child(3) {
    text-align: left;
}
.mytable tbody > tr.highlight > td {
    text-align: center;
}

/* ------------------------------ Contingency Tables ------------------------------ */

.contingency-tables {
    --inter-table-gap: 1em;
    --intra-table-gap: 0.3em;
    --cell-padding: 0.2em;

    --row1-col1: none;
    --row1-col2: none;
    --row1-col3: none;

    --row2-col1: none;
    --row2-col2: none;
    --row2-col3: none;

    --row3-col1: none;
    --row3-col2: none;
    --row3-col3: none;

    --row4-col1: none;
    --row4-col2: none;
    --row4-col3: none;

    display: grid;

    grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
    gap: var(--inter-table-gap);
    margin-left: auto;
    margin-right: auto;
    max-width: max-content;
}

.sex-vs-age-group, .activity-vs-age-group {
    grid-template-columns: 1fr 1fr 1fr 1fr 1fr;

    --row1-col3: #e8e8e8;
    --row3-col3: #e8e8e8;
}
.outcome-vs-age-group {
    grid-template-columns: 1fr 1fr 1fr 1fr;

    --row1-col4: #e8e8e8;
}
.outcome-vs-age-group.de {
    --row2-col4: #e8e8e8;
    --row4-col4: #e8e8e8;
}
.outcome-vs-age-group.us {
    --row3-col4: #e8e8e8;
}
.sex-vs-age-group {
    --row1-col1: #e6efff;
    --row3-col1: #ffe5ef;
}
.activity-vs-age-group {
    --row1-col1: #ffecc5;
    --row3-col1: #ffe7e3;
}
.outcome-vs-age-group.de {
    --row1-col1: #ffe6e2;
    --row1-col2: #ffe6e2;
    --row2-col1: #ffebc1;
    --row2-col2: #ffebc1;
    --row4-col1: #c2ffca;
    --row4-col2: #c2ffca;
}
.outcome-vs-age-group.us {
    --row1-col1: #ffebc1;
    --row1-col2: #ffebc1;
    --row3-col1: #c2ffca;
    --row3-col2: #c2ffca;
}

:where(.sex-vs-age-group, .activity-vs-age-group)
table.contingency {
    grid-template-columns: 1fr 1fr 1fr;
}

:where(.outcome-vs-age-group)
table.contingency {
    grid-template-columns: 1fr 1fr 1fr 1fr;
}

table.contingency {
    font-size: 0.8em;
    line-height: 1.2;
    display: grid;
    width: max-content;
}

:where(.sex-vs-age-group, .activity-vs-age-group)
table.contingency
:where(caption, tbody, tfoot) {
    grid-column: span 3;
}

:where(.outcome-vs-age-group)
table.contingency
:where(caption, tbody, tfoot) {
    grid-column: span 4;
}

table.contingency caption {
    font-style: italic;
    margin-bottom: var(--cell-padding);
}

table.contingency tbody, table.contingency tfoot {
    display: grid;
    grid-template-columns: subgrid;
    gap: var(--intra-table-gap);
}

table.contingency tbody {
    border-top: 2px solid black;
    border-bottom: 1px solid black;
}
table.contingency tfoot {
    border-bottom: 2px solid black;
}
table.contingency tr {
    display: contents;
}
table.contingency td {
    display: grid;
    grid-template-columns: subgrid;
    padding: var(--cell-padding);
}
table.contingency td > span {
    font-variant-numeric: tabular-nums;
    text-align: right;
}

table.contingency tbody .row1 .col1 { background-color: var(--row1-col1); }
table.contingency tbody .row1 .col2 { background-color: var(--row1-col2); }
table.contingency tbody .row1 .col3 { background-color: var(--row1-col3); }
table.contingency tbody .row1 .col4 { background-color: var(--row1-col4); }

table.contingency tbody .row2 .col1 { background-color: var(--row2-col1); }
table.contingency tbody .row2 .col2 { background-color: var(--row2-col2); }
table.contingency tbody .row2 .col3 { background-color: var(--row2-col3); }
table.contingency tbody .row2 .col4 { background-color: var(--row2-col4); }

table.contingency tbody .row3 .col1 { background-color: var(--row3-col1); }
table.contingency tbody .row3 .col2 { background-color: var(--row3-col2); }
table.contingency tbody .row3 .col3 { background-color: var(--row3-col3); }
table.contingency tbody .row3 .col4 { background-color: var(--row3-col4); }

table.contingency tbody .row4 .col1 { background-color: var(--row4-col1); }
table.contingency tbody .row4 .col2 { background-color: var(--row4-col2); }
table.contingency tbody .row4 .col3 { background-color: var(--row4-col3); }
table.contingency tbody .row4 .col4 { background-color: var(--row4-col4); }
</style>
</head>
<body>
<main>
<h1>Statistics on Online Child Sexual Exploitation</h1>
<p style="font-size: 1.4em; font-weight: bold;">Robert Grimm, Charles University</p>
"""


_MARKER_BEGIN = "### BEGIN-RESULT ###"
_MARKER_END = "### END-RESULT ###"

_PRINTR = f"""
printr <- function(value = NULL) {{
    cat2 <- function(...) cat(paste0(c(...), collapse = ""))

    # Split markers to avoid spurious matches. Print marker before
    # capturing the output to avoid missed output.
    cat2("#", "#", "#", " BEGIN-RESULT ", "#", "#", "#", "\\n")

    if (is.null(value)) {{
        lines <- c()
    }} else if (is.character(value)) {{
        lines <- strsplit(value, "\n")
    }} else {{
        lines <- capture.output(print(value))
        lines <- gsub("\t", "    ", lines)
    }}

    for (line in lines) {{
        cat2(line, "\\n")
    }}

    cat2("#", "#", "#", " END-RESULT ", "#", "#", "#", "\\n")
}}
"""

_RESULT_REGEX = re.compile(fr"{_MARKER_BEGIN}(.*?){_MARKER_END}", re.DOTALL)
_TRIM_WS = re.compile(r"^(?:[ \t]*\n)*(.*?)(?:\n*)$", re.DOTALL)
_WIDTH, _ = shutil.get_terminal_size()
_IS_DEBUG = bool(os.getenv("DEBUG"))

def _runr(data: pl.DataFrame, template: str) -> list[str]:
    if len(data) == 1:
        values = data.row(0)
    elif len(data.columns) == 1:
        values = data.get_column(data.columns[0]).to_list()
    else:
        values = None

    if values is not None:
        code = template.format(VECTOR_DATA=", ".join((str(v) for v in values)))
    else:
        buffer = StringIO()
        data.write_csv(buffer)
        code = template.format(CSV_DATA=buffer.getvalue())

    input = _PRINTR + code

    if _IS_DEBUG:
        _print_heading("R Input", weight = "light")
        print(input)

    completion = subprocess.run(["R", "--vanilla"],
        input=input,
        encoding="utf8",
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    output = completion.stdout

    if _IS_DEBUG:
        _print_heading("R Output", weight = "light")
        print(output)

    if completion.returncode != 0:
        raise ValueError(f"R exited due to error:\n{output}")

    results = _RESULT_REGEX.findall(output)
    if not results:
        raise ValueError(f"R did not produce result:\n{output}")

    trimmed_results = []
    for result in results:
        match = _TRIM_WS.match(result)
        assert match is not None
        trimmed_results.append(match.group(1))
    return trimmed_results


def _print_heading(
    title: None | str = None, weight: Literal["light", "heavy", "double"] = "double",
) -> None:
    if weight == "light":
        dash = "─"
    elif weight == "heavy":
        dash = "━"
    else:
        dash = "═"

    if title is None:
        title = ""
    else:
        title = f" {title} "

    print(f"\n\n{dash * 4}{title}{dash * (_WIDTH - 4 - len(title))}\n")

# --------------------------------------------------------------------------------------

def juxtapose(frame: pl.DataFrame) -> pl.DataFrame:
    """Juxtapose quantities disclosed by platforms versus NCMEC."""
    return frame.lazy().filter(
        pl.col("target").is_in(["ESP Total", "Total"]).not_()
    ).group_by(
        pl.col("target", "year"), maintain_order=True,
    ).agg(
        pl.col("value").filter(
            pl.col("source").eq(pl.col("target")).and_(
                pl.col("variable").eq("pieces")
            )
        ).alias("pieces"),
        pl.col("value").filter(
            pl.col("source").eq(pl.col("target")).and_(
                pl.col("variable").eq("reports")
            )
        ).alias("reports"),
        pl.col("value").filter(
            pl.col("source").eq("NCMEC").and_(
                pl.col("variable").eq("reports")
            )
        ).alias("NCMEC"),
    ).select(
        pl.col("target").alias("platform"),
        pl.col("year"),
        pl.col("pieces").list.first(),
        pl.col("reports").list.first(),
        pl.col("NCMEC").list.first(),
    ).with_columns(
        pl.col("pieces").truediv(pl.col("reports")).alias("pieces_factor"),
        pl.col("NCMEC").add(pl.col("reports")).truediv(2).alias("mean_reports")
    ).with_columns(
        pl.col("NCMEC").sub(pl.col("reports")).truediv("mean_reports").alias("pct_diff"),
    ).join(
        frame.lazy().filter(
            pl.col("source").eq("NCMEC").and_(
                pl.col("target").eq("Total")
            ).and_(
                pl.col("variable").eq("reports")
            )
        ).select(
            pl.col("year"),
            pl.col("value").alias("total")
        ),
        on="year",
        how="left",
    ).with_columns(
        pl.col("NCMEC").truediv(pl.col("total")).alias("pct_total")
    ).select(
        "platform", "year",
        "pieces", "pieces_factor", "reports",
        "pct_diff",
        "NCMEC", "pct_total", "total"
    ).sort(
        pl.col("platform", "year")
    ).collect()


def format_percent(value: None | float) -> str:
    if value is None:
        return ""
    if value < 0.000005:
        return "ε"

    return f"{value * 100:0.3f}%"


def format_juxtaposition(frame: pl.DataFrame, with_highlights: bool = False) -> gt.GT:
    """Format the juxtaposition as a great table."""

    table = gt.GT(frame).tab_header(
        title="Comparison of Transparency Disclosures",
        subtitle="About CyberTipline Reports on Child Sexual Exploitation",
    ).tab_spanner(
        label="By Service Provider",
        columns=["pieces", "pieces_factor", "reports"],
    ).tab_spanner(
        label="By NCMEC",
        columns=["NCMEC", "pct_total", "total"],
    ).cols_label(
        year="Year",
        pieces="Pieces",
        pieces_factor="per",
        reports="Reports",
        pct_diff="Δ%",
        NCMEC="Reports",
        pct_total="of",
        total="Total",
    ).tab_stub(
        groupname_col="platform",
        rowname_col="year",
    ).tab_style(
        style=gt.style.text(align="center"),
        locations=gt.loc.column_header(),
    ).tab_style(
        style=gt.style.text(color="#a0a0a0"),
        locations=gt.loc.body(columns=["year", "total"]),
    )

    if with_highlights:
        table = table.tab_style(
            style=gt.style.fill(color= "#ccffba"),
            locations=gt.loc.body(
                columns=["reports", "pct_diff", "NCMEC"],
                rows=pl.col("pct_diff").eq(0),
            )
        )

        for index, diff in enumerate(frame.get_column("pct_diff").to_list()):
            if diff is None:
                continue

            diff = abs(diff)
            if 1 < diff:
                color = "#e3011080"  # Oklch(0.575 0.2348 28º)
            elif 0.80 < diff:
                color = "#ff504480"  # Oklch(0.675 0.2129 28º)
            elif 0.20 < diff:
                color = "#ffc7bac0"  # Oklch(0.875 0.0668 33º)
            elif 0.15 < diff:
                color = "#fec8b2c0"  # Oklch(0.875 0.069 43º)
            elif 0.10 < diff:
                color = "#ffc9a8c0"  # Oklch(0.875 0.0756 53º)
            elif 0.05 < diff:
                color = "#fecb9d80"  # Oklch(0.875 0.0833 63º)
            elif 0.01 < diff:
                color = "#fecc8b80"  # Oklch(0.875 0.1 73º)
            else:
                color = None

            if color is None:
                continue

            table = table.tab_style(
                style=gt.style.fill(color=color),
                locations=gt.loc.body(
                    columns=["reports", "pct_diff", "NCMEC"],
                    rows=[index],
                ),
            )

            if color == "#e3011080":
                table = table.tab_style(
                    style=gt.style.text(color="#ffffff"),
                    locations=gt.loc.body(
                        columns=["reports", "pct_diff", "NCMEC"],
                        rows=[index],
                    ),
                )

    return table.fmt_integer(
        columns=["pieces", "reports", "NCMEC", "total"],
        sep_mark=","
    ).fmt_number(
        columns=["pieces_factor"],
        decimals=2,
    ).fmt_percent(
        columns="pct_diff",
        decimals=2,
        force_sign=True,
    ).sub_missing(
        missing_text="",
    ).sub_zero(
        columns="pct_diff",
        zero_text="≡",
    ).fmt(
        format_percent,
        columns="pct_total",
        is_substitution=True,
    ).opt_table_font(
        stack="neo-grotesque",
    ).opt_all_caps(
        locations=gt.loc.row_groups,
    ).opt_vertical_padding(
        scale=0.8,
    )

# --------------------------------------------------------------------------------------

_PROVIDERS = [
    ["Meta"],
    ["Amazon", "Google", "Snap", "TikTok", "X"],
    ["Discord", "MediaLab", "Omegle", "Reddit", "Pinterest"],
    ["Automattic", "Grindr", "Microsoft", "OpenAI", "X.AI"],
    ["Apple", "Aylo", "Bluesky",  "Quora", "Wikimedia"],
]

_COLORS = [
    Palette.BLUE,
    Palette.ORANGE,
    Palette.RED,
    Palette.GREEN,
    Palette.PURPLE,
]

def plot_reports_per_provider() -> alt.VConcatChart:
    table = tabulate().filter(
        pl.col("source").eq("NCMEC").and_(
            pl.col("variable").eq("reports")
        ).and_(
            pl.col("target").is_in(["Total", "ESP Total"]).not_()
        )
    ).select(
        pl.col("year"),
        pl.col("target").alias("provider"),
        pl.col("value").truediv(1_000_000).alias("reports"),
    )

    charts = []
    for providers in _PROVIDERS:
        data = table.filter(pl.col("provider").is_in(providers))
        chart = alt.Chart(data).mark_line().encode(
            alt.X("year:O").title(None).axis(labelAngle=-45),
            alt.Y("reports:Q").title(None),
            alt.Color("provider:N").title(None)
            .scale(range=_COLORS).legend(orient="right"),
        ).properties(
            height=200,
            width=200,
        )

        if "X.AI" in providers:
            chart = chart + alt.Chart(data.filter(
                pl.col("provider").eq("X.AI")
            )).mark_point(
                shape="triangle",
                size=50,
            ).encode(
                alt.X("year:O"),
                alt.Y("reports:Q"),
                alt.Color("provider:N").scale(range=_COLORS).legend(None)
            )

        charts.append(chart)

    return alt.vconcat(
        alt.hconcat(*charts[:3]).resolve_scale(x="shared", color="independent"),
        alt.hconcat(*charts[3:]).resolve_scale(x="shared", color="independent"),
    ).properties(
        title="Reports (Millions) per Year per Service Provider"
    )

# --------------------------------------------------------------------------------------

def get_options() -> Any:
    parser = ArgumentParser()
    parser.add_argument(
        "--reports",
        action="store_true",
        dest="with_reports",
        help="analyze overall report counts",
    )
    parser.add_argument(
        "--platforms",
        action="store_true",
        dest="with_platforms",
        help="audit platforms' report counts",
    )
    parser.add_argument(
        "--with-icc",
        action="store_true",
        help="compute ICC for platform counts",
    )
    parser.add_argument(
        "--crimes",
        action="store_true",
        dest="with_crimes",
        help="analyze crime statistics",
    )
    return parser.parse_args()


if __name__ == "__main__":
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    options = get_options()
    analyzer = Analyzer("report.html", **vars(options))
    if analyzer.has_content():
        with analyzer:
            analyzer.run()
