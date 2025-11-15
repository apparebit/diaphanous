import polars as pl

from .aunz import au_age_distribution, nz_age_distribution
from .bka import de_age_distribution
from .nibrs import compute_us_porn_age_distribution, load_all_us_csam, load_all_us_porn
from .util import (
    add_age_group, add_country_material_role, arrange_age_distribution,
    compute_sex_and_age_cdfs
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
            pl.col("age").str.extract(r"- (\d+)")
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


def load_all_age_distributions(compact: bool = False) -> dict[str, pl.DataFrame]:
    csam = load_all_us_csam()
    csam_arrestees = csam.arrestee_demographics().age_distribution()
    csam_offenders = csam.offender_demographics().age_distribution()
    porn = load_all_us_porn()
    porn_arrestees = compute_us_porn_age_distribution(porn[0], "Arrestee")
    porn_offenders = compute_us_porn_age_distribution(porn[1], "Offender")

    distributions = {
        "au": au_age_distribution(),
        "de": de_age_distribution(),
        "es": es_age_distribution(),
        "fi": fi_age_distribution(),
        "nz": nz_age_distribution(),
        "us_arrestees": csam_arrestees,
        "us_offenders": csam_offenders,
        "us_porn_arrestees": porn_arrestees,
        "us_porn_offenders": porn_offenders,
    }

    if compact:
        for key in distributions:
            distributions[key] = distributions[key].drop_nulls(
                "count"
            ).filter(
                pl.col("count").ne(0.0)
            )

    return distributions


def compute_cdf_titles(distributions: dict[str, pl.DataFrame]) -> dict[str, str]:
    return {
        key: dist.select(
            pl.format(
                "{}: {} {}s",
                pl.col("country"),
                pl.col("material"),
                pl.col("role"),
            )
        ).item(0, 0)
        for key, dist in distributions.items()
    }


def compute_cdfs(distributions: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    return {k: compute_sex_and_age_cdfs(d) for k, d in distributions.items()}


def compute_totals(distributions: pl.DataFrame) -> pl.DataFrame:
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


def summarize_age_distributions(frame: pl.DataFrame) -> pl.DataFrame:
    # Spreading integer counts over age ranges may result in fractional counts,
    # while also incurring floating point error. Adding them together again in
    # this function may incur further floating point error, with the result that
    # some integer casts result in numbers that are too small by one. Rounding
    # ensures that the sums are correct.
    frame = frame.group_by(
        pl.col("country", "material", "role", "data_year"), maintain_order=True,
    ).agg(
        pl.col("count").sum().round(0).cast(pl.Int64).alias("total"),

        pl.col("count").filter(
            pl.col("age_group").is_not_null()
        ).sum().round(0).cast(pl.Int64).alias("with_age"),

        pl.col("count").filter(
            pl.col("age").is_not_null()
        ).sum().round(0).cast(pl.Int64).alias("with_age_too"),

        pl.col("count").filter(
            pl.col("age_group").is_in(["Child", "Juvenile"])
        ).sum().round(0).cast(pl.Int64).alias("minors"),

        pl.col("count").filter(
            pl.col("age_group").eq("Adult")
        ).sum().round(0).cast(pl.Int64).alias("adults"),

        pl.col("count").filter(
            pl.col("age").is_not_null().and_(
                pl.col("sex").eq("Female")
            )
        ).sum().round(0).cast(pl.Int64).alias("aged_women"),

        pl.col("count").filter(
            pl.col("age").is_not_null().and_(
                pl.col("sex").eq("Male")
            )
        ).sum().round(0).cast(pl.Int64).alias("aged_men"),

        pl.col("count").filter(
            pl.col("age_group").is_in(["Child", "Juvenile"]).and_(
                pl.col("sex").eq("Female")
            )
        ).sum().round(0).cast(pl.Int64).alias("female_minors"),

        pl.col("count").filter(
            pl.col("age_group").eq("Adult").and_(
                pl.col("sex").eq("Female")
            )
        ).sum().round(0).cast(pl.Int64).alias("female_adults"),

        pl.col("count").filter(
            pl.col("age_group").is_in(["Child", "Juvenile"]).and_(
                pl.col("sex").eq("Male")
            )
        ).sum().round(0).cast(pl.Int64).alias("male_minors"),

        pl.col("count").filter(
            pl.col("age_group").eq("Adult").and_(
                pl.col("sex").eq("Male")
            )
        ).sum().round(0).cast(pl.Int64).alias("male_adults"),
    )

    assert frame.select(
        pl.col("minors").add(pl.col("adults")).eq(pl.col("with_age")).all()
    ).item()

    assert frame.select(
        pl.col("with_age").eq(pl.col("with_age_too")).all()
    ).item()

    assert frame.select(
        pl.col("aged_women").add(pl.col("aged_men")).le(pl.col("with_age")).all()
    ).item()

    assert frame.select(
        pl.col("female_minors").add(pl.col("male_minors")).le(pl.col("minors")).all()
    ).item()

    assert frame.select(
        pl.col("female_adults").add(pl.col("male_adults")).le(pl.col("adults")).all()
    ).item()

    return frame.with_columns(
        pl.col("with_age").truediv(pl.col("total")).mul(100)
            .alias("with_age_pct"),
        pl.col("minors").truediv(pl.col("with_age")).mul(100)
            .alias("minors_pct"),
        pl.col("male_minors").truediv(pl.col("minors")).mul(100)
            .alias("male_minors_pct"),
        pl.col("female_minors").truediv(pl.col("minors")).mul(100)
            .alias("female_minors_pct"),
        pl.col("male_adults").truediv(pl.col("adults")).mul(100)
            .alias("male_adults_pct"),
        pl.col("female_adults").truediv(pl.col("adults")).mul(100)
            .alias("female_adults_pct"),
    ).select(
        "country", "material", "role",
        "data_year",
        "total",
        "with_age_pct", "minors_pct",
        "male_minors_pct", "female_minors_pct",
        "male_adults_pct", "female_adults_pct",
    ).fill_nan(
        0
    ).sort(
        "country", "material", "role", "data_year"
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

    frame = frame.filter(
        pl.col("country").ne("Australia").and_(
            pl.col("data_year").ge(2015)
        ).and_(
            pl.col("data_year").lt(2025)
        )
    )
    print(compute_totals(frame))
