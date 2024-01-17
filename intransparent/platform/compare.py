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
    if platform == "NCMEC":
        raise ValueError('cannot compare NCMEC with itself')
    if table is None or "reports" not in table.columns:
        raise ValueError(f'nothing to compare for {platform}')
    if platform not in NCMEC.columns:
        raise ValueError(f"{platform} does not appear in NCMEC's disclosures")

    if "redundant" in table.columns:
        table = table[~table["redundant"]]

    selection = ["pieces", "reports"] if "pieces" in table.columns else ["reports"]
    comparison = _annualize(table[selection])

    sent = comparison["reports"]
    received = NCMEC[platform]
    comparison["Δ%"] = (received - sent) / sent * 100
    comparison["NCMEC"] = received

    return comparison


def compare_all_platform_reports(data: PlatformData) -> dict[str, pd.DataFrame]:
    NCMEC = wide_ncmec_reports(data)
    comparisons = {}

    for platform, table in combine_brands(data).items():
        if platform == 'NCMEC' or table is None or "reports" not in table.columns:
            continue
        comparison = compare_platform_reports(platform, table, NCMEC)
        if comparison is not None:
            comparisons[platform] = comparison

    return comparisons
