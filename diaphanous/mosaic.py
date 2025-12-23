from collections.abc import Sequence
from typing import Literal

import altair as alt
import itertools
import numpy as np
import polars as pl
from polars.expr.whenthen import ChainedThen, Then
from scipy import stats

from .color import Palette, PlusMinus
from .util import (
    COUNTRIES, hrule, MATERIALS, METRIC_ORDER, METRICS, rate_pvalue, ROLES,
    to_contingency_table, to_minor_adult
)


def _sort_values(values: Sequence[None | str]) -> Sequence[None | str]:
    return sorted(values, key=lambda v:"0" if v is None else f"1:{v}")


def _make_index(
    frame: pl.DataFrame,
    columns: Sequence[str],
    index: None | dict[str, Sequence[None | str]] = None,
) -> dict[str, Sequence[None | str]]:
    """
    Create an index for the given columns. This function fills in the given
    index, if not null. Otherwise, it creates an index from scratch. The index
    is an ordered map of columns names as keys and the list of column values as
    values.
    """
    if index is None:
        index = {}

    for column in columns:
        frame_values = frame.select(
            pl.col(column).unique(maintain_order=True)
        ).get_column(column).to_list()

        index_values = index.get(column)
        if index_values is None:
            # As special case, place null between two non-null values:
            if len(frame_values) == 3 and None in frame_values:
                vs = sorted(v for v in frame_values if v is not None)
                index[column] = [vs[0], None, vs[1]]
            else:
                index[column] = _sort_values(frame_values)

        elif (fvs := _sort_values(frame_values)) != (ivs := _sort_values(index_values)):
            raise ValueError(
                f"index for column {column} contains {ivs} instead of {fvs}"
            )

    return index


def _make_index_norm(
    frame: pl.DataFrame,
    index: dict[str, Sequence[None | str]],
) -> pl.DataFrame:
    # Compute the empty core with null column values only
    empty_core = pl.DataFrame({
        c: None for c in index.keys()
    }).cast({
        c: frame.schema[c] for c in index.keys()
    })

    # Compute the core product of column values
    core = pl.DataFrame({
        # Compute rows with the product of per-column values, all in order, and
        # then convert to columnar form.
        c: v for c, v in zip(index.keys(), zip(*itertools.product(*index.values())))
    }).cast({
        c: frame.schema[c] for c in index.keys()
    })

    # For every metric...
    all_data = []
    for (metric,), group in frame.group_by(pl.col("metric"), maintain_order=True):
        country_material, _, role = metric.rpartition(" ")
        role = role[:-1]
        country, _, material = country_material.rpartition(" ")
        metric_columns = [
            pl.lit(country, dtype=pl.Enum(COUNTRIES)).alias("country"),
            pl.lit(material, dtype=pl.Enum(MATERIALS)).alias("material"),
            pl.lit(role, dtype=pl.Enum(ROLES)).alias("role"),
            pl.lit(metric, dtype=pl.Enum(METRICS)).alias("metric"),
            pl.lit(METRIC_ORDER[metric], dtype=pl.Int8).alias("metric_order"),
        ]

        # Determine years with non-null column values
        data_years = frozenset(group.select(
            pl.col("data_year").filter(
                *(
                    pl.col(c).is_not_null() for c in index.keys()
                )
            ).unique()
        ).get_column("data_year"))

        # For every year...
        for year in group.select(
            pl.col("data_year").unique(maintain_order=True)
        ).get_column("data_year"):
            all_data.append(
                (core if year in data_years else empty_core).select(
                    *metric_columns,
                    pl.lit(year, dtype=pl.Int16).alias("data_year"),
                    *core.columns,
                )
            )

    return pl.concat(all_data)


def _check_highlights(
    columns: Sequence[str],
    index: dict[str, Sequence[None | str]],
    highlights: None | dict[None | str, dict[None | str, str]],
) -> dict[None | str, dict[None | str, str]]:
    if highlights is None:
        highlights = {}

    xs = index[columns[0]]
    ys = index[columns[1]]

    for key1, level2 in highlights.items():
        if key1 not in xs:
            raise ValueError(f"column {columns[0]} does not contain {key1}")

        for key2 in level2:
            if key2 not in ys:
                raise ValueError(f"column {columns[1]} does not contain {key2}")

    return highlights


