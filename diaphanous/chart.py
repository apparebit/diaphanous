from collections.abc import Sequence
from typing import Literal

import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id
from .util import (
    compute_age_sex_cdf_extrema, get_year_range, grouping_columns, to_axis_range
)


def _prep_sex_by_age(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.group_by(
        "country", "material", "role", "data_year", "age", "age_group", "sex"
    ).agg(
        pl.col("count").sum(),
    ).with_columns(
        pl.col("count").filter(
            pl.col("sex").eq("Female")
        ).sum().add(
            pl.col("count").filter(
                pl.col("sex").is_null()
            ).sum().truediv(2)
        ).mul(-1).over("data_year", "age").alias("minimum"),

        pl.col("count").filter(
            pl.col("sex").eq("Male")
        ).sum().add(
            pl.col("count").filter(
                pl.col("sex").is_null()
            ).sum().truediv(2)
        ).over("data_year", "age").alias("maximum"),

        pl.when(
            pl.col("sex").eq("Female")
        ).then(
            pl.lit(-1)
        ).when(
            pl.col("sex").is_null()
        ).then(
            pl.lit(0)
        ).otherwise(
            pl.lit(1)
        ).cast(pl.Int8).alias("sex_order"),
    ).sort(
        "data_year", "age", "sex_order"
    ).with_columns(
        pl.col("count").cum_sum().add(
            pl.col("minimum")
        ).over(
            "data_year", "age", order_by="sex_order"
        ).alias("range_stop")
    ).with_columns(
        pl.col("range_stop").sub(pl.col("count")).alias("range_start")
    )


def plot_sex_by_age_detailed(
    frame: pl.DataFrame, country: str, material: str, role: str
) -> alt.Chart | alt.LayerChart | alt.FacetChart:
    data = _prep_sex_by_age(frame).with_columns(
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP),
        pl.lit("", dtype=pl.String).alias("label"),
    ).select(
        "country", "material", "role",
        "data_year",
        "age", "age_group",
        "range_start", "range_stop", "count",
        "label",
    )

    def fmt(n):
        num = int(n)
        return (
            "" if num == 0 else
            f"Not shown: {num:,} {role}{"" if num == 1 else "s"} Without Age"
        )

    columns = grouping_columns(frame)
    labels = frame.group_by(
        pl.col(*columns)
    ).agg(
        pl.col("count").filter(pl.col("age").is_null()).sum()
    ).select(
        pl.col(*columns),
        *(
            pl.lit(None).alias(c) for c in [

                "age", "age_group",
                "range_start", "range_stop", "count",
            ]
        ),
        pl.col("count").map_elements(fmt).alias("label"),
    )

    data = pl.concat([data, labels])

    domain = [
        "Female Child", "Female Juvenile", "Female Adult",
        "Unknown Sex",
        "Male Child", "Male Juvenile", "Male Adult",
    ]

    range = [
        Palette.PINK, Palette.RED, Palette.LIGHT_GRAY,
        Palette.BLACK,
        Palette.LIGHT_BLUE, Palette.BLUE, Palette.LIGHT_GRAY,
    ]

    right_side = alt.Axis(
        labelExpr = 'format(datum.value < 0 ? -datum.value : datum.value, ",d")',
        orient="right",
    )

    base = alt.Chart(data)

    chart = base.mark_bar(size=4).encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("range_start:Q", axis=right_side).title(None),
        alt.Y2("range_stop:Q"),
        alt.Color("age_group:N")
            .title("Sex and Age Group")
            .scale(domain=domain, range=range),
    ).properties(
        width=440,
        height=220,
    )

    rule = base.mark_rule().encode(
        alt.YDatum(0)
    )

    label = alt.Chart(
        data,
    ).mark_text(
        x="width",
        y=20,
        dx=-10,
        align="right",
        fontSize=14,
        fontStyle="italic",
    ).encode(
        alt.Text("label:N", title=None)
    )

    return alt.layer(chart, rule, label).facet(
        facet=alt.Facet("data_year:N", title="Year"),
        title=alt.Title(
            f"{country}: {material} {role}s",
            anchor="middle",
            orient="left",
            angle=270,
            fontSize=15,
            subtitle="Women (down) and Men (up)",
            subtitleFontSize=14,
        ),
    )


