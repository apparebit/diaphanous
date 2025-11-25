from collections.abc import Sequence

import altair as alt
import polars as pl
from polars.expr.whenthen import ChainedThen, Then
from scipy import stats

from .color import Palette
from .util import hrule, rate_pvalue, regularize_age_distribution, to_contingency_table


def _sort_values(values: Sequence[None | str]) -> Sequence[None | str]:
    return sorted(values, key=lambda v:"0" if v is None else f"1:{v}")


def _make_index(
    frame: pl.DataFrame,
    columns: Sequence[str],
    index: None | dict[str, Sequence[None | str]] = None,
) -> dict[str, Sequence[None | str]]:
    if index is None:
        index = {}

    for column in columns:
        frame_values = frame.select(
            pl.col(column).unique()
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


def _make_fill_expr(
    columns: Sequence[str],
    highlights: dict[None | str, dict[None | str, str]],
    include_null: bool = False,
) -> pl.Expr:
    expr = _make_highlight_expr(columns, highlights, "a0")

    if include_null:
        expr = (pl if expr is None else expr).when(
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
    use_minor: bool = False,
    include_null: bool = False,
    show_counts: bool = False,
) -> pl.DataFrame:
    # use_minor and include_null both impact index
    if use_minor:
        frame = frame.with_columns(
            pl.col("age_group").replace({
                "Child": "Minor",
                "Juvenile": "Minor",
            })
        )
    if not include_null:
        frame = frame.drop_nulls(
            [x_axis, y_axis]
        )

    # Fill in index of axis values and thereafter check highlights and counts
    index = _make_index(frame, [x_axis, y_axis], index)
    highlights = _check_highlights([x_axis, y_axis], index, highlights)
    if show_counts:
        _check_counts([x_axis, y_axis], index, include_null)

    # Compute frequency form for two axes. Also, since row order determines
    # rectangle order in the mosaic, ensure correct order.
    contingencies = frame.group_by(
        "country", "material", "role", "metric", "metric_order",
        "data_year",
        x_axis, y_axis,
        maintain_order=True
    ).agg(
        pl.col("count").sum().round().cast(pl.Int64),
    ).with_columns(
        # We achieve custom sort orders by mapping values to integers.
        pl.col(x_axis).replace({
            value: key for key, value in enumerate(index[x_axis])
        }).alias("x_order"),
        pl.col(y_axis).replace({
            value: key for key, value in enumerate(index[y_axis])
        }).alias("y_order"),
    ).sort(
        "metric_order", "data_year", "x_order", "y_order"
    )

    # contingencies = regularize_age_distribution(
    #     contingencies,
    #     "metric",
    #     "data_year",
    #     x_axis,
    #     y_axis,
    # )

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
    stroke_expr = _make_stroke_expr([x_axis, y_axis], include_null)
    fill_expr = _make_fill_expr([x_axis, y_axis], highlights, include_null)

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

    if show_counts:
        labels = []
        for x, y in ((1, 1), (1, 2), (2, 1), (2, 2)):
            labels.append(
                pl.when(
                    (
                        pl.col("x1").eq(0) if x == 1
                        else pl.col("x2").eq(pl.col("x_scale"))
                    ).and_(
                        pl.col("y1").eq(0) if y == 1
                        else pl.col("y2").eq(pl.col("y_scale"))
                    ).and_(
                        pl.col("count").gt(0)
                    )
                ).then(
                    pl.col("count")
                        .cast(pl.String)
                        .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
                ).otherwise(
                    pl.lit("", dtype=pl.String)
                ).alias(f"label{x}{y}")
            )

        expr = _make_highlight_expr([x_axis, y_axis], highlights)
        labels.append(
            pl.lit(Palette.BLACK, dtype=pl.String) if expr is None else expr.otherwise(
                pl.lit(Palette.BLACK, dtype=pl.String)
            ).alias("label_color")
        )

        mosaic_frame = mosaic_frame.with_columns(*labels)

    # Clean up data frame by dropping unneeded columns and arranging remaining
    # columns in meaningful order.
    mosaic_frame = mosaic_frame.select(
        "country", "material", "role", "metric",
        "data_year",
        x_axis, y_axis,
        "count",
        "x1", "x2", "normalized_x1", "normalized_x2", "x_scale",
        "y1", "y2", "normalized_y1", "normalized_y2", "y_scale",
        *(
            ["label11", "label12", "label21", "label22", "label_color"] if show_counts
            else []
        ),
    ).with_columns(
        stroke_expr,
        fill_expr,
    )

    return mosaic_frame


def test_chi2_independence(
    frame: pl.DataFrame,
    x_axis: str,
    y_axis: str,
) -> pl.DataFrame:
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
        group = group.select(
            x_axis, y_axis, "count"
        ).drop_nulls(
            [x_axis, y_axis]
        )

        # Is χ² safe to use?
        use_chi2 = group.select(
            pl.col("count").ge(5).all()
        ).item()

        if not use_chi2 or group.height < 2:
            chi2s.append(None)
            p_values.append(None)
            ratings.append("" if group.height < 2 else "N/A")
            continue

        # Extract group data as contingency table
        table = group.pivot(
            on=x_axis,
            values="count",
        ).drop(
            y_axis
        ).to_numpy(
            order="c",
            structured=False,
        )

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
                    y=325 if y == 1 else -5,
                    align="left" if x== 1 else "right",
                    baseline="top" if y == 1 else "bottom",
                    fontSize=30,
                ).encode(
                    alt.Text(f"label{x}{y}:N"),
                    alt.Color("label_color:N", legend=None).scale(None)
                ))

        if show_ratings:
            labels.append(base.mark_text(
                x=160,
                y=-5,
                align="center",
                baseline="bottom",
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
        hrule(10),
        *rows,
        spacing=row_gap,
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