def _check_counts(
    columns: Sequence[str],
    index: dict[str, Sequence[None | str]],
    include_null: bool,
) -> None:
    count = len(index[columns[0]])
    if include_null and count != 3 or not include_null and count != 2:
        raise ValueError(
            f"can't show counts for column {columns[0]} with {count} distinct values"
        )
    count = len(index[columns[1]])
    if include_null and count != 3 or not include_null and count != 2:
        raise ValueError(
            f"can't show counts for column {columns[1]} with {count} distinct values"
        )


def _make_null_predicate(
    columns: Sequence[str],
    junction: Literal["and", "or"],
    predicate: None | pl.Expr = None,
) -> pl.Expr:
    for column in columns:
        if predicate is None:
            predicate = pl.col(column).is_null()
        elif junction == "and":
            predicate = predicate.and_(
                pl.col(column).is_null()
            )
        elif junction == "or":
            predicate = predicate.or_(
                pl.col(column).is_null()
            )
        else:
            assert False, "unreachable"

    assert predicate is not None
    return predicate


def _make_color_expr(
    columns: Sequence[str],
    default_color: str = Palette.GRAY,
    alpha: str = "ff",
    include_null: bool = False,
) -> pl.Expr:
    expr = None

    predicate = None
    for column in columns:

        if predicate is None:
            predicate = pl.col(column).is_null()
        else:
            predicate = predicate.and_(
                pl.col(column).is_null()
            )

        assert predicate is not None
        expr = pl.when(
            predicate
        ).then(
            pl.lit("transparent")
        ).when(
            pl.col(columns[0]).is_null().or_(
                pl.col(columns[1]).is_null()
            )
        ).then(
            pl.lit("#dadee6a0")
        )

    return (pl.lit(Palette.GRAY) if expr is None else expr.otherwise(
        pl.lit(Palette.GRAY)
    )).cast(pl.String).alias("stroke")


def _make_stroke_expr(
    columns: Sequence[str],
    include_null: bool = False,
) -> pl.Expr:
    expr = None
    if include_null:
        expr = pl.when(
            pl.col(columns[0]).is_null().and_(
                pl.col(columns[1]).is_null()
            )
        ).then(
            pl.lit("transparent")
        ).when(
            pl.col(columns[0]).is_null().or_(
                pl.col(columns[1]).is_null()
            )
        ).then(
            pl.lit("#dadee6a0")
        )

    return (pl.lit(Palette.GRAY) if expr is None else expr.otherwise(
        pl.lit(Palette.GRAY)
    )).cast(pl.String).alias("stroke")


def _make_highlight_expr(
    columns: Sequence[str],
    highlights: dict[None | str, dict[None | str, str]],
    alpha: str = "ff",
) -> None | Then | ChainedThen:
    expr = None
    for key1, level2 in highlights.items():
        for key2, value in level2.items():
            expr = (pl if expr is None else expr).when(
                (
                    pl.col(columns[0]).is_null() if key1 is None
                    else pl.col(columns[0]).eq(key1)
                ).and_(
                    pl.col(columns[1]).is_null() if key2 is None
                    else pl.col(columns[1]).eq(key2)
                )
            ).then(
                pl.lit(f"{value}{alpha}")
            )
    return expr


def _compute_residuals(
    frame: pl.DataFrame,
    x_axis: str,
    y_axis: str,
    x_order: None | str = None,
    y_order: None | str = None,
) -> pl.DataFrame:
    data = []
    for (metric, year), group in frame.group_by(
        "metric", "data_year",
        maintain_order=True
    ):
        observed = to_contingency_table(
            group, x_axis, y_axis,
            x_order=x_order,
            y_order=y_order,
        )

        if observed is None:
            continue

        expected = stats.contingency.expected_freq(observed)
        if np.any(expected == 0):
            continue

        residuals = (observed - expected) / np.sqrt(expected)
        column = np.reshape(residuals, shape=residuals.size)

        data.append(group.filter(
            pl.col(x_axis).is_not_null().and_(pl.col(y_axis).is_not_null())
        ).select(
            pl.lit(metric, dtype=pl.Enum(METRICS)).alias("metric"),
            pl.lit(year, dtype=pl.Int16).alias("data_year"),
            pl.col(x_axis),
            pl.col(y_axis),
            pl.lit(column, dtype=pl.List(pl.Float64)).alias("residual")
        ).explode("residual"))

    return pl.concat(data)


