from pathlib import Path

import polars as pl

from .aunz import au_age_distribution, nz_age_distribution
from .de import de_age_distribution
from .nibrs import done_ingestion, step_ingestion, us_age_distributions
from .util import add_empty_year, finish_age_distribution, to_minor_adult


_ROOT = Path(__file__).parent.parent


def es_age_distribution() -> pl.LazyFrame:
    frame = pl.scan_csv(
        _ROOT / "data/spain.csv", separator=";"
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

    return finish_age_distribution(
        frame,
        country="Spain",
        material="CSAM",
        role="Offender",
        juvenile_min=14,
        juvenile_max=17,
    )



def fi_age_distribution() -> pl.LazyFrame:
    frame = pl.scan_csv(
        _ROOT / "data/finland.csv",
    ).select(
        pl.exclude(
            "ICCS offence category",
            "Number of offence headings for suspects of solved offences",
        )
    ).rename({
        "Year": "data_year",
        "Suspect's sex": "sex",
        "Suspect's age": "age",
        "Persons suspected of solved offences": "count",
    }).filter(
        pl.col("sex").ne("Total").and_(
            pl.col("age").is_in(["Total", "18 -"]).not_()
        )
    ).select(
        pl.col("data_year").cast(pl.Int16),
        pl.col("sex").replace({
            "Males": "Male",
            "Females": "Female",
            "Unknown": None,
        }),
        pl.col("age").replace({
            "Unknown": None,
        }),
        pl.col("count"),
    )

    frame = pl.concat([
        frame.filter(
            pl.col("age").ne("0 - 17")
        ),
        frame.filter(
            pl.col("age").eq("0 - 17")
        ).select(
            "data_year", "sex", "count",
        ).join(
            frame.filter(
                pl.col("age").eq("0 - 14")
            ).select(
                "data_year", "sex", "count",
            ),
            on=["data_year", "sex"],
            how="inner",
        ).select(
            pl.col("data_year", "sex"),
            pl.lit("15 - 17").alias("age"),
            pl.col("count").sub(pl.col("count_right")),
        ),
    ]).with_columns(
        pl.col("age").str.extract(r"^(\d+) -").cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age").eq("50 -")
        ).then(
            pl.lit(99)
        ).otherwise(
            pl.col("age").str.extract(r"- (\d+)$")
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

    return finish_age_distribution(
        frame,
        country="Finland",
        material="CSAM",
        role="Offender",
        juvenile_min=15,
        juvenile_max=17,
    )


def it_age_distribution() -> pl.LazyFrame:
    frame = pl.scan_csv(
        _ROOT / "data/italy.csv"
    ).select(
        "AGE", "Sex (DESC)", "CITIZENSHIP", "TIME_PERIOD", "Observation",
    ).filter(
        pl.col("CITIZENSHIP").ne("TOTAL")
    ).rename({
        "AGE": "age",
        "Sex (DESC)": "sex",
        "CITIZENSHIP": "ethnicity",
        "TIME_PERIOD": "data_year",
        "Observation": "count",
    }).with_columns(
        pl.col("data_year").cast(pl.Int16),
        pl.when(
            pl.col("age").eq("Y_UN13")
        ).then(
            pl.lit(0)
        ).when(
            pl.col("age").eq("Y_GE65")
        ).then(
            pl.lit(65)
        ).otherwise(
            pl.col("age").str.extract(r"^Y(\d+)-")
        ).cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age").eq("Y_UN13")
        ).then(
            pl.lit(13)
        ).when(
            pl.col("age").eq("Y_GE65")
        ).then(
            pl.lit(99)
        ).otherwise(
            pl.col("age").str.extract(r"-(\d+)$")
        ).cast(pl.Int8).add(1).alias("age_last"),
        pl.col("sex").replace({"Females": "Female", "Males": "Male"}),
        pl.col("ethnicity").replace({"ITL": "Italian", "FRG": "Foreign"}),
    ).with_columns(
        pl.col("count").truediv(
            pl.col("age_last").sub(pl.col("age_first"))
        ),
        pl.int_ranges("age_first", "age_last", dtype=pl.Int8).alias("age"),
    ).explode("age").sort(
        "data_year", "age", "sex", "ethnicity"
    ).with_columns(
        pl.lit(None, dtype=pl.String).alias("activity"),
    ).select(
        "data_year", "age", "sex", "ethnicity", "activity", "count"
    )

    frame = add_empty_year(frame, 2024)
    return finish_age_distribution(
        frame,
        country="Italy",
        material="CSAM",
        role="Offender",
        juvenile_min=14,
        juvenile_max=17,
    )



def load_all_age_distributions(
    compact: bool = False,
    verbose: bool = False,
) -> dict[str, pl.DataFrame]:
    """
    Load all age distributions. The resulting dictionary uses ISO two-letter
    codes to identify countries, with "us" followed by CSAM/porn and
    offenders/arrestees, both separated by underscores and all lower-case. It
    also is sorted alphabetically by country name. Each frame, in turn, is
    sorted by year, age, sex, ethnicity, and activity.
    """
    if verbose:
        us = us_age_distributions(step_ingestion, done_ingestion)
    else:
        us = us_age_distributions()
    csam_offenders = us.filter(pl.col("metric").eq("United States CSAM Offenders"))
    csam_arrestees = us.filter(pl.col("metric").eq("United States CSAM Arrestees"))
    porn_offenders = us.filter(pl.col("metric").eq("United States Porn Offenders"))
    porn_arrestees = us.filter(pl.col("metric").eq("United States Porn Arrestees"))

    distributions = {
        "au": au_age_distribution().collect(),
        "fi": fi_age_distribution().collect(),
        "de": de_age_distribution().collect(),
        "it": it_age_distribution().collect(),
        "nz": nz_age_distribution().collect(),
        "es": es_age_distribution().collect(),
        "us_csam_offenders": csam_offenders,
        "us_csam_arrestees": csam_arrestees,
        "us_porn_offenders": porn_offenders,
        "us_porn_arrestees": porn_arrestees,
    }

    if compact:
        for key in distributions:
            distributions[key] = distributions[key].drop_nulls(
                "count"
            ).filter(
                pl.col("count").ne(0.0)
            )

    return distributions


def summarize_totals(distributions: pl.DataFrame) -> pl.DataFrame:
    return distributions.group_by(
        "country", "material", "role", "data_year", maintain_order=True
    ).agg(
        pl.col("count").sum().round(0).cast(pl.Int64)
    ).select(
        "metric", "data_year", "count"
    ).pivot(
        on="data_year",
        index="metric",
        values="count",
    )


def summarize_age_and_sex(
    frame: pl.DataFrame,
    year_range: tuple[int, int] = (2020, 2025),
) -> pl.DataFrame:
    frame = frame.filter(
        pl.col("country").ne("Australia").and_(
            pl.col("data_year").is_between(*year_range, closed="left")
        ).and_(
            pl.col("age_group").is_not_null()
        ).and_(
            pl.col("sex").is_not_null()
        )
    )

    return to_minor_adult(frame).select(
        "metric", "data_year", "age_group", "sex", "count"
    ).group_by(
        "metric", "data_year", "age_group", "sex", maintain_order=True
    ).agg(
        pl.col("count").sum().round().cast(pl.Int64)
    )


if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)
    pl.Config.set_tbl_rows(100)
    pl.Config.set_thousands_separator(True)
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment("RIGHT")

    # _WIDTH, _ = shutil.get_terminal_size()
    compact = load_all_age_distributions(compact=True, verbose=True)
    frame = pl.concat(compact.values())
    frame.write_csv("data/age-distributions.csv")

    # age_dist = pl.concat(load_all_age_distributions().values())
    # print(summarize_age_and_sex(age_dist, (2015, 2019)))
    # print(summarize_age_and_sex(age_dist, (2020, 2025)))
