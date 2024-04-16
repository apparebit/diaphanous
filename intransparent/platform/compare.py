import pandas as pd

from .ingest import combine_brands, PlatformData, wide_ncmec_reports


def _components(p: pd.Period) -> tuple[pd.Period, int, int]:
    return pd.Period(p.year, freq='Y'), p.start_time.month, p.end_time.month


def _annualize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downsample the given dataframe, which must have a period index, to yearly
    periods by summing up the columns for each year. The period index must cover
    a continuous time period without redundant entries.
    """
    # When periods are uniform, Pandas uses PeriodIndex as index and
    # downsampling is as easy as df.groupby(df.index.year). For our non-uniform
    # index, we need to manually extract the year first. Furthermore, to ensure
    # that we only include full years in the result, we check the minimum start
    # month and maximum end month for each year. This does assume that the
    # period index is continuous (but not uniform).

    aux = pd.DataFrame.from_records(
        [_components(p) for p in df.index],
        index=df.index,
        columns=['year', 'start_month', 'end_month'],
    )
    yearly = pd.concat([df, aux], axis=1).groupby('year')
    return yearly.sum(min_count=1)[
        (yearly['start_month'].min() == 1) & (yearly['end_month'].max() == 12)
    ].drop(columns=['start_month', 'end_month'])


def compare_platform_reports(
    platform: str, table: pd.DataFrame, NCMEC: pd.DataFrame
) -> None | pd.DataFrame:
    """
    Create a table comparing a platform's disclosures with those of NCMEC for
    the same platform.

    This function only includes platforms that disclose either *pieces* or
    *reports*; otherwise it returns `None`. The resulting table has the
    following columns:

      - pieces: as disclosed by platform
      - π: average number of pieces per report
      - reports: as disclosed by platform
      - Δ%: the signed percentage difference between the platform's and NCMEC's
        report counts
      - NCMEC: the report counts disclosed by NCMEC

    Columns are filled with NaN when data is unavailable.

    Since NCMEC makes only yearly disclosures, the returned table also has
    yearly granularity.
    """
    if (
        platform == "NCMEC"
        or table is None
        or not ("reports" in table.columns or "pieces" in table.columns)
        or platform not in NCMEC.columns
    ):
        return None

    if "redundant" in table.columns:
        table = table[~table["redundant"]]

    # reindex() creates non-existent columns
    comparison = _annualize(table.reindex(columns=["pieces", "π", "reports"]))

    has_sent = "reports" in table.columns
    sent = comparison["reports"]
    received = NCMEC[platform]

    # Update π (pieces per report) only if pieces are available
    if "pieces" in table.columns:
        comparison["π"] = comparison["pieces"] / (sent if has_sent else received)

    comparison["Δ%"] = ((received - sent) / sent * 100) if has_sent else None
    comparison["NCMEC"] = received
    return comparison


def compare_all_platform_reports(data: PlatformData) -> dict[str, pd.DataFrame]:
    """
    Create tables comparing platforms' disclosures with those of NCMEC for the
    same platforms. Since NCMEC only discloses yearly counts and did not
    distinguish between social media brands for 2019 and 2020, this function
    combines the data for all of a firm's brands.
    """
    NCMEC = wide_ncmec_reports(data)
    comparisons = {}

    for platform, table in combine_brands(data).items():
        comparison = compare_platform_reports(platform, table, NCMEC)
        if comparison is not None:
            comparisons[platform] = comparison

    return dict(sorted(comparisons.items()))