def _make_fill_expr(
    columns: Sequence[str],
    highlights: dict[None | str, dict[None | str, str]],
    use_residuals: bool = False,
    include_null: bool = False,
) -> pl.Expr:
    expr = _make_highlight_expr(columns, highlights, "a0")

    if use_residuals:
        expr = (pl.when if expr is None else expr.when)(
            pl.col("residual").le(-4)
        ).then(
            pl.lit(PlusMinus.MINUS_MINUS)
        ).when(
            pl.col("residual").le(-2)
        ).then(
            pl.lit(PlusMinus.MINUS)
        ).when(
            pl.col("residual").ge(4)
        ).then(
            pl.lit(PlusMinus.PLUS_PLUS)
        ).when(
            pl.col("residual").ge(2)
        ).then(
            pl.lit(PlusMinus.PLUS)
        )

    if include_null:
        expr = (pl.when if expr is None else expr.when)(
            pl.col(columns[0]).is_null().and_(
                pl.col(columns[1]).is_null()
            )
        ).then(
            pl.lit("transparent")
        ).when(
            pl.col(columns[0]).is_null().or_(
                pl.col(columns[1]).is_null()
            )
        ).then(
            pl.lit("#dadee6a0")
        )

    expr = pl.lit("#aaaeb6a0") if expr is None else expr.otherwise(
        pl.lit("#aaaeb6a0")
    )

    return expr.cast(pl.String).alias("fill")


