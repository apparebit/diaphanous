import pandas as pd

from .ingest import PlatformData, wide_ncmec_reports


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
    ].drop(columns=['start_month', 'end_month'])


def _compare_platform_reports(
    platform: str, table: None | pd.DataFrame, NCMEC: pd.DataFrame
) -> pd.DataFrame:
    """
    Create a table comparing a platform's disclosures with those of NCMEC for
    the same platform or return `None` if no such comparison can be made.
    """
    # Ensure that every comparison covers full range of years
    if table is None:
        table = pd.DataFrame(index=NCMEC.index).reindex(columns=["pieces", "reports"])

    # Fill in the rest of the table
    sent = table['reports']
    received = NCMEC[platform]

    table.insert(1, 'π', table['pieces'] / sent.fillna(received))
    table["Δ%"] = (received - sent) / sent * 100
    table["NCMEC"] = received
    industry = NCMEC["ESP Total"]
    table["esp%"] = received.fillna(sent) / industry * 100
    table["esp"] = industry
    total = NCMEC["Total"]
    table["total%"] = received.fillna(sent) / total * 100
    table["total"] = total
    table["esp/total%"] = industry / total * 100
    return table


def compare_all_platform_reports(data: PlatformData) -> dict[str, pd.DataFrame]:
    """
    Create tables comparing platforms' disclosures with those of NCMEC for the
    same platforms. Since NCMEC only discloses yearly counts and did not
    distinguish between social media brands for 2019 and 2020, this function
    combines the data for all of a firm's brands.
    """
    NCMEC = wide_ncmec_reports(data)

    # Annualize all tables so that they have compatible indices
    nonredundant = (
        (p, t[~t["redundant"]] if "redundant" in t.columns else t)
        for p, t in data.disclosures.items()
        if t is not None and len(t) > 0
    )

    annualized = {
        p: _annualize(t.reindex(columns=["pieces", "reports"])).reindex(NCMEC.index)
        for p, t in nonredundant
    }

    # Sum data of each firm and its brands
    for firm, brands in data.brands.items():
        tables = [annualized.get(p) for p in (firm, *brands) if p in annualized]

        for b in brands:
            if b in annualized:
                del annualized[b]

        if not tables:
            continue

        sum = tables[0]
        for t in tables[1:]:
            sum = sum.add(t, fill_value=0)

        annualized[firm] = sum

    comparisons = {}
    for platform in NCMEC.columns:
        if platform in ("NCMEC", "Telegram", "ESP Total", "Total"):
            continue

        comparison = _compare_platform_reports(
            platform, annualized.get(platform), NCMEC
        )
        comparisons[platform] = comparison

    return dict(sorted(comparisons.items()))
