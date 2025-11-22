import polars as pl

from .aunz import au_age_distribution, nz_age_distribution
from .bka import de_age_distribution
from .nibrs import compute_us_porn_age_distribution, load_all_us_csam, load_all_us_porn
from .util import (
    add_age_group, add_country_material_role, add_empty_year, arrange_age_distribution,
)

def es_age_distribution() -> pl.DataFrame:
    frame = pl.scan_csv(
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

    frame = add_age_group(frame, 14, 17).collect()
    frame = add_country_material_role(frame, "Spain", "CSAM", "Suspect")
    return arrange_age_distribution(frame)


def fi_age_distribution() -> pl.DataFrame:
    frame = pl.scan_csv(
        "data/finland.csv",
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

    frame = add_age_group(frame, 15, 17).collect()
    frame = add_country_material_role(frame, "Finland", "CSAM", "Suspect")
    return arrange_age_distribution(frame)


def it_age_distribution() -> pl.DataFrame:
    frame = pl.read_csv(
        "data/italy.csv"
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
    frame = add_age_group(frame, 14, 17)
    frame = add_country_material_role(frame, "Italy", "CSAM", "Offender")
    frame = arrange_age_distribution(frame)
    return frame


def load_all_age_distributions(compact: bool = False) -> dict[str, pl.DataFrame]:
    csam = load_all_us_csam()
    csam_offenders = csam.offender_demographics().age_distribution()
    csam_arrestees = csam.arrestee_demographics().age_distribution()
    porn = load_all_us_porn()
    porn_offenders = compute_us_porn_age_distribution(porn[1], "Offender")
    porn_arrestees = compute_us_porn_age_distribution(porn[0], "Arrestee")

    distributions = {
        "au": au_age_distribution(),
        "de": de_age_distribution(),
        "es": es_age_distribution(),
        "fi": fi_age_distribution(),
        "it": it_age_distribution(),
        "nz": nz_age_distribution(),
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
        "country", "material", "role", "data_year",
        maintain_order=True
    ).agg(
        pl.col("count").sum().round(0).cast(pl.Int64)
    ).select(
        pl.format("{} {} {}s", "country", "material", "role").alias("metric"),
        "data_year", "count"
    ).pivot(
        on="data_year",
        index="metric",
        values="count",
    )


def summarize_age_and_sex(
    frame: pl.DataFrame,
    year_range: tuple[int, int] = (2020, 2025),
) -> pl.DataFrame:
    return frame.filter(
        pl.col("country").ne("Australia").and_(
            pl.col("data_year").is_between(*year_range, closed="left")
        ).and_(
            pl.col("age_group").is_not_null()
        ).and_(
            pl.col("sex").is_not_null()
        )
    ).select(
        pl.format(
            "{} {} {}s",
            pl.col("country"),
            pl.col("material"),
            pl.col("role")
        ).alias("metric"),
        pl.col("data_year"),
        pl.col("age_group").replace({
            "Child": "Minor",
            "Juvenile": "Minor",
        }),
        pl.col("sex", "count"),
    ).group_by(
        "metric", "data_year", "age_group", "sex"
    ).agg(
        pl.col("count").sum().round().cast(pl.Int64)
    ).group_by(
        "metric", "sex"
    ).agg(
        *(
            pl.col("count").filter(
                pl.col("data_year").eq(year).and_(
                    pl.col("age_group").eq(group)
                )
            ).first().alias(f"{year} {group.lower()}")
            for year in range(*year_range) for group in ("Minor", "Adult")
        )
    ).with_columns(
        pl.col("sex").replace({"Male": 1, "Female": -1}).alias("order")
    ).sort(
        "metric", "order"
    ).drop(
        "order"
    )


if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)
    pl.Config.set_tbl_rows(100)
    pl.Config.set_thousands_separator(True)
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment("RIGHT")

    # _WIDTH, _ = shutil.get_terminal_size()
    distributions = load_all_age_distributions(compact=True)
    frame = pl.concat(distributions.values())
    frame.write_csv("data/age-distributions.csv")

    age_dist = pl.concat(load_all_age_distributions().values())
    print(summarize_age_and_sex(age_dist, (2015, 2019)))
    print(summarize_age_and_sex(age_dist, (2020, 2025)))