def plot_sex_by_age(
    frame: pl.DataFrame,
    country: str,
    material: Literal["Porn", "CSAM"],
    role: Literal["Suspect", "Offender", "Arrestee"],
    facet_labels: bool = False
) -> alt.Chart | alt.LayerChart | alt.FacetChart:
    data = _prep_sex_by_age(frame).with_columns(
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP),

        pl.col("count").filter(
            pl.col("age").is_not_null()
        ).sum().over("data_year").round().cast(pl.Int64).alias("with_age"),
        pl.col("count").filter(
            pl.col("age").is_null()
        ).sum().over("data_year").round().cast(pl.Int64).alias("without_age"),
    ).with_columns(
        pl.col("with_age")
            .cast(pl.String)
            .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
            .alias("total_shown"),
        pl.when(
            pl.col("without_age").eq(0)
        ).then(
            pl.lit(None)
        ).otherwise(
            pl.col("without_age")
                .cast(pl.String)
                .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
        ).alias("not_shown")
    ).with_columns(
        pl.when(
            pl.col("with_age").gt(0)
        ).then(
            pl.format("N={}", pl.col("total_shown"))
        ).otherwise(
            pl.lit("N/A", dtype=pl.String)
        ).alias("total_shown"),
        pl.when(
            pl.col("not_shown").is_not_null()
        ).then(
            pl.format("{} w/o Age", pl.col("not_shown"))
        ).otherwise(
            pl.lit("")
        ).alias("not_shown")
    )

    domain = [
        "Female Child", "Female Juvenile", "Female Adult",
        "Unknown Sex",
        "Male Child", "Male Juvenile", "Male Adult",
    ]

    range = [
        Palette.RED, Palette.RED, Palette.LIGHT_GRAY,
        Palette.BLACK,
        Palette.BLUE, Palette.BLUE, Palette.LIGHT_GRAY,
    ]

    actual_min, actual_max = data.filter(
        pl.col("age").is_not_null()
    ).select(
        pl.col("minimum").min(),
        pl.col("maximum").max()
    ).row(0)

    ymin, ystep, ymax = to_axis_range(actual_min, actual_max)
    #print(f">>>>> {actual_min}| from {ymin:,} by {ystep:,} to {ymax:,} | {actual_max}")

    data = data.select(
        "data_year",
        "age", "age_group",
        "range_start", "range_stop",
        "total_shown", "not_shown",
    )

    yaxis = alt.Axis(
        labelExpr=(
            f'datum.value=={ymin} || datum.value==0 || datum.value=={ymax} ? '
            'format(datum.value < 0 ? -datum.value : datum.value, ",d") : ""'
        ),
        tickMinStep=ystep,
        orient="right",
    )

    base = alt.Chart(data)

    return alt.layer(
        base.mark_bar().encode(
            alt.X("age:Q", axis=None) # alt.Axis(labels=False, tickWidth=0))
                .scale(domain=(0, 100))
                .title(None),
            alt.Y("range_start:Q", axis=yaxis)
                .scale(domain=(ymin, ymax))
                .title(None),
            alt.Y2("range_stop:Q")
                .title(None),
            alt.Color("age_group:N", legend=None)
                .scale(domain=domain, range=range),
        ),
        base.mark_text(
            x="width",
            y=25,
            dx=-20,
            align="right",
            fontSize=30,
            fontStyle="italic",
            fontWeight="lighter",
        ).encode(
            alt.Text("total_shown:N")
        ),
        base.mark_text(
            x="width",
            y=60,
            dx=-20,
            align="right",
            fontSize=30,
            fontStyle="italic",
            fontWeight="lighter",
        ).encode(
            alt.Text("not_shown:N")
        ),
        base.mark_rule(strokeWidth=1.5).encode(
            alt.YDatum(0)
        )
    ).facet(
        column=alt.Column(
            "data_year:N",
            title=None,
            header=alt.Header(
                labelAnchor="middle",
                labelOrient="bottom",
                labelFontSize=40,
            ) if facet_labels else alt.Header(labels=False),
        ),
        title=alt.Title(
            country,
            anchor="middle",
            orient="left",
            angle=270,
            fontSize=40,
            fontWeight="normal",
            dx=0,
            subtitle=f"{material} {role}s",
            subtitleFontSize=35,
        ),
    )


def plot_cdf_grid(
    frame: pl.DataFrame,
    cell_width: float = 500,
    cell_height: float = 350,
    column_count: int = 5,
    gap: float = 20,
) -> alt.VConcatChart:
    group_iter = frame.group_by("country", "material", "role", maintain_order=True)
    grid = []

    for index, (labels, group) in enumerate(group_iter):
        if index % column_count == 0:
            grid.append([])
            grid.append([])

        country = labels[0]
        material_role = f"{labels[1]} {labels[2]}s"

        grid[-2].append(_plot_age_sex_cdfs(group, country, material_role).properties(
            width=cell_width,
            height=cell_height,
        ))
        grid[-1].append(_plot_age_sex_cdf_bands(group, country).properties(
            width=cell_width,
            height=cell_height,
        ))

    return alt.vconcat(
        alt.Chart().mark_rule(strokeWidth=7.5).encode(
            alt.YDatum(0).axis(None)
        ).properties(
            width=column_count * cell_width + (column_count - 1) * gap,
            height=5,
        ),
        *(alt.hconcat(*row) for row in grid),
    ).resolve_scale(
        x="shared",
    ).properties(
        title=alt.Title(
            "Cumulative Distributions of Male/Female Perpetrators "
            "by Age, Year, and Country",
            fontSize=40,
            fontWeight="bold",
            anchor="start",
            frame="group",
            dx=0,
            dy=-10,
        )
    )


