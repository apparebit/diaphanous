import polars as pl

from .aunz import au_age_distribution, nz_age_distribution
from .bka import de_age_distribution
from .nibrs import compute_porn_age_distribution, load_all_csam, load_all_porn
from .util import (
    add_age_group, add_country_entity, arrange_age_distribution, compute_sex_and_age_cdfs
)

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


def load_all_age_distributions(compact: bool = False) -> dict[str, pl.DataFrame]:
    csam = load_all_csam()
    csam_arrestees = csam.arrestee_demographics().age_distribution(descriptive=True)
    csam_offenders = csam.offender_demographics().age_distribution(descriptive=True)
    porn = load_all_porn()
    porn_arrestees = compute_porn_age_distribution(porn[0], entity="US Porn Arr'ees")
    porn_offenders = compute_porn_age_distribution(porn[1], entity="US Porn Off'ers")

    distributions = {
        "au": au_age_distribution(descriptive=True),
        "de": de_age_distribution(descriptive=True),
        "es": es_age_distribution(descriptive=True),
        "nz": nz_age_distribution(descriptive=True),
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
            pl.format("{} ({}s)", pl.col("country"), pl.col("entity"))
        ).item(0, 0)
        for key, dist in distributions.items()
    }


def compute_cdfs(distributions: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    return {k: compute_sex_and_age_cdfs(d) for k, d in distributions.items()}


if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)
    pl.Config.set_tbl_rows(100)

    # _WIDTH, _ = shutil.get_terminal_size()
    distributions = pl.concat(load_all_age_distributions(compact=True).values())
    distributions.write_csv("data/age_distributions.csv")
