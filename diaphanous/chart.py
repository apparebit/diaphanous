from collections.abc import Iterable
from typing import Literal

import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id
from .util import (
    compute_sex_and_age_cdf_extrema, get_year_range, grouping_columns, to_axis_range
)

def _trace(frame: pl.DataFrame) -> pl.DataFrame:
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_rows(200)
    print(frame.select(
        pl.exclude("country", "material", "role", "activity")
    ))
    return frame

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


def plot_age_and_sex(
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

def plot_age_thumbs(
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
        pl.col("count").sum().over("data_year").round().cast(pl.Int64).alias("total"),
    ).with_columns(
        pl.col("with_age")
            .cast(pl.String)
            .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
            .alias("anno1"),
        pl.when(
            pl.col("total").eq(pl.col("with_age"))
        ).then(
            pl.lit(None)
        ).otherwise(
            pl.col("total")
                .cast(pl.String)
                .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
        ).alias("anno2")
    ).with_columns(
        pl.format("N={}", pl.col("anno1")).alias("anno1"),
        pl.when(
            pl.col("anno2").is_not_null()
        ).then(
            pl.format("of {}", pl.col("anno2"))
        ).otherwise(
            pl.lit("")
        ).alias("anno2")
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
        "anno1", "anno2",
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
            alt.Text("anno1:N")
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
            alt.Text("anno2:N")
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


def plot_thumb_rule(
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


_GAP = 3.0

def plot_age_sex_mosaics(
    frame: pl.DataFrame,
    country: str,
    material: Literal["Porn", "CSAM"],
    role: Literal["Suspect", "Offender", "Arrestee"],
    facet_labels: bool = False
) -> alt.FacetChart:
    frame = frame.group_by(
        "country", "material", "role", "data_year", maintain_order=True
    ).agg(
        pl.lit(0.0, dtype=pl.Float64).alias("0%"),
        pl.lit(100.0 + _GAP, dtype=pl.Float64).alias("100%"),
        pl.col("minors_pct").first().alias("minors_end"),
        pl.col("minors_pct").first().add(_GAP).alias("minors_start"),
        pl.col("female_minors_pct").first(),
        pl.col("female_adults_pct").first(),
        pl.col("male_minors_pct").first().neg().add(100.0 + _GAP),
        pl.col("male_adults_pct").first().neg().add(100.0 + _GAP),

        pl.col("minors_pct").first().add(_GAP).add(
            pl.col("minors_pct").first().neg().add(100).truediv(2)
        ).alias("male_adults_x"),
        pl.col("male_adults_pct").truediv(2).neg().add(100.0 + _GAP)
            .alias("male_adults_y"),
        pl.col("male_adults_pct").map_elements(
            lambda v: [f"{v:.1f}% of", "Adults"],
            return_dtype=pl.List(pl.String),
        ).alias("male_adults_text"),

        pl.col("minors_pct").first().truediv(2).alias("female_minors_x"),
        pl.col("female_minors_pct").first().truediv(2).alias("female_minors_y"),
        pl.when(
            pl.col("minors_pct").first().mul(pl.col("female_minors_pct").first())
            .ge(800)
        ).then(
            pl.col("female_minors_pct").first().map_elements(
                lambda v: f"{v:.1f}%", return_dtype=pl.String
            )
        ).otherwise(
            pl.lit("", dtype=pl.String)
        ).alias("female_minors_text"),
        pl.when(
            pl.col("minors_pct").first().mul(pl.col("female_minors_pct").first())
            .lt(800)
        ).then(
            pl.col("female_minors_pct").first().map_elements(
                lambda v: f"{v:.1f}%", return_dtype=pl.String
            )
        ).otherwise(
            pl.lit("", dtype=pl.String)
        ).alias("female_minors_alt_text"),

        pl.col("minors_pct").map_elements(
            lambda v: f"Minors={v:.1f}%",
            return_dtype=pl.String,
        ).alias("marginal_minors_text"),
    ).select(
        pl.col("country", "material", "role", "data_year"),
        pl.concat_list("0%", "minors_start", "0%", "minors_start").alias("x1"),
        pl.concat_list("minors_end", "100%", "minors_end", "100%").alias("x2"),
        pl.concat_list(
            "0%", "0%", "male_minors_pct", "male_adults_pct"
        ).alias("y1"),
        pl.concat_list(
            "female_minors_pct", "female_adults_pct", "100%", "100%"
        ).alias("y2"),
        pl.lit([
            "female_minors", "female_adults", "male_minors", "male_adults"
        ], dtype=pl.List(pl.String)).alias("category"),
        pl.col(
            "male_adults_x", "male_adults_y", "male_adults_text",
            "female_minors_x", "female_minors_y", "female_minors_text",
            "female_minors_alt_text",
            "marginal_minors_text"
        ),
    ).explode(
        "x1", "x2", "y1", "y2", "category"
    )

    base = alt.Chart(frame)
    return alt.layer(
        base.mark_rect(
            stroke="black",
            strokeWidth=2,
        ).encode(
            alt.X("x1:Q", axis=None).scale(domain=(0, 100 + _GAP)),
            alt.X2("x2:Q"),
            alt.Y("y1:Q", axis=None).scale(domain=(0, 100 + _GAP)).title(None),
            alt.Y2("y2:Q"),
            alt.Color("category:N", legend=None).scale(
                domain=["male_minors", "male_adults", "female_minors", "female_adults"],
                range=[
                    f"{Palette.BLUE}a0",
                    "#aaaeb6a0",
                    f"{Palette.RED}a0",
                    "#aaaeb6a0"
                ],
            )
        ),
        base.mark_text(
            align="center",
            baseline="middle",
            fontSize=25,
            fontStyle="italic",
        ).encode(
            alt.X("male_adults_x:Q"),
            alt.Y("male_adults_y:Q"),
            alt.Text("male_adults_text:N"),
        ),
        base.mark_text(
            align="center",
            baseline="middle",
            fontSize=25,
            fontStyle="italic",
        ).encode(
            alt.X("female_minors_x:Q"),
            alt.Y("female_minors_y:Q"),
            alt.Text("female_minors_text:N"),
        ),
        base.mark_text(
            x=0,
            y=310,
            align="left",
            baseline="top",
            fontSize=25,
            fontStyle="italic",
            color="#b22817",
        ).encode(
            alt.Text("female_minors_alt_text:N"),
        ),
        base.mark_text(
            x=0,
            y=10,
            align="left",
            baseline="bottom",
            fontSize=30,
            fontStyle="italic",
        ).encode(
            alt.Text("marginal_minors_text:N"),
        ),
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


def plot_sex_and_age_cdfs(
    frame: pl.DataFrame, title: None | str = None, rule: None | int = None
) -> alt.LayerChart:
    layers = [
        plot_cdf(frame, column="cdf", title=title, colors=f"{Palette.BLUE}80"),
        plot_cdf(frame, column="female_cdf", title=title, colors=f"{Palette.RED}80"),
    ]

    if rule is not None:
        layers.append(alt.Chart().mark_rule(
            color=Palette.GRAY,
            strokeWidth=3,
            strokeDash=(4, 2),
        ).encode(
            alt.XDatum(rule)
        ))

    return alt.layer(*layers).resolve_scale(
        color="independent"
    )


def plot_cdf(
    frame: pl.DataFrame,
    column: str = "cdf",
    title: None | str = None,
    colors: None | str | Iterable[str] = None,
) -> alt.Chart:
    year_min, year_max = get_year_range(frame)
    if colors is None:
        colors = [f"{Palette.BLUE}80"] * (year_max - year_min)
    elif isinstance(colors, str):
        colors = [colors] * (year_max - year_min)
    assert isinstance(colors, list)

    return (
        alt.Chart(frame) if title is None else alt.Chart(frame, title=title)
    ).mark_line().encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y(f"{column}:Q").scale(domain=(0, 1)).title("CDF"),
        alt.Color("data_year:N", legend=None).scale(
            domain=[y for y in range(year_min, year_max)], range=colors
        ),
    ).properties(
        width=500,
        height=300,
    )


def plot_sex_and_age_cdf_bands(
    frame: pl.DataFrame,
    title: None | str = None,
    color_all: str = Palette.BLUE,
    color_female: str = Palette.RED,
    rule: None | int = None,
) -> alt.LayerChart:
    extrema = compute_sex_and_age_cdf_extrema(frame)
    layers = [
        plot_cdf_band(extrema, "cdf", title=title, color=f"{color_all}80"),
        plot_cdf_band(extrema, "female_cdf", title=title, color=f"{color_female}80"),
    ]

    if rule is not None:
        layers.append(alt.Chart().mark_rule(
            color=Palette.GRAY,
            strokeWidth=3,
            strokeDash=(4, 2),
        ).encode(
            alt.XDatum(rule)
        ))

    return alt.layer(*layers)


def plot_cdf_band(
    frame: pl.DataFrame,
    column: str = "cdf",
    title: None | str = None,
    color: None | str = None,
) -> alt.Chart:
    return (
        alt.Chart(frame) if title is None else alt.Chart(frame, title=title)
    ).mark_area(color=color or f"{Palette.BLUE}80").encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y(f"min_{column}:Q").scale(domain=(0, 1)).title("CDF"),
        alt.Y2(f"max_{column}:Q"),
    ).properties(
        width=500,
        height=300,
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
