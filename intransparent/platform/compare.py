import pandas as pd


def _annualize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downsample the given dataframe, which must have a period index, to yearly
    periods by summing up all data for a given year.
    """
    # Pandas' resample() only handles dataframes with uniform periods.
    # Converting to timestamps, resampling, and converting back to periods is
    # exceedingly brittle. Since we are downsampling anyways, forcing every
    # sample into the desired period is straight-forward (even if it requires an
    # explicit lambda application) and works.
    has_redundant = 'redundant' in df.columns

    df = df[~df['redundant']] if has_redundant else df.copy()
    df.index = df.index.map(lambda p: pd.Period(p.start_time.year, freq="Y"))
    df.index.name = 'year'
    result = df.groupby(df.index).sum(min_count=1).sort_index()
    return result.drop(['redundant'], axis=1) if has_redundant else result


def _combine(
    disclosures: dict[str, pd.DataFrame], target: str, *sources: str
) -> dict[str, pd.DataFrame]:
    """
    Compute a new version of the disclosures that has the same entries as the
    given one but without the source platforms and with the target platform as
    the sum of the source and target platforms. The target platform need not
    exist originally. All source and target platform tables should have the same
    columns and row index.
    """
    combined = disclosures.get(target)
    new_disclosures = {}

    for platform, table in disclosures.items():
        if platform == target:
            pass
        elif platform in sources:
            if combined is None:
                combined = table
            else:
                combined += table
        else:
            new_disclosures[platform] = table

    assert combined is not None
    new_disclosures[target] = combined
    return new_disclosures


def compare_platform_reports(
    platform: str, table: pd.DataFrame, NCMEC: pd.DataFrame
) -> None | pd.DataFrame:
    if platform == "NCMEC":
        return None
    if table is None or "reports" not in table.columns:
        return None
    if platform not in NCMEC.columns:
        raise ValueError(f"{platform} does not appear in NCMEC's disclosures")

    table = _annualize(table)
    if "pieces" in table.columns:
        comparison = table["pieces"].to_frame()
        comparison["reports"] = sender = table["reports"]
    else:
        sender = table["reports"]
        comparison = sender.to_frame()

    receiver = NCMEC[platform]
    comparison["Δ%"] = (receiver - sender) / sender * 100
    comparison["NCMEC"] = receiver
    return comparison


def compare_all_platform_reports(
    disclosures: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    disclosures = _combine(disclosures, "Google/YouTube", "Google", "YouTube")
    NCMEC = disclosures["NCMEC"]
    comparisons = {}

    for platform, table in disclosures.items():
        comparison = compare_platform_reports(platform, table, NCMEC)
        if comparison is not None:
            comparisons[platform] = comparison

    return comparisons
