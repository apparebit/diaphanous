from pathlib import Path

import polars as pl

from .util import add_age_group, arrange_age_distribution

AIC = pl.DataFrame({
    "Year": ["2022/23"] * 12,
    "Sex": (["Male"] * 4) + (["Female"] * 4) + (["All"] * 4),
    "Age": ["10-17", "18-44", "45+", "Total"] * 3,
    "Offenders": [287, 611, None, 1_216, 202, 25, None, 235, 489, 637, 319, 1452],
})

def au_age_distribution() -> pl.DataFrame:
    return AIC.filter(
        pl.col("Age").ne("Total")
    ).pivot(
        on="Sex",
        index=["Year", "Age"],
        values="Offenders",
    ).with_columns(
        pl.col("All").sub(pl.col("Male")).sub(pl.col("Female"))
    ).unpivot(
        on=["Male", "Female", "All"],
        index=["Year", "Age"],
        variable_name="sex",
        value_name="count",
    ).with_columns(
        pl.col("sex").replace({"All": None}),
        pl.col("Age").replace({
            "10-17": 10,
            "18-44": 18,
            "45+": 45,
        }, return_dtype=pl.Int8).alias("age_first"),
        pl.col("Age").replace({
            "10-17": 18,
            "18-44": 45,
            "45+": 100,
        }, return_dtype=pl.Int8).alias("age_last"),
    ).with_columns(
        pl.col("count").truediv(pl.col("age_last").sub(pl.col("age_first")))
    ).select(
        pl.col("Year").replace(
            {"2022/23": 2023},
            return_dtype=pl.Int16
        ).alias("data_year"),
        pl.int_ranges("age_first", "age_last").alias("age"),
        pl.col("sex", "count")
    ).explode("age").sort(
        "data_year", "age", "sex"
    ).with_columns(
        pl.lit(None, dtype=pl.String).alias("activity"),
    ).pipe(
        add_age_group
    ).pipe(
        arrange_age_distribution
    )


# ======================================================================================


POLICEDATA = Path("data/policedata.nz/nz-up-to-2025-08.csv")

def nz_load() -> pl.DataFrame:
    # UTF-16? That's just plain nuts
    return pl.read_csv(POLICEDATA, encoding="utf16", separator="\t").select(
        pl.col("Year Month").alias("year_month"),
        pl.col("Proceedings").alias("proceedings"),
        pl.col("SEX").alias("sex"),
        pl.col("Person/Organisation").alias("entity"),
        pl.col("Number of Records").alias("records"),
        pl.col("Mop Division").alias("method_type"),
        pl.col("Mop Subdivision").alias("method_subtype"),
        pl.col("Mop Group").alias("method_group"),
        pl.col("Ethnicity").alias("ethnicity"),
        pl.col("ANZSOC_GROUP_CD").alias("activity"),
        pl.col("Age Group").alias("age"),
    ).with_columns(
        pl.col("year_month").str.extract(r"...(\d+)").cast(pl.Int16).alias("year"),
        pl.col("year_month").str.extract("(...)").replace({
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }).alias("month"),
        pl.col("age").str.extract(r"(\d+)").cast(pl.Int8).alias("age_low"),
        pl.when(
            pl.col("age").eq("80yearsorover")
        ).then(
            pl.lit(99)
        ).otherwise(
            pl.col("age").str.extract(r"\d+-(\d+)").cast(pl.Int8)
        ).add(1).alias("age_high"),
        pl.col("sex").replace({"Not Stated": None}),
        pl.col("ethnicity").replace({
            "Not Stated": None,
            "Not Elsewhere Classified": "Other",
        }),
        pl.col("activity").replace_strict({
            341: "Producer",
            342: "Consumer",
            340: None
        }, return_dtype=pl.String),
    ).select(
        pl.col(
            "year", "month",
            "method_type", "method_subtype", "method_group",
            "activity",
            "entity",
            "age_low", "age_high", "sex", "ethnicity",
            "records", "proceedings"
        )
    ).sort(
        pl.col("year", "month")
    )


def nz_age_distribution() -> pl.DataFrame:
    return nz_load().group_by(
        pl.col("year", "age_low", "age_high", "sex", "ethnicity", "activity")
    ).agg(
        pl.col("proceedings").sum().alias("count")
    ).with_columns(
        pl.col("count").truediv(pl.col("age_high").sub(pl.col("age_low")))
    ).with_columns(
        pl.int_ranges("age_low", "age_high").alias("age"),
    ).explode("age").pipe(
        add_age_group
    ).with_columns(
        pl.col("year").alias("data_year"),
    ).sort(
        "data_year", "age", "sex", "activity"
    ).pipe(
        arrange_age_distribution
    )

if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)

    print(au_age_distribution())
    #print(nz_age_distribution())
    print(nz_load())
