import shutil

import polars as pl

from .model import Table
from .reader import (
    analyze_offender_anomalies, done_ingestion, ingest_crosswalk, ingest_tables,
    step_ingestion, us_age_distributions
)

if __name__ == "__main__":
    WIDTH, _ = shutil.get_terminal_size()
    DASH = "━"
    LIGHT_DASH = "─"

    def section(title: str, heavy: bool = True) -> None:
        dash = DASH if heavy else LIGHT_DASH
        print(f"\n\n{dash * 4} {title} {dash * (WIDTH - 4 - 2 - len(title))}\n")

    pl.Config.set_tbl_cols(35)
    pl.Config.set_tbl_rows(200)
    pl.Config.set_fmt_str_lengths(100)
    pl.Config.set_thousands_separator(True)
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment("RIGHT")

    # distributions = us_age_distributions(step_ingestion, done_ingestion)
    # print(distributions)

    tables = ingest_tables(step_ingestion)

    section("Agencies")
    agencies = tables[Table.AGENCY]
    print(agencies.columns)
    print(agencies.select(
        pl.len(),
        pl.col("agency_id").n_unique(),
        pl.col("ori").n_unique(),
    ))

    ambiguous_names = agencies.group_by(
        "ori"
    ).agg(
        pl.col("ncic_agency_name").alias("name"),
    ).filter(
        pl.col("name").list.unique().list.len().gt(1)
    )

    # We explode twice because when exploding multiple columns at the same time
    # their list values must have the same sizes.
    unique_agencies = agencies.explode("nibrs_cert_date").explode("nibrs_start_date").group_by(
        "ori"
    ).agg(
        pl.col(c).filter(pl.col(c).is_not_null()).unique() for c in (
            "ncic_agency_name", "state_abbr", "nibrs_cert_date", "nibrs_start_date"
        )
    )

    section("Divergent Names", heavy=False)
    for ori, names in ambiguous_names.rows():
        print(f"{ori} {names[0]}")
        for name in names[1:]:
            print(f"{" " * len(ori)} {name}")

    section("Divergent States", heavy=False)
    print(unique_agencies.filter(
        pl.col("state_abbr").list.len().gt(1)
    ))

    section("Divergent Certification Dates", heavy=False)
    print(unique_agencies.filter(
        pl.col("nibrs_cert_date").list.len().gt(1)
    ))

    section("Divergent Start Dates", heavy=False)
    print(unique_agencies.filter(
        pl.col("nibrs_start_date").list.len().gt(1)
    ))

    # exclusions = [
    #     "yearly_agency_id", "agency_id", "data_year", "legacy_ori",
    #     "covered_by_legacy_ori", "ucr_agency_name", "ncic_agency_name",
    #     "pub_agency_name", "pub_agency_unit", "state_id", "state_name",
    #     "state_abbr", "submitting_agency_id", "sai", "submitting_agency_name",
    #     "male_officer", "male_civilian", "male_officer+male_civilian",
    #     "female_officer", "female_civilian", "female_officer+female_civilian",
    #     "officer_rate", "employee_rate", "nibrs_leoka_start_date",
    #     "nibrs_multi_bias_start_date", "nibrs_off_eth_start_date",
    # ]

    # interesting = set(agencies.columns) - set(exclusions)
    # print(interesting)
    # print(len(interesting))

    # print(agencies.select(
    #     pl.exclude(exclusions)
    # ))

    # print(agencies.unpivot(
    #     index="ori",
    #     variable_name="kind",
    #     value_name="date",
    # ).explode(
    #     "date"
    # ))

    # agencies2 = agencies.group_by(
    #     pl.col("ori")
    # ).agg(
    #     pl.col("nibrs_cert_date", "nibrs_start_date").last()
    # ).select(
    #     pl.col("ori"),
    #     pl.col("nibrs_cert_date"),
    #     pl.col("nibrs_cert_date").str.to_date("%Y-%m-%d", strict=False).alias("cert"),
    #     pl.col("nibrs_cert_date").str.to_date("%d-%b-%y", strict=False).alias("cert2"),
    # ).select(
    #     pl.col("ori"),
    #     pl.col("cert").fill_null(pl.col("cert2")),
    # )

    # section("Incidents")
    # incidents = tables[Table.INCIDENT]
    # print(incidents.columns)

    # section("Participation")
    # participation = agencies.select(
    #     pl.col(
    #         "yearly_agency_id",
    #         "agency_id",
    #         "data_year",
    #         "ori",
    #         "legacy_ori",
    #         "nibrs_cert_date",
    #         "nibrs_start_date"
    #     )
    # )

    #print(participation)
