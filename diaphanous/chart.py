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
        Palette.ORANGE, Palette.RED, Palette.PINK,
        "#555",
        Palette.LIGHT_BLUE, Palette.BLUE, Palette.PURPLE,
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
        # Form group label by combining sex and age group
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP),
        # Format the total with thousands separator
        pl.col("count")
            .sum()
            .over("data_year")
            .round()
            .cast(pl.Int64)
            .cast(pl.String)
            .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
            .alias("population"),
        # Determine the number of female offenders/arrestees
        pl.col("count")
            .filter(pl.col("age").is_not_null().and_(pl.col("sex").eq("Female")))
            .sum()
            .over("data_year")
            .alias("female_population"),
        # Determine the age of majority
        pl.when(
            pl.col("country").eq("New Zealand"),
        ).then(
            pl.lit(20, dtype=pl.Int16),
        ).otherwise(
            pl.lit(18, dtype=pl.Int16),
        ).alias("age_of_majority"),
    ).with_columns(
        # Format the "N=<n>" label
        pl.format("N={}", pl.col("population")).alias("N_annotation"),
        # Compute the number of female offenders below the age of majority
        pl.col("count")
            .filter(
                pl.col("age").lt(pl.col("age_of_majority")).and_(
                    pl.col("sex").eq("Female")
                )
            ).sum()
            .over("data_year")
            .alias("female_minors"),
    ).with_columns(
        # Determine the percentage fraction of minor female offenders
        pl.col("female_minors")
            .truediv(pl.col("female_population"))
            .mul(100)
            .round(1)
            .alias("female_minors"),
    ).with_columns(
        # Format the "fm=<p>%"" label
        pl.when(
            pl.col("female_minors").is_nan()
        ).then(
            pl.lit("fm=—", dtype=pl.String)
        ).otherwise(
            pl.col("female_minors").map_elements(
                lambda el: f"fm={el:.1f}%"
            )
        ).alias("fm_annotation")
    )

    domain = [
        "Female Child", "Female Juvenile", "Female Adult",
        "Unknown Sex",
        "Male Child", "Male Juvenile", "Male Adult",
    ]

    range = [
        Palette.RED, Palette.RED, "#aaaeb6",
        "#aaaeb6",
        Palette.BLUE, Palette.BLUE, "#aaaeb6",
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
        "N_annotation", "fm_annotation",
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
            alt.Text("N_annotation:N")
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
            alt.Text("fm_annotation:N")
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


def plot_thumb_rule(width: int) -> alt.Chart:
    """Create a horizontal rule as a chart for separating rows of thumbs."""
    return alt.Chart().mark_rule(
        strokeWidth=width
    ).encode(
        alt.YDatum(0).axis(None)
    ).properties(
        width=3_230,
        height=5,
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
