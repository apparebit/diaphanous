import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id
from .util import to_step_and_limit

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

    ystep, ymax = to_step_and_limit(frame.group_by(
        "data_year", "age"
    ).agg(
        pl.col("count").sum()
    ).select(
        pl.col("count").max()
    ).item())

    yaxis = alt.Axis(
        labelExpr=(
            f'datum.value==0 || datum.value=={ymax} ? format(datum.value, ",d") : ""'
        ),
        tickMinStep=ystep,
        orient="right",
    )

    return alt.Chart(
        data,
        title=alt.Title(
            country,
            anchor="middle",
            orient="left",
            angle=270,
            fontSize=40,
            fontWeight="normal",
            dx=0,
        ),
    ).mark_bar().encode(
        alt.X("age:Q", axis=alt.Axis(labels=False))
            .scale(domain=(0, 100))
            .title(None),
        alt.Y("sum(count):Q", axis=yaxis, sort=domain)
            .scale(domain=(0, ymax))
            .title(None),
        alt.Color("age_group:N", legend=None)
            .scale(domain=domain, range=range),
        alt.Order("color_variant_label_sort_index:Q"),
        alt.Column(
            "data_year:N",
            title=None,
            header=alt.Header(
                labelAnchor="middle",
                labelOrient="bottom",
                labelFontSize=40,
            ) if facet_labels else alt.Header(labels=False),
        ),
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