def make_mosaic_frame(
    frame: pl.DataFrame,
    x_axis: str,
    y_axis: str,
    *,
    gap: float = 3.0,
    index: None | dict[str, Sequence[None | str]] = None,
    highlights: None | dict[None | str, dict[None | str, str]] = None,
    use_residuals: bool = False,
    use_minor: bool = False,
    include_null: bool = False,
    show_counts: bool = False,
    show_percent: bool = False,
) -> pl.DataFrame:
    # use_minor and include_null both impact index
    if use_minor:
        frame = to_minor_adult(frame)
    if not include_null:
        frame = frame.drop_nulls(
            [x_axis, y_axis]
        )

    # Fill in index of axis values and thereafter check counts
    index = _make_index(frame, [x_axis, y_axis], index)
    highlights = _check_highlights([x_axis, y_axis], index, highlights)
    if show_counts:
        _check_counts([x_axis, y_axis], index, include_null)
    if show_percent:
        if not show_counts:
            raise ValueError("can't show percent without counts")

    # Compute frequency form for two axes.
    contingencies = frame.group_by(
        "country", "material", "role", "metric", "metric_order",
        "data_year",
        x_axis, y_axis,
        maintain_order=True
    ).agg(
        pl.col("count").sum().round().cast(pl.Int64),
    )

    # Normalize frequency table by including all possible non-null rows.
    # Ensure the table covers all possible rows
    norm = _make_index_norm(contingencies, index)
    contingencies = norm.join(
        contingencies,
        on=[
            "country", "material", "role", "metric", "metric_order",
            "data_year",
            x_axis, y_axis,
        ],
        how="left",
        maintain_order="left",
        nulls_equal=True,
    ).filter(
        pl.col("count").is_not_null().or_(
            pl.col(x_axis).is_not_null().and_(
                pl.col(y_axis).is_not_null()
            )
        )
    ).with_columns(
        pl.col("count").fill_null(0),
    )

    # Sort rows in custom order by mapping values to integer.
    contingencies = contingencies.with_columns(
        pl.col(x_axis).replace({
            value: key for key, value in enumerate(index[x_axis])
        }).alias("x_order"),
        pl.col(y_axis).replace({
            value: key for key, value in enumerate(index[y_axis])
        }).alias("y_order"),
    ).sort(
        "metric_order", "data_year", "x_order", "y_order"
    )

    # Compute x coordinates using x_axis' marginal frequencies: Normalize
    # counts, add in gaps, normalize again.
    xs = contingencies.group_by(
        "metric", "data_year", x_axis, maintain_order=True
    ).agg(
        pl.col("country", "material", "role").first(),
        pl.col("count").sum(),
    ).with_columns(
        pl.col("count").cum_sum().over(
            "metric", "data_year"
        ).alias("x2"),
        pl.lit(gap, dtype=pl.Float64).alias("gap"),
    ).with_columns(
        pl.col("x2").sub("count").alias("x1"),
        pl.col("x2").max().over(
            "metric", "data_year"
        ).alias("scale"),
        pl.col("gap").cum_sum().sub(gap).over(
            "metric", "data_year",
        ),
    ).with_columns(
        pl.col(
            "x1", "x2"
        ).truediv("scale").mul(100).add(pl.col("gap")).name.prefix("normalized_"),
    ).with_columns(
        # Renormalize the normalized coordinates to account for gap differences
        pl.col("normalized_x1").truediv(
            pl.col("normalized_x2").max()
        ).mul(100).over(
            "metric", "data_year"
        ),
        pl.col("normalized_x2").truediv(
            pl.col("normalized_x2").max()
        ).mul(100).over(
            "metric", "data_year"
        ),
    )

    # Compute y coordinates using y_axis' conditional frequencies: Normalize
    # counts, add in gaps, normalize again.
    ys = contingencies.with_columns(
        pl.col("count").cum_sum().over(
            "metric", "data_year", x_axis
        ).alias("y2"),
        pl.lit(gap, dtype=pl.Float64).alias("gap"),
    ).with_columns(
        pl.col("y2").sub("count").alias("y1"),
        pl.col("y2").max().over(
            "metric", "data_year", x_axis
        ).alias("scale"),
        pl.col("gap").cum_sum().sub(gap).over(
            "metric", "data_year", x_axis
        )
    ).with_columns(
        pl.col(
            "y1", "y2"
        ).truediv("scale").mul(100).add(pl.col("gap")).name.prefix("normalized_"),
    ).with_columns(
        # Renormalize the normalized coordinates to account for gap differences
        pl.col("normalized_y1").truediv(
            pl.col("normalized_y2").max()
        ).mul(100).over(
            "metric", "data_year", x_axis
        ),
        pl.col("normalized_y2").truediv(
            pl.col("normalized_y2").max()
        ).mul(100).over(
            "metric", "data_year", x_axis
        ),
    )

    # Combine coordinates into one data frame.
    mosaic_frame = xs.drop(
        "count"
    ).join(
        ys,
        on=["metric", "data_year", x_axis],
        how="inner",
        nulls_equal=True,
        maintain_order="left",
    ).rename({
        "scale": "x_scale",
        "scale_right": "y_scale",
    })

    if show_percent:
        mosaic_frame = mosaic_frame.with_columns(
            pl.col("count").fill_null(0).sum().over(
                "metric", "data_year"
            ).alias("non_null_total"),
        ).with_columns(
            pl.col("count").truediv("non_null_total").mul(100).alias("percent")
        ).with_columns(
            pl.col("percent").map_elements(
                lambda v: f"({v:.1f}%)",
                return_dtype=pl.String,
            )
        )

    # Add count labels.
    if show_counts:
        labels = []
        for x, y in ((1, 1), (1, 2), (2, 1), (2, 2)):
            labels.append(
                pl.when(
                    (
                        pl.col("x_order").eq(pl.col("x_order").min()) if x == 1
                        else pl.col("x_order").eq(pl.col("x_order").max())
                    ).and_(
                        pl.col("y_order").eq(pl.col("y_order").min()) if y == 1
                        else pl.col("y_order").eq(pl.col("y_order").max())
                    )
                ).then(
                    pl.col("count")
                        .cast(pl.String)
                        .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
                ).otherwise(
                    pl.lit("", dtype=pl.String)
                ).alias(f"label{x}{y}")
            )

        mosaic_frame = mosaic_frame.with_columns(*labels)

    if show_percent:
        labels = []
        for x, y in ((1, 1), (1, 2), (2, 1), (2, 2)):
            label = f"label{x}{y}"

            labels.append(
                pl.when(
                    pl.col(label).ne("")
                ).then(
                    pl.concat_list(label, "percent")
                ).otherwise(
                    pl.lit([], dtype=pl.List(pl.String))
                )
            )

        mosaic_frame = mosaic_frame.with_columns(*labels)

    # Clean up data frame by dropping unneeded columns and arranging remaining
    # columns in meaningful order.
    mosaic_frame = mosaic_frame.select(
        "country", "material", "role", "metric",
        "data_year",
        x_axis, y_axis, "x_order", "y_order",
        "count",
        "x1", "x2", "normalized_x1", "normalized_x2", "x_scale",
        "y1", "y2", "normalized_y1", "normalized_y2", "y_scale",
        *(
            ["label11", "label12", "label21", "label22"] if show_counts
            else []
        ),
    )

    # Compute Pearson residuals
    if use_residuals:
        residuals = _compute_residuals(mosaic_frame, x_axis, y_axis, "x_order", "y_order")
        mosaic_frame = mosaic_frame.join(
            residuals,
            on=["metric", "data_year", x_axis, y_axis],
            how="left",
            maintain_order="left",
        )

    stroke_expr = _make_stroke_expr([x_axis, y_axis], include_null)
    fill_expr = _make_fill_expr(
        [x_axis, y_axis],
        highlights,
        use_residuals=use_residuals,
        include_null=include_null,
    )

    return mosaic_frame.with_columns(
        stroke_expr,
        fill_expr,
    )


