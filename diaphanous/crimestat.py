import polars as pl

from .aunz import au_age_distribution, nz_age_distribution
from .bka import de_age_distribution
from .nibrs import us_arrestees_age_distribution
from .nibrs import us_offenders_age_distribution
from .util import add_age_group, add_country_entity, arrange_age_distribution

def es_age_distribution(descriptive: bool = False) -> pl.DataFrame:
    frame = pl.read_csv(
        "data/spain.csv", separator=";"
    ).rename({
        "Age group": "age",
        "Sex": "sex",
        "period": "data_year",
        "Total": "count"
    }).filter(
        pl.col("age").ne("TOTAL").and_(
            pl.col("sex").ne("Total")
        )
    ).with_columns(
        pl.col("data_year").cast(pl.Int16),
        pl.when(
            pl.col("age").eq("Over 64 years")
        ).then(
            pl.lit(65)
        ).otherwise(
            pl.col("age").str.extract(r"^(\d+)-")
        ).cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age").eq("Over 64 years")
        ).then(
            pl.lit(99)
        ).otherwise(
            pl.col("age").str.extract(r"-(\d+)")
        ).cast(pl.Int8).add(1).alias("age_last"),
    ).with_columns(
        pl.col("count").truediv(
            pl.col("age_last").sub(pl.col("age_first"))
        ),
        pl.int_ranges("age_first", "age_last", dtype=pl.Int8).alias("age"),
    ).explode("age").sort(
        "data_year", "age", "sex"
    ).with_columns(
        pl.lit(None, dtype=pl.String).alias("ethnicity"),
        pl.lit(None, dtype=pl.String).alias("activity"),
    )

    frame = add_age_group(frame, 14, 17)
    if descriptive:
        frame = add_country_entity(frame, "Spain", "Suspect")
    return arrange_age_distribution(frame)


def load_all_age_distributions(compact: bool = False) -> list[pl.DataFrame]:
    au = au_age_distribution(descriptive=True)
    de = de_age_distribution(descriptive=True)
    es = es_age_distribution(descriptive=True)
    nz = nz_age_distribution(descriptive=True)
    us_arrestees = us_arrestees_age_distribution(descriptive=True)
    us_offenders = us_offenders_age_distribution(descriptive=True)

    distributions = [au, de, es, nz, us_arrestees, us_offenders]
    if compact:
        for index in range(len(distributions)):
            distributions[index] = distributions[index].drop_nulls(
                "count"
            ).filter(
                pl.col("count").ne(0.0)
            )

    return distributions


if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)
    distributions = load_all_age_distributions(compact=True)

    pl.concat(distributions).write_csv("data/age_distributions.csv")

    for distribution in distributions:
        print(distribution.head(5))