def plot_hrule(
    stroke: Literal["thin", "regular"] | float = "regular",
    width: Literal["pyramid", "mosaic"] | int = "pyramid",
) -> alt.Chart:
    """Create a horizontal rule as a chart for separating rows of thumbs."""
    if stroke == "thin":
        stroke = 7.5
    elif stroke == "regular":
        stroke = 10

    if width == "pyramid":
        width = 3_235
    elif width == "mosaic":
        width = 3_200

    return alt.Chart().mark_rule(
        strokeWidth=stroke,
    ).encode(
        alt.YDatum(0).axis(None)
    ).properties(
        width=width,
        height=5,
    )


def _plot_age_sex_cdfs(
    frame: pl.DataFrame, country: str, material_role: str
) -> alt.LayerChart:
    return alt.layer(
        _plot_cdf(frame, column="male_cdf", colors=f"{Palette.BLUE}80"),
        _plot_cdf(frame, column="female_cdf", colors=f"{Palette.RED}80"),
        alt.Chart().mark_rule(color=Palette.BLACK, strokeWidth=4).encode(
            alt.XDatum(20 if country == "New Zealand" else 18)
        ),
        title=alt.Title(
            country,
            subtitle=material_role,
            anchor="middle",
            orient="top",
            fontSize=30,
            fontWeight="normal",
            subtitleFontSize=25,
        )
    ).resolve_scale(
        color="independent",
    )


def _plot_cdf(
    frame: pl.DataFrame,
    column: str,
    colors: str | Sequence[str],
) -> alt.Chart:
    year_min, year_max = get_year_range(frame)
    if isinstance(colors, str):
        colors = [colors] * (year_max - year_min)

    return alt.Chart(frame).mark_line().encode(
        alt.X("age:Q", axis=alt.Axis(labels=False)).title(None),
        alt.Y(f"{column}:Q", axis=alt.Axis(labels=False)).title(None),
        alt.Color("data_year:N", legend=None).scale(
            domain=[y for y in range(year_min, year_max)], range=colors
        ),
    )


def _plot_age_sex_cdf_bands(
    frame: pl.DataFrame, country: str
) -> alt.LayerChart:
    extrema = compute_age_sex_cdf_extrema(frame)
    return alt.layer(
        _plot_cdf_band(extrema, "male_cdf", color=f"{Palette.BLUE}80"),
        _plot_cdf_band(extrema, "female_cdf", color=f"{Palette.RED}80"),
        alt.Chart().mark_rule(color=Palette.BLACK, strokeWidth=4).encode(
            alt.XDatum(20 if country == "New Zealand" else 18)
        ),
    )


def _plot_cdf_band(
    frame: pl.DataFrame,
    column: str,
    color: str,
) -> alt.Chart:
    return alt.Chart(frame).mark_area(
        color=color,
    ).encode(
        alt.X("age:Q", axis=alt.Axis(labels=False)).title(None),
        alt.Y(f"min_{column}:Q", axis=alt.Axis(labels=False)).title(None),
        alt.Y2(f"max_{column}:Q"),
    )


def plot_age_and_supply(
    frame: pl.DataFrame, country: str, material: str, role: str
) -> alt.Chart:
    domain = [
        "Child Consumer", "Juvenile Consumer", "Adult Consumer",
        "Child Producer", "Juvenile Producer", "Adult Producer",
    ]

    range = [
        Palette.ORANGE, Palette.RED, Palette.PINK,
        Palette.LIGHT_BLUE, Palette.BLUE, Palette.PURPLE,
    ]

    frame = frame.with_columns(
        pl.format("{} {}", pl.col(Id.GROUP), pl.col("activity")).alias(Id.GROUP)
    ).sort(
        Id.YEAR, Id.GROUP
    )

    return alt.Chart(
        frame,
        title=f"{material} {role}s by Age: {country}"
    ).mark_bar().encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("sum(count):Q", sort=domain).title(f"{material} {role}s"),
        alt.Color("age_group:N")
            .title("Sex and Age Group")
            .scale(domain=domain, range=range),
        alt.Column("data_year:N").title("Year"),
        alt.Order("color_variant_label_sort_index:Q"),
    ).properties(
        width=550,
        height=250,
    )
