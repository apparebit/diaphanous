import polars as pl

from .util import add_age_group, arrange_age_distribution

def es_age_distribution() -> pl.DataFrame:
    frame = pl.read_csv(
        "data/spain.csv", separator=";"
    ).rename({
        "Age group": "age",
        "Sex": "sex",
        "period": "data_year",
        "Total": "count"
    }).filter(
        pl.col("data_year").is_in([2023, 2024]).and_(
            pl.col("age").ne("TOTAL")
        ).and_(
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
        pl.int_ranges("age_first", "age_last").alias("age"),
    ).explode("age").sort(
        "data_year", "age", "sex"
    ).with_columns(
        pl.lit(None, dtype=pl.String).alias("activity")
    ).pipe(
        add_age_group, 14, 17
    ).pipe(
        arrange_age_distribution
    )



    return frame


if __name__ == "__main__":
    from .aunz import au_age_distribution
    print(au_age_distribution())
    print(es_age_distribution())
