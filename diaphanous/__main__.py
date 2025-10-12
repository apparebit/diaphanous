import sys

if sys.version_info < (3, 10):
    print(f"{__package__} requires at least Python 3.10!")
    sys.exit(1)

from .main import main

if __name__ == "__main__":
    from pathlib import Path
    import polars as pl
    from .bka import Data
    from .nibrs import humanize_frame, Id, load_all
    from .platform.data import REPORTS_PER_PLATFORM
    from .platform.export import encode_reports_per_platform
    from .platform.tabulate import tabulate
    from .util import configure

    configure()

    json_path = Path('data/ocse-reports-per-platform.json')
    tmp_path = json_path.with_suffix('.tmp.json')
    with open(tmp_path, mode='w', encoding='utf') as file:
        file.write('\n'.join(encode_reports_per_platform(REPORTS_PER_PLATFORM)))
    tmp_path.replace(json_path)

    print(f"▶︎ {json_path}")

    # ----------------------------------------------------------------------------------

    platform_data = tabulate()
    platform_data.write_csv("data/ocse-reports-per-platform.csv")
    print("▶︎ data/ocse-reports-per-platform.csv")

    # ----------------------------------------------------------------------------------
    us = load_all()
    offenders = humanize_frame(us.offender_demographics().by(
        Id.YEAR, Id.GROUP, Id.RACE, Id.SEX, Id.SUPPLY, sorted=True
    ))

    offenders.write_csv("data/nibrs/offenders.csv")
    print(f"▶︎ data/nibrs/offenders.csv")

    # ----------------------------------------------------------------------------------
    de = Data.ingest()
    suspects = humanize_frame(de.age_distribution().group_by(
        Id.YEAR, Id.GROUP, "sex", Id.SUPPLY, maintain_order=True
    ).agg(
        pl.col("count").sum().cast(pl.Int64)
    ))

    suspects.write_csv("data/bka/suspects.csv")
    print(f"▶︎ data/bka/suspects.csv")
