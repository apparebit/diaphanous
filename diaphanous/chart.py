from collections.abc import Sequence
from typing import Literal

import altair as alt
import polars as pl

from .color import Palette, Scale
from .nibrs.model import Id
from .util import (
    compute_age_sex_cdf_extrema, get_year_range, hrule, to_axis_range
)


def _prep_sex_by_age(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.group_by(
        "country", "material", "role",
        "data_year",
        "age", "age_group", "sex", "sex_order",
        maintain_order=True,
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

    labels = frame.group_by(
        "country", "material", "role", "data_year", maintain_order=True
    ).agg(
        pl.col("count").filter(pl.col("age").is_null()).sum()
    ).select(
        "country", "material", "role", "data_year",
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


def plot_sex_by_age_grid(frame: pl.DataFrame) -> alt.VConcatChart:
    group_iter = frame.group_by("country", "material", "role", maintain_order=True)
    rows = []

    for labels, group in group_iter:
        country, material, role = labels
        with_label = (
            country == "United States" and material == "Porn" and role == "Arrestee"
        )
        rows.append(
            plot_sex_by_age(group, country, material, role, facet_labels=with_label)
        )

    return alt.vconcat(
        hrule(7.5),
        *rows,
        spacing=15
    ).resolve_scale(
        x="shared"
    ).configure_axis(
        labelFontSize=35,
        titleFontSize=40,
    ).properties(
        title=alt.Title(
            "Perpetrators by Age (0→100), Sex (Female↓, Male↑), "
            "Year (2015⇒2024), and Country",
            fontSize=45,
            fontWeight="bold",
            anchor="start",
            frame="group",
            dx=0,
            dy=-10,
            subtitle=(
                "With Female Minors in Red, Male Minors in Blue, and "
                "People w/o Sex in Black"
            ),
            subtitleFontSize=40,
        )
    )


def plot_sex_by_age(
    frame: pl.DataFrame,
    country: str,
    material: Literal["Porn", "CSAM"],
    role: Literal["Suspect", "Offender", "Arrestee"],
    facet_labels: bool = False,
) -> alt.FacetChart:
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
            pl.format("+{} w/o age", pl.col("not_shown"))
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
            y=24,
            dx=-5,
            align="right",
            fontSize=28,
            #fontStyle="italic",
            fontWeight="lighter",
        ).encode(
            alt.Text("total_shown:N")
        ),
        base.mark_text(
            x="width",
            y=58,
            dx=-5,
            align="right",
            fontSize=28,
            #fontStyle="italic",
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
    cell_small_height: float = 250,
    column_count: int = 5,
    gap: float = 20,
    small_gap: float = 5,
) -> alt.VConcatChart:
    group_iter = frame.group_by("country", "material", "role", maintain_order=True)
    grid = []

    for index, (labels, group) in enumerate(group_iter):
        if index % column_count == 0:
            if 0 < index:
                grid.append(hrule(gap - small_gap, color="#ffffff"))
            grid.append([])
            grid.append([])

        country = labels[0]
        material_role = f"{labels[1]} {labels[2]}s"

        grid[-2].append(_plot_age_sex_cdfs(group, country, material_role).properties(
            width=cell_width,
            height=cell_height,
        ))
        grid[-1].append(_plot_age_sex_bands(group, country, material_role).properties(
            width=cell_width,
            height=cell_small_height,
        ))

    rows = [
        (alt.hconcat(*row, spacing=gap) if isinstance(row, list) else row)
        for row in grid
    ]

    return alt.vconcat(
        hrule(7.5),
        *rows,
        spacing=small_gap
    ).resolve_scale(
        x="shared",
    ).properties(
        title=alt.Title(
            "Yearly Cumulative Distributions for Male/Female Perpetrators "
            "by Age and Country",
            fontSize=40,
            fontWeight="bold",
            anchor="start",
            frame="group",
            dx=0,
            dy=-10,
        )
    )


def _plot_age_sex_cdfs(
    frame: pl.DataFrame, country: str, material_role: str
) -> alt.LayerChart:
    male_colors = Scale.BLUE.value
    female_colors = Scale.RED.value
    if country == "Australia":
        male_colors = male_colors[7]
        female_colors = female_colors[7]

    return alt.layer(
        _plot_cdf(frame, column="male_cdf", colors=male_colors),
        _plot_cdf(frame, column="female_cdf", colors=female_colors),
        alt.Chart().mark_rule(
            color=Palette.BLACK,
            strokeWidth=4,
            strokeDash=(4, 2),
        ).encode(
            alt.XDatum(20 if country == "New Zealand" else 18)
        ),
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


def _plot_age_sex_bands(
    frame: pl.DataFrame, country: str, material_role: str
) -> alt.LayerChart:
    extrema = compute_age_sex_cdf_extrema(frame)
    return alt.layer(
        _plot_cdf_band(extrema, "male_cdf", color=f"{Scale.BLUE.value[6]}80"),
        _plot_cdf_band(extrema, "female_cdf", color=f"{Scale.RED.value[4]}80"),
        alt.Chart().mark_rule(
            color=Palette.BLACK,
            strokeWidth=4,
            strokeDash=(4, 2),
        ).encode(
            alt.XDatum(20 if country == "New Zealand" else 18)
        ),
        title=alt.Title(
            country,
            subtitle=material_role,
            anchor="middle",
            orient="bottom",
            fontSize=30,
            fontWeight="normal",
            subtitleFontSize=25,
        )
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
