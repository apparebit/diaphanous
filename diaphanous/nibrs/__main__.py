import polars as pl
from .reader import (
    analyze_offender_anomalies, done_ingestion, step_ingestion, us_age_distributions
)

if __name__ == "__main__":
    pl.Config.set_tbl_cols(15)
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(True)
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment("RIGHT")

    # distributions = us_age_distributions(step_ingestion, done_ingestion)
    # print(distributions)

    agencies, age_ranges = analyze_offender_anomalies(step_ingestion)
    print(agencies)
    print(age_ranges)

