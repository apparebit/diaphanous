from collections.abc import Iterable

import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id
from .util import compute_sex_and_age_cdf_extrema, get_year_range, to_step_and_limit

def plot_age_and_sex(
    frame: pl.DataFrame, entity: str, country: str
) -> alt.Chart | alt.LayerChart | alt.FacetChart:
    data = frame.with_columns(
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP),
        pl.lit("", dtype=pl.String).alias("label"),
    )

    def fmt(n):
        num = int(n)
        return (
            "" if num == 0 else
            f"Not shown: {num:,} {entity[:-1] if num == 1 else entity} Without Age"
        )

    columns = []
    if "country" in frame.columns:
        columns.append("country")
    if "entity" in frame.columns:
        columns.append("entity")
    columns.append("data_year")

    labels = frame.group_by(
        pl.col(*columns)
    ).agg(
        pl.col("count").filter(pl.col("age").is_null()).sum()
    ).select(
        pl.col(*columns),
        *(
            pl.lit(None).alias(c) for c in [
                "age", "age_group", "group_rank",
                "sex", "ethnicity", "activity",
                "count"
            ]
        ),
        pl.col("count").map_elements(fmt).alias("label"),
    )

    data = pl.concat([data, labels])

    domain = [
        "Unknown Sex",
        "Female Child", "Female Juvenile", "Female Adult",
        "Male Child", "Male Juvenile", "Male Adult",
    ]

    range = [
        "#555",
        Palette.ORANGE, Palette.RED, Palette.PINK,
        Palette.LIGHT_BLUE, Palette.BLUE, Palette.PURPLE,
    ]

    chart = alt.Chart(
        data,
    ).mark_bar(size=4).encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("sum(count):Q", sort=domain).title(f"{entity}"),
        alt.Color("age_group:N")
            .title("Sex and Age Group")
            .scale(domain=domain, range=range),
        alt.Order("color_variant_label_sort_index:Q"),
    ).properties(
        width=440,
        height=220,
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

    return (chart + label).facet(
        facet=alt.Facet("data_year:N", title="Year"),
        title=f"{country}: {entity} by Age and Sex",
    )

def plot_age_thumbs(
    frame: pl.DataFrame, country: str, facet_labels: bool = True
) -> alt.Chart | alt.LayerChart | alt.FacetChart:
    data = frame.with_columns(
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP),
        pl.col("count")
            .sum()
            .over("data_year")
            .round()
            .cast(pl.Int64)
            .cast(pl.String)
            .str.replace(r"(\d+)(\d\d\d)$", "${1},${2}")
            .alias("total"),
        pl.col("count")
            .filter(pl.col("sex").eq("Female"))
            .sum()
            .over("data_year")
            .alias("fem"),
        pl.when(
            pl.col("country").eq("New Zealand"),
        ).then(
            pl.lit(20, dtype=pl.Int16),
        ).otherwise(
            pl.lit(18, dtype=pl.Int16),
        ).alias("age_of_majority"),
    ).with_columns(
        pl.format("N={}", pl.col("total")).alias("total"),
        pl.col("count")
            .filter(
                pl.col("sex").eq("Female").and_(
                    pl.col("age").lt(pl.col("age_of_majority"))
                )
            ).sum()
            .over("data_year")
            .alias("fem_juv"),
    ).with_columns(
        pl.col("fem_juv").truediv(pl.col("fem")).mul(100).round(1).alias("fem_pct"),
    ).with_columns(
        pl.when(
            pl.col("fem_pct").is_nan()
        ).then(
            pl.lit("fm=—", dtype=pl.String)
        ).otherwise(
            pl.col("fem_pct").map_elements(
                lambda el: f"fm={el:.1f}%"
            )
        ).alias("fem_fmt")
    )

    domain = [
        "Unknown Sex",
        "Female Child", "Female Juvenile", "Female Adult",
        "Male Child", "Male Juvenile", "Male Adult",
    ]

    range = [
        Palette.GRAY,
        Palette.RED, Palette.RED, Palette.RED,
        Palette.BLUE, Palette.BLUE, Palette.GRAY,
    ]

    actual_max = frame.drop_nulls(
        "age"
    ).group_by(
        "data_year", "age"
    ).agg(
        pl.col("count").sum()
    ).select(
        pl.col("count").max()
    ).item()
    ystep, ymax = to_step_and_limit(actual_max)
    # print(f">>> {actual_max} {ystep} {ymax}")

    yaxis = alt.Axis(
        labelExpr=(
            f'datum.value==0 || datum.value=={ymax} ? format(datum.value, ",d") : ""'
        ),
        tickMinStep=ystep,
        orient="right",
    )

    base = alt.Chart(
        data,
    )

    return alt.layer(
        base.mark_bar().encode(
            alt.X("age:Q", axis=alt.Axis(labels=False))
                .scale(domain=(0, 100))
                .title(None),
            alt.Y("sum(count):Q", axis=yaxis, sort=domain)
                .scale(domain=(0, ymax))
                .title(None),
            alt.Color("age_group:N", legend=None)
                .scale(domain=domain, range=range),
            alt.Order("color_variant_label_sort_index:Q"),
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
            alt.Text("total:N")
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
            alt.Text("fem_fmt:N")
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
    frame: pl.DataFrame, entity: str, country: str
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
        title=f"{entity} by Age: {country}"
    ).mark_bar().encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("sum(count):Q", sort=domain).title(f"{entity}"),
        alt.Color("age_group:N")
            .title("Sex and Age Group")
            .scale(domain=domain, range=range),
        alt.Column("data_year:N").title("Year"),
        alt.Order("color_variant_label_sort_index:Q"),
    ).properties(
        width=550,
        height=250,
    )
