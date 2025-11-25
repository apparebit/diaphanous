import sys

if sys.version_info < (3, 10):
    print(f"{__package__} requires at least Python 3.10!")
    sys.exit(1)

from .main import main

if __name__ == "__main__":
    from pathlib import Path
    import polars as pl
    from .crimestat import load_all_age_distributions
    from .platform.data import REPORTS_PER_PLATFORM
    from .platform.export import encode_reports_per_platform
    from .tabulate import tabulate
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
    compact = load_all_age_distributions(compact=True)
    frame = pl.concat(compact.values())
    frame.write_csv("data/age-distributions.csv")
    print("▶︎ data/age-distributions.csv")
