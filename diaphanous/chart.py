import altair as alt
import polars as pl

from .color import Palette
from .nibrs.model import Id

def plot_age_distribution(
    frame: pl.DataFrame, entity: str, country: str
) -> alt.Chart:
    if Id.SEX in frame.columns or "sex" in frame.columns:
        if "sex" in frame.columns:
            frame = frame.rename({"sex": Id.SEX})

        title = "Sex & Age Group"
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

        frame = frame.with_columns(
            pl.when(
                pl.col(Id.SEX).is_null()
            ).then(
                pl.lit("Unknown Sex")
            ).otherwise(
                pl.format("{} {}", pl.col(Id.SEX), pl.col(Id.GROUP))
            ).alias(Id.GROUP)
        ).with_columns(
            pl.col(Id.GROUP).replace_strict(
                {group: index for index, group in enumerate(domain)},
                return_dtype=pl.Int8,
            ).alias("rank")
        ).sort("rank")
    else:
        title = "Age Group"
        domain = ["Child", "Adolescent", "Adult"]
        range = [Palette.ORANGE, Palette.RED, Palette.PURPLE]

    return alt.Chart(
        frame,
        title=f"{entity} by Age: {country}"
    ).mark_bar().encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("sum(count):Q", sort=domain).title(f"{entity}"),
        alt.Color("age_group:N").title(title).scale(domain=domain, range=range),
        alt.Column("data_year:N").title("Year"),
        alt.Order("color_variant_label_sort_index:Q"),
    ).properties(
        width=550,
        height=250,
    )
