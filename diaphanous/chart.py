import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id
from .util import arrange_age_distribution

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
        ).alias(Id.GROUP)
    )

    null_age = frame.group_by(
        pl.col("data_year")
    ).agg(
        pl.lit(None).alias("age_too"),
        pl.lit("Unknown").alias("age_group"),
        pl.lit(None).alias("group_rank"),
        pl.lit(None).alias("sex"),
        pl.lit(None).alias("activity"),
        pl.col("age").is_null().sum().cast(pl.Float64).alias("count"),
    ).rename({
        "age_too": "age",
    }).pipe(
        arrange_age_distribution
    )

    data = pl.concat([data, null_age])

    domain = [
        "Unknown Sex",
        "Female Child", "Female Adolescent", "Female Adult",
        "Male Child", "Male Adolescent", "Male Adult",
    ]

    range = [
        "#555",
        Palette.ORANGE, Palette.RED, Palette.PINK,
        Palette.LIGHT_BLUE, Palette.BLUE, Palette.PURPLE,
    ]

    chart = alt.Chart(
        data,
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

    # label = chart.mark_text(
    #     x="width",
    #     dx=-10,
    #     dy=100,
    #     align="right",
    #     baseline="bottom",
    #     text=[f"{no_age:,} Offenders", "Without Age"],
    #     color=Palette.GRAY,
    # )

    return chart

def plot_age_and_supply(
    frame: pl.DataFrame, entity: str, country: str
) -> alt.Chart:
    domain = [
        "Child Consumer", "Adolescent Consumer", "Adult Consumer",
        "Child Producer", "Adolescent Producer", "Adult Producer",
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


if __name__ == "__main__":
    from .aunz import au_age_distribution, nz_age_distribution
    from .bka import Data as bka
    from .nibrs import load_all

    print(au_age_distribution())
    print(bka.ingest().age_distribution())
    print(nz_age_distribution())
    print(load_all().offender_demographics().age_distribution())
