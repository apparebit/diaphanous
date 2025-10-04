from collections.abc import Iterator, Sequence
from io import StringIO
import subprocess
from typing import Any, cast, Literal

import altair as alt
import great_tables as gt
import polars as pl

from .data import REPORTS_PER_PLATFORM


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

# --------------------------------------------------------------------------------------

def distill_differences(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.lazy().filter(
        pl.col("source").ne("NCMEC")
    ).select(
        pl.col("target", "year", "variable", "value"),
    ).join(
        frame.lazy().filter(
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


def analyze_differences(differences: pl.DataFrame) -> None:
    histogram = differences.select(pl.col("pct_diff").hist())
    alt.Chart(
        differences
    ).mark_bar().encode(
        alt.X("pct_diff:Q", bin=True),
        alt.Y("count()"),
    ).save("diff-hist.svg")

    source = _prepare_arr(differences)
    print(source)
    completion = subprocess.run(["R", "--vanilla"],
        input=source,
        encoding="utf8",
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    completion.check_returncode()
    output = completion.stdout
    print(output)


def _prepare_arr(differences: pl.DataFrame) -> str:
    buffer = StringIO()
    differences.with_columns(pl.col("pct_diff").mul(100)).write_csv(buffer)

    match_counts = _get_match_counts(differences).get_column("count")
    sign_counts = _get_sign_counts(differences).filter(
        pl.col("sign").ne(0)
    ).get_column("count")

    def S(name: None | str = None) -> str:
        name = "┈" * 6 if name is None else f" {name} "
        return f"cat(\"\\n┈┈┈┈{name}{'┈' * (80 - len(name) - 4)}\\n\")"

    return f"""\

library(tidyverse)
library(patchwork)
library(scales)

# --------------------------------------------------------------------------------------
{S()}
dt.match <- data.frame(
    platform = c("Reddit", "Reddit", "Other", "Other"),
    has_match = c("yes", "no", "yes", "no"),
    freq = c({", ".join(str(c) for c in match_counts)})
)
print(dt.match)
dt.match.contab <- xtabs(freq ~ platform + has_match, data = dt.match)

{S('Platform Independence')}
dt.match.test <- fisher.test(dt.match.contab)
print(dt.match.test)

# --------------------------------------------------------------------------------------
{S()}
dt.sign <- c({", ".join(str(c) for c in sign_counts)})
print(dt.sign)

{S('Directional Bias')}
dt.sign.test <- binom.test(
    dt.sign,
    p = 0.5,
    alternative = "two.sided",
)
print(dt.sign.test)

# --------------------------------------------------------------------------------------
{S('Mean Difference Plots')}

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

    graph <- graph + theme_light() #linedraw()
    return(graph)
}}

difference.data <- read.csv(text = "{buffer.getvalue()}")
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

plot.grid <- wrap_plots(plots, ncol=3, guides="collect", design=design)
ggsave("comparable-reports.svg", plot.grid, width=8, height=8)
    """


def _get_match_counts(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(
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
    ).sort("platform", "matches", descending=True)


def _get_sign_counts(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(
        pl.col("diff").sign()
    ).group_by(
        pl.col("diff")
    ).agg(
        pl.len()
    ).select(
        pl.col("diff").alias("sign"),
        pl.col("len").alias("count"),
    ).sort(
        pl.col("sign"), descending=True
    )

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

if __name__ == "__main__":
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    pieces_and_reports = tabulate()
    differences = distill_differences(pieces_and_reports)
    print(differences)
    analyze_differences(differences)

    comparison = juxtapose(pieces_and_reports)
    format_juxtaposition(comparison, with_highlights=True).save("report-counts.pdf")
