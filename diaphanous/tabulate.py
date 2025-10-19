from argparse import ArgumentParser
from collections.abc import Iterator, Sequence
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

from .chart import plot_age_and_sex
from .platform.data import REPORTS_PER_PLATFORM

import diaphanous.aunz as aunz
import diaphanous.bka as bka
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

HEIGHT_ATTR = re.compile(r'height="\d+"')
WIDTH_ATTR = re.compile(r'width="\d+"')
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
        self._secno = [0, 0]
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
            self.h2("Platforms vs NCMEC")

            self.h3("The Data")
            self.html(f"""
                <ul>
                <li>{len(self._diffs.select(
                    pl.col("platform").unique()
                ))} out of {len(self._data.select(
                    pl.col("target").unique()
                )) - 2} surveyed platforms make necessary disclosures
                </li><li>{len(self._diffs)} data pairs
                    <ul>
                    <li>{len(self._diffs.filter(pl.col("pct_diff").abs().le(0.10)))}
                        differ by less than 10%
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").abs().le(0.01)))}
                        differ by less than 1%
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().gt(0)))}
                        positive differences
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().eq(0)))}
                        with no difference
                    </li><li>{len(self._diffs.filter(pl.col("pct_diff").sign().lt(0)))}
                        negative differences
                    </li><li>{self._diffs.select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.2}%
                        mean difference
                    </li><li>{self._diffs.filter(
                            pl.col("platform").ne("Aylo").or_(
                                pl.col("year").ne(2020)
                            )
                        ).select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.2}% mean difference, discounting one explained
                        outlier
                    </li><li>{self._diffs.filter(
                            pl.col("platform").ne("Aylo").or_(
                                pl.col("year").ne(2020)
                            ).and_(
                                pl.col("platform").ne("Pinterest").or_(
                                    pl.col("year").ne(2024)
                                )
                            )
                        ).select(
                            pl.col("pct_diff").mean()
                        ).item() * 100:.2}% mean difference, discounting top two outliers
                    </li></ul></li>
                </ul>
            """)

            comparison = juxtapose(self._data)
            self.html(
                format_juxtaposition(comparison, with_highlights=True).as_raw_html()
            )
            self._see_path()

            self.h3("A Histogram of Percent Differences")
            self.chart(
                alt.Chart(
                    self._diffs
                ).mark_bar().encode(
                    alt.X("pct_diff:Q", bin=True),
                    alt.Y("count()"),
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
            self.html("""
                <p>The following countries and organizations do not seem to collect
                the necessary data:</p>
                <ul>
                <li>European Union
                <li>Phillipines
                <li>Singapore
                <li>UK
                </ul>

                <p>The following countries apparently collect but do not publish
                the necessary data:</p>
                <ul>
                <li>Canada
                </ul>
            """)

            self.emit_mosaics()
            self.emit_age_distributions()

    def emit_mean_difference_plots(self) -> None:
        self._runr(self._diffs, """
library(tidyverse)
library(patchwork)
library(scales)

COLORS <- c(
    "2019" = "#0D0887",
    "2020" = "#5402A3",
    "2021" = "#8B0AA5",
    "2022" = "#B93289",
    "2023" = "#DB5C68",
    "2024" = "#F48849"
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
        xlab(ifelse(all.platforms, "log(Mean)", "Mean")) +
        ylab("Δ% (Mean)") +
        labs(title = platform)

    if (platform == "Reddit") {{
        # Reddit is the only provider with data for all six years.
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

    graph <- graph + theme_light() + theme(axis.title = element_text(face = "italic"))
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

design <- "ABC
           DEF
           GHI
           JJJ"

plot.grid <- wrap_plots(
    plots,
    ncol=3,
    guides="collect",
    design=design,
    axis_titles = "collect"
)
ggsave("figure/comparable-reports.svg", plot.grid, width=8, height=8)
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
        self.h3("Australia 2022/2023")
        self._runr(aunz.au_age_distribution(), """
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
    main = paste0("Offenders by Age/Sex (Australia, 2022/23)")
)
dev.off()
printr()
        """)
        self.col(2)
        self.svg("figure/au-age-sex-2022-23.svg")
        self.end_col()

        self.h3("Germany, 2023-2024")
        self._runr(bka.age_distribution(), """
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
        main = paste0("Offenders by Age/Sex (Germany, ", year, ")")
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
        main = paste0("Offenders by Age/Activity (Germany, ", year, ")")
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

        self.h3("New Zealand 2022/2023")
        frame = aunz.nz_age_distribution().drop_nulls(
            ["age_group", "sex"]
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
        main = paste0("Offenders by Age/Sex (New Zealand, ", year, ")")
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
        main = paste0("Offenders by Age/Activity (New Zealand, ", year, ")")
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

        self.h3("United States, 2023-2024")
        frame = nibrs.offender_age_distribution(with_race=True).drop_nulls(
            ["age_group", "sex"],
        )
        self._runr(frame, """
library(tidyverse)
library(vcdExtra)
us.yearly <- read.csv(text="{CSV_DATA}") |>
    mutate(
        age_group = factor(age_group, levels=c("Child", "Juvenile", "Adult")),
        race = factor(race, levels=c("White", "Black", "Hispanic", "Other"))
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
        main = paste0("Offenders by Age/Sex (United States, ", year, ")")
    )
    dev.off()

    us.contab <- xtabs(count ~ age_group + race + sex, data = us.data)
    print(us.contab)
    svg(paste0("figure/us-age-race-sex-", year, ".svg"))
    vcd::mosaic(
        ~ age_group + race + sex, data = us.contab, direction = c("v", "h", "v"),
        shade = TRUE,
        main = paste0("Offenders by Age/Race/Sex (United States, ", year, ")"),
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
        main = paste0("Offenders by Age/Activity (United States, ", year, ")")
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

    def emit_age_distributions(self) -> None:
        self.html("<div class=wide>\n")
        self.h3("Age Distribution of Offenders")

        au_ages = aunz.au_age_distribution()
        de_ages = bka.age_distribution()
        nz_ages = aunz.nz_age_distribution().filter(
            pl.col("data_year").ge(2023).and_(
                pl.col("data_year").lt(2025)
            )
        )
        us_ages = nibrs.offender_age_distribution()
        us_arrestees = nibrs.arrestee_age_distribution()

        fig = alt.vconcat(
            plot_age_and_sex(au_ages, "Offenders", "Australia"),
            plot_age_and_sex(de_ages, "Suspects", "Germany"),
            plot_age_and_sex(nz_ages, "Offenders", "New Zealand"),
            plot_age_and_sex(us_ages, "Offenders", "United States"),
            plot_age_and_sex(us_arrestees, "Arrestees", "United States"),
        ).resolve_scale(x="shared")

        path = "figure/age-distributions.svg"
        fig.save(path)
        self.svg(path)
        self.html("</div>\n")

    # ==================================================================================

    def hr(self) -> None:
        self.html("<hr>\n")

    def h2(self, title: str) -> None:
        self._secno[0] += 1
        self._secno[1] = 0
        secno = f"{self._secno[0]}."

        s = f"{secno} {title}"
        _print_heading(s)
        self._section(s, level=2)

    def h3(self, title: str) -> None:
        self._secno[1] += 1
        secno = f"{self._secno[0]}.{self._secno[1]}"

        s = f"{secno} {title}"
        _print_heading(s, weight="heavy")
        self._section(s, level=3)

    def _section(self, title: str, level: Literal[2, 3, 4] = 2) -> None:
        self.html(f"\n\n<h{level}>{title}</h{level}>\n")

    def col(self, num: int) -> None:
        self.html(
            '<div style="display: grid; grid-template-columns:'
            f'{" 1fr" * num}; gap: 2rem;">\n'
        )

    def end_col(self) -> None:
        self.html("</div>\n")

    def _runr(self, frame: pl.DataFrame, template: str) -> None:
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
}
body {
    margin: 3rem 0.5rem;
}

svg {
    display: block;
}
.vega-embed {
    display: block !important;
}
figure {
    margin: 0;
}

main > * {
    max-width: 80rch;
    margin-left: auto;
    margin-right: auto;
}

main > .wide {
    max-width: 1085px;
}

h2 {
    margin-top: 3rem;
    padding: 0.5rem;
    background-color: #e8e8e8;
}

h3 {
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
/* ----------------------------------- Table ----------------------------------- */

.mytable {
    border-collapse: separate;
    border-spacing: 0;
    line-height: 1.2;
    margin-bottom: 3rem;
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
</style>
</head>
<body>
<main>
<h1>The CyberTipline Reporting System</h1>
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
        lambda x: "ε" if x < 0.000005 else f"{x * 100:0.3f}%",
        columns="pct_total",
        is_substitution=True,
    ).opt_table_font(
        stack="neo-grotesque",
    ).opt_all_caps(
        locations="row_group",
    ).opt_vertical_padding(
        scale=0.8,
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
        "--crimes",
        action="store_true",
        dest="with_crimes",
        help="analyze crime statistics",
    )
    return parser.parse_args()


if __name__ == "__main__":
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    options = get_options()
    analyzer = Analyzer("report.html", **vars(options))
    if analyzer.has_content():
        with analyzer:
            analyzer.run()
