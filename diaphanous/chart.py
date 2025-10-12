import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id

def plot_age_and_sex(
    frame: pl.DataFrame, entity: str, country: str
) -> alt.Chart:
    frame = frame.with_columns(
        pl.when(
            pl.col("sex").is_null()
        ).then(
            pl.lit("Unknown Sex")
        ).otherwise(
            pl.format("{} {}", pl.col("sex"), pl.col(Id.GROUP))
        ).alias(Id.GROUP)
    )

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
        pl.format("{} {}", pl.col(Id.GROUP), pl.col("supply")).alias(Id.GROUP)
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