def test_chi2_independence(
    frame: pl.DataFrame,
    x_axis: str,
    y_axis: str,
    x_order: None | str = None,
    y_order: None | str = None,
) -> pl.DataFrame:
    x_order = x_order or x_axis
    y_order = y_order or y_axis

    # Collect results in column form to more easily reintegrate into data frame
    metrics = []
    years = []
    chi2s = []
    p_values = []
    ratings = []

    for labels, group in frame.group_by("metric", "data_year", maintain_order=True):
        # Record group labels
        metrics.append(labels[0])
        years.append(labels[1])

        # Reduce group data to bare essentials
        table = to_contingency_table(
            group, x_axis, y_axis,
            x_order=x_order,
            y_order=y_order,
        )

        if table is None or not np.all(table >= 5):
            chi2s.append(None)
            p_values.append(None)
            ratings.append("" if table is None else "N/A")
            continue

        # Perform Monte Carlo version of χ² test
        result = stats.chi2_contingency(
            table,
            correction=False,
            method=stats.MonteCarloMethod(),
        )

        chi2s.append(result.statistic) # type: ignore
        p_values.append(result.pvalue) # type: ignore
        ratings.append(rate_pvalue(result.pvalue)) # type: ignore

    # Add χ² test results to existing mosaic frame
    return frame.join(
        pl.DataFrame({
            "metric": metrics,
            "data_year": years,
            "chi2": chi2s,
            "pvalue": p_values,
            "rating": ratings,
        }).cast({
            "metric": pl.Enum(METRICS),
            "data_year": pl.Int16,
        }),
        on=["metric", "data_year"],
        how="left",
        maintain_order="left",
    )


