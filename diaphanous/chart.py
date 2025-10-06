import altair as alt
import polars as pl

from .color import Palette

def plot_age_distribution(
    frame: pl.DataFrame, entity: str, country: str
) -> alt.Chart:
    return alt.Chart(
        frame,
        title=f"{entity} by Age: {country}"
    ).mark_bar().encode(
        alt.X("age:Q").scale(domain=(0, 100)).title("Age"),
        alt.Y("sum(count):Q", stack=None).title(f"{entity}"),
        alt.Color(
            "age_group:N"
        ).title("Age Group").scale(
            domain=["Child", "Adolescent", "Adult"],
            range=[Palette.ORANGE, Palette.RED, Palette.PURPLE], # "#00000088"
        ),
        alt.Column("data_year:N").title("Year"),
    ).properties(
        width=550,
        height=250,
    )
