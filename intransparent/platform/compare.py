import pandas as pd

from .ingest import combine_brands, PlatformData, wide_ncmec_reports


def _components(p: pd.Period) -> tuple[pd.Period, int, int]:
    return pd.Period(p.year, freq='Y'), p.start_time.month, p.end_time.month


def _annualize(df: pd.DataFrame) -> pd.DataFrame:
    # If periods have uniform length, Pandas uses PeriodIndex and hence supports
    # expressions such as `df.index.year` that simplify aggregation by year.
    # This function still works in the more general case.
    aux = pd.DataFrame.from_records(
        [_components(p) for p in df.index],
        index=df.index,
        columns=['year', 'start_month', 'end_month'],
    )

    yearly = pd.concat([df, aux], axis=1).groupby('year')
    # Don't drop start_month and end_month here since we reindex anyways.
    return yearly.sum(min_count=1)[
        (yearly['start_month'].min() == 1) & (yearly['end_month'].max() == 12)
    ]


def compare_platform_reports(
    platform: str, table: pd.DataFrame, NCMEC: pd.DataFrame
) -> None | pd.DataFrame:
    """
    Create a table comparing a platform's disclosures with those of NCMEC for
    the same platform or return `None` if no such comparison can be made.
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
    comparison = _annualize(table).reindex(columns=["pieces", "π", "reports"])

    has_sent = "reports" in table.columns
    sent = comparison["reports"]
    received = NCMEC[platform]

    # Update π (pieces per report) only if pieces are available
    if "pieces" in table.columns:
        comparison["π"] = comparison["pieces"] / (sent if has_sent else received)

    comparison["Δ%"] = ((received - sent) / sent * 100) if has_sent else None
    comparison["NCMEC"] = received
    industry = NCMEC["ESP Total"]
    comparison["esp%"] = received / industry * 100
    comparison["esp"] = industry
    total = NCMEC["Total"]
    comparison["total%"] = received / total * 100
    comparison["total"] = total
    comparison["esp/total%"] = industry / total * 100
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