def plot_mosaic_grid(
    frame: pl.DataFrame,
    x_label: str,
    y_label: str,
    *,
    subtitle: None | str | Sequence[str] = None,
    cell_width: float = 320,
    cell_height: float = 320,
    row_gap: float = 20,
    column_gap: float = 20,
) -> alt.VConcatChart:
    """
    Plot a mosaic grid. This function creates a grid of mosaic plots, using
    years as columns and different combinations of country, material, and role
    as rows.
    """
    title = alt.Title(
        f"Perpetrators by {x_label}, {y_label}, Year, and Country",
        fontSize=50,
        fontWeight="bold",
        anchor="start",
        frame="group",
        dx=0,
        dy=-10,
    )
    if subtitle is not None:
        title["subtitle"] = subtitle
        title["subtitleFontSize"] = 40

    show_counts = "label12" in frame.columns and "label21" in frame.columns
    show_percent = (
        "label12" in frame.columns and isinstance(frame.schema["label12"], pl.List)
    )
    show_ratings = "chi2" in frame.columns and "rating" in frame.columns

    last_metric = frame.select(
        pl.col("metric").last()
    ).item()

    # Prepare text of numeric labels and χ² test results
    rows = []
    for metric, group in frame.group_by("metric", maintain_order=True):
        base = alt.Chart(group)

        labels = []
        if show_counts:
            for x, y in ((1, 1), (1, 2), (2, 1), (2, 2)):
                labels.append(base.mark_text(
                    x=0 if x == 1 else 320,
                    y=325 if y == 1 else (-40 if show_percent else -5),
                    align="left" if x== 1 else "right",
                    baseline="top" if y == 1 else "bottom",
                    fontSize=30,
                ).encode(
                    alt.Text(f"label{x}{y}:N"),
                ))

        if show_ratings:
            labels.append(base.mark_text(
                x=160,
                y=325,
                align="center",
                baseline="top",
                fontSize=30,
            ).encode(
                alt.Text("rating:N"),
            ))

        # Chart an entire row of per-country data over the years
        row = alt.layer(
            base.mark_rect(
                stroke="black",
                strokeWidth=3,
            ).encode(
                alt.X("normalized_x1:Q").axis(None),
                alt.X2("normalized_x2"),
                alt.Y("normalized_y1:Q").axis(None),
                alt.Y2("normalized_y2"),
                alt.Stroke("stroke:N", legend=None).scale(None),
                alt.Fill("fill:N", legend=None).scale(None),
            ),
            *labels,
        ).properties(
            width=cell_width,
            height=cell_height,
        ).facet(
            column=alt.Column(
                "data_year:N",
                title=None,
                header=alt.Header(
                    labelAnchor="middle",
                    labelOrient="bottom",
                    labelFontSize=40,
                ) if metric[0] == last_metric else alt.Header(labels=False),
            ),
            title=alt.Title(
                group.select(pl.col("country").first()).item(),
                anchor="middle",
                orient="left",
                angle=270,
                fontSize=40,
                fontWeight="normal",
                dx=20 if metric[0] == last_metric else 0,
                dy=0,
                subtitle=f"{
                    group.select(pl.col("material").first()).item()
                } {
                    group.select(pl.col("role").first()).item()
                }s",
                subtitleFontSize=35,
            ),
            spacing=column_gap,
        )

        rows.append(row)

    # Combine rows into grid
    grid = alt.vconcat(
        hrule(10, 10 * cell_width + 11 * column_gap),
        *rows,
        spacing=row_gap + (20 if show_percent else 0),
    ).resolve_scale(
        x="shared",
    ).configure_axis(
        grid=False,
        labelFontSize=35,
        titleFontSize=40,
    ).configure_view(
        stroke=None,
    ).properties(
        title=title,
    )

    return grid


def compute_odds_ratios(
    frame: pl.DataFrame,
    x_axis: str,
    y_axis: str,
    x_order: None | str = None,
    y_order: None | str = None,
    use_minor: bool = False,
) -> pl.DataFrame:
    x_order = x_order or x_axis
    y_order = y_order or y_axis

    if use_minor:
        frame = to_minor_adult(frame)

    labels = []
    odds_ratios = []
    odds_labels = []
    lower_cis = []
    upper_cis = []

    for label, group in frame.group_by(
        "country", "material", "role", "data_year", maintain_order=True
    ):
        labels.append(label)

        table = to_contingency_table(
            group, x_axis, y_axis,
            x_order=x_order,
            y_order=y_order,
        )

        if table is None or not np.all(table > 0):
            odds_ratios.append(None)
            odds_labels.append(
                "N/A" if label[0] != "Australia" and label[0] != "Italy" else ""
            )
            lower_cis.append(None)
            upper_cis.append(None)
            continue

        ratio = stats.contingency.odds_ratio(table, kind="sample")
        odds_ratios.append(ratio.statistic)
        odds_labels.append("")

        ci = ratio.confidence_interval()
        lower_cis.append(ci[0])
        upper_cis.append(ci[1])

    # Turn rows into columns
    labels = [*zip(*labels)]

    return pl.DataFrame({
        "country": labels[0],
        "material": labels[1],
        "role": labels[2],
        "data_year": labels[3],
        "odds_ratio": odds_ratios,
        "odds_label": odds_labels,
        "lower_ci": lower_cis,
        "upper_ci": upper_cis,
    }, schema={
        "country": pl.String,
        "material": pl.Enum(MATERIALS),
        "role": pl.Enum(ROLES),
        "data_year": pl.Int16,
        "odds_ratio": pl.Float64,
        "odds_label": pl.Enum(["", "N/A"]),
        "lower_ci": pl.Float64,
        "upper_ci": pl.Float64,
    })


def plot_odds_ratio_grid(
    frame: pl.DataFrame,
    cell_width: float = 300,
    cell_height: float = 300,
    column_count: int = 5,
    gap: float = 20,
) -> alt.VConcatChart:
    group_iter = frame.group_by("country", "material", "role", maintain_order=True)
    grid = []

    for index, (labels, group) in enumerate(group_iter):
        is_first_column = index % column_count == 0
        if is_first_column:
            grid.append([])

        country, material, role = labels
        material_role = f"{material} {role}s"

        outlier = None
        if country == "Finland":
            outlier = group.filter(
                pl.col("data_year").eq(2019)
            ).select(
                "lower_ci", "odds_ratio", "upper_ci"
            ).row(0)

            group = group.with_columns(
                *(
                    pl.when(
                        pl.col("data_year").eq(2019)
                    ).then(
                        pl.lit(None)
                    ).otherwise(
                        pl.col(c)
                    ).alias(c)
                    for c in ("lower_ci", "odds_ratio", "upper_ci")
                )
            )

        min_ci, max_ci = group.select(
            pl.col("lower_ci").min().alias("min_ci"),
            pl.col("upper_ci").max().alias("max_ci"),
        ).row(0)

        base = alt.Chart(group)

        if country == "Finland":
            assert outlier is not None
            label = f"{outlier[1]:.1f}, 95% CI [{outlier[0]:.1f}, {outlier[2]:.1f}]"

            outlier_text = [base.mark_text(
                fontSize=15,
                x=cell_width,
                dx=-17,
                y=4 * cell_height / 10 + cell_height / 10 / 2,
                align="right",
                baseline="middle",
            ).encode(
                alt.TextDatum(label),
            )]
        else:
            outlier_text = []

        if min_ci < 1.0 < max_ci:
            independence_rule = [base.mark_rule(
                strokeWidth=2.5,
                strokeDash=(8, 4),
            ).encode(
                alt.XDatum(1),
            )]
        else:
            independence_rule = []

        chart = alt.layer(
            base.mark_point(
                filled=True,
                size=45,
                color=Palette.BLACK,
            ).encode(
                alt.X("odds_ratio:Q", axis=alt.Axis(
                    labelFontSize=18,
                    title=None,
                )),
                alt.Y("data_year:N", axis=alt.Axis(
                    labels=is_first_column,
                    labelFontSize=18,
                    title=None,
                )),
            ),
            base.mark_point(
                size=1,
                color="transparent",
            ).encode(
                alt.XDatum(0),
                alt.Y("data_year:N"),
            ),
            base.mark_rule(
                strokeWidth=2,
                color=Palette.BLACK,
            ).encode(
                alt.X("lower_ci:Q"),
                alt.X2("upper_ci:Q"),
                alt.Y("data_year:N"),
            ),
            base.mark_text(
                fontSize=15,
            ).encode(
                alt.Y("data_year:N"),
                alt.Text("odds_label:N"),
            ),
            *outlier_text,
            *independence_rule,
            title=alt.Title(
                country,
                subtitle=material_role,
                anchor="middle",
                orient="bottom",
                fontSize=20,
                fontWeight="normal",
                subtitleFontSize=18,
                dy=10,
            ),
        ).properties(
            width=cell_width,
            height=cell_height,
        )

        grid[-1].append(chart)

    return alt.vconcat(
        hrule(7.5, column_count * cell_width + (column_count + 1) * gap),
        *(
            alt.hconcat(*row, spacing=gap) for row in grid
        ),
        spacing=gap,
    ).properties(
        title=alt.Title(
            "Odds Ratios for Age Group and Sex by Year and Country",
            fontSize=20,
            fontWeight="bold",
            anchor="start",
            frame="group",
            dx=0,
            dy=-10,
        )
    )


if __name__ == "__main__":
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_rows(100)
    pl.Config.set_thousands_separator(True)
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment("RIGHT")

    from .crimestat import load_all_age_distributions

    # _WIDTH, _ = shutil.get_terminal_size()
    distributions = load_all_age_distributions(compact=True)
    #frame = pl.concat(distributions.values())

    frame = make_mosaic_frame(
        distributions["nz"],
        "age_group",
        "sex",
        index={"age_group": ["Minor", "Adult"], "sex": ["Male", "Female"]},
        use_minor=True,
    ) # type: ignore

    print(frame.select(pl.exclude("metric")))
