from pathlib import Path

import pandas as pd


# Meta metrics with counts as values.
COUNT = (
    'Content Actioned',
    'Content Appealed',
    'Content Restored with appeal',
    'Content Restored without appeal',
)

# Meta metrics with percentages as values. That is meant literally as well.
PERCENT = (
    'Proactive rate',
    'UBP',
    'Prevalence',
    'Lowerbound Prevalence',
    'Upperbound Prevalence',
)

# The schema of Meta's transparency disclosures after parsing into a data frame.
SCHEMA = {
    'app': 'category',
    'policy_area': 'category',
    'metric': 'category',
    'period': 'period[Q]',
    'value': 'string',
}


def _parse_counts(df: pd.DataFrame) -> pd.Series:
    """Parse all values that are integer counts."""
    return (
        df.loc[df['metric'].isin(COUNT), 'value'].str.replace(',', '').astype('Float64')
    )


def _parse_percents(df: pd.DataFrame) -> pd.Series:
    """Parse all values that are percentages."""
    return df.loc[df['metric'].isin(PERCENT), 'value'].str.rstrip('%').astype('Float64')

FIRST_REPORT_PERIOD = pd.Period('2021q2')
LATEST_REPORT_PERIOD = pd.Period('2023q3')
PATCH_REPORT_START = pd.Period('2022q4')


def _read(path: str | Path, quarter: str | pd.Period) -> pd.DataFrame:
    """
    Read Meta's transparency disclosures for the given quarter. The prevalence
    of fake accounts for Q4 2022 and Q1 2023 is not a percentage but the range
    "4%-5%". This function normalizes the value to 4.5%.
    """
    if isinstance(quarter, str):
        quarter = pd.Period(quarter)

    path = Path(path) / f'meta-{quarter.year}-q{quarter.quarter}.csv'
    # mypy madness: read_csv's dtype accepts defaultdict but not dict.
    data = pd.read_csv(path, dtype=SCHEMA)

    # Quick and dirty mitigation against unusual value "4%-5%":
    if quarter >= PATCH_REPORT_START:
        fake_account_prevalence = (data['policy_area'] == 'Fake Accounts') & (
            data['metric'] == 'Prevalence'
        )
        assert len(data[fake_account_prevalence]) == 1
        data.loc[fake_account_prevalence, 'value'] = "4.5%"

    return (
        data.assign(count=_parse_counts)
        .assign(percent=_parse_percents)
        .assign(value=lambda df: df['count'].fillna(df['percent']))
        .drop(columns=['count', 'percent'])
    )


def read_all(
    path: str | Path,
    first: str | pd.Period = FIRST_REPORT_PERIOD,
    last: str | pd.Period = LATEST_REPORT_PERIOD,
) -> dict[pd.Period, pd.DataFrame]:
    """
    Read Meta's transparency disclosures.

    This function ingests all transparency disclosures between `first` and
    `last` (inclusive) and returns a `dict` mapping periods to data frames.
    Meta's CSV files have a straightforward schema with five columns identifying
    the application, policy area, metric, period, and finally exactly one value.
    Data frames mirror this simplicity but use Pandas' categories for the first
    three columns, Pandas' periods for the fourth, and the value as a `float`.
    """
    if isinstance(first, str):
        first = pd.Period(first)
    if isinstance(last, str):
        last = pd.Period(last)

    disclosures = {}

    cursor = first
    while cursor <= last:
        disclosures[cursor] = _read(path, cursor)
        cursor += 1

    return disclosures


def _diff(
    label1: str, data1: pd.DataFrame, label2: str, data2: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute the differences between the two dataframes, using the given labels
    to annotate the source of values.
    """
    return (
        pd.merge(
            data1,
            data2,
            how='inner',
            on=['app', 'policy_area', 'metric', 'period'],
            suffixes=(label1, label2),
        )
        .query(f'not value{label1}.isna() or not value{label2}.isna()')
        .query(f'value{label1} != value{label2}')
        .sort_values(['period', 'policy_area', 'app', 'metric'])
    )


def _period2label(period: pd.Period) -> str:
    return f'_q{period.quarter}_{period.year}'


def diff_all(
    disclosures: dict[pd.Period, pd.DataFrame]
) -> dict[pd.Period, pd.DataFrame]:
    """
    Find all differences in Meta's transparency disclosures between the
    historical data in one quarter's file and the previous quarter's file.

    Obviously, there is no previous quarter for the first in the dataset and
    hence no differences can be found.

    This function determines the range of periods, traverses them in order, and
    computes the difference between the two sets by first performing an inner
    join and then comparing the values from each of the disclosures. If one of
    the values is N/A, they are ignored.

    The resulting `dict` maps the *earlier* period to the data frame containing
    the differences.
    """
    cursor = min(*disclosures.keys())
    last = max(*disclosures.keys())

    label1 = _period2label(cursor)
    data1 = disclosures[cursor]
    differences = {}

    while cursor < last:
        next_cursor = cursor + 1
        label2 = _period2label(next_cursor)
        data2 = disclosures[next_cursor]

        differences[cursor] = _diff(label1, data1, label2, data2)

        cursor = next_cursor
        label1 = label2
        data1 = data2

    return differences


def age_of_divergence(delta: pd.DataFrame) -> pd.DataFrame:
    """
    Given a data frame with differences between two disclosures, determine the
    number of measurements per historical period that are divergent. This
    function does not create zero entries for periods without such measurements.
    It returns the result as a data frame.
    """
    return (
        delta
        .groupby('period')
        .size()
        .to_frame()
        .rename(columns={0: 'divergent'})
    )


def rate_of_divergence(
    disclosures: dict[pd.Period, pd.DataFrame],
    differences: dict[pd.Period, pd.DataFrame],
) -> pd.DataFrame:
    """
    Given the parsed disclosures dictionary and the computed differences
    dictionary, determine the rate of divergence for each quarter (but the
    first). That rate is the number of divergent measurements divided by the
    number of all measurements included in the earlier period's CSV file. The
    result is returned in a data frame
    """

    cursor = min(*disclosures.keys())
    last = max(*disclosures.keys())

    data = []
    while cursor < last:
        next_cursor = cursor + 1
        changed = len(differences[cursor])
        total = len(disclosures[cursor])
        cursor = next_cursor

        data.append({
            'period': next_cursor,
            'changed': changed,
            'total': total,
            'rate_of_divergence': changed / total * 100,
        })

    return pd.DataFrame(data)


def descriptors_of_divergence(delta: pd.DataFrame) -> str:
    """
    Format a simple HTML fragment with bulleted lists identifying the policy and
    metric categories represented in the difference data frame.
    """
    fragments = [
        f'<p>There are <strong>{len(delta)} divergent values</strong>. '
        'They differ in these policy areas:</p><ul>',
        *(f'<li>{policy}</li>' for policy in delta['policy_area'].unique()),
        '</ul><p>They also differ in these metrics:</p><ul>',
        *(f'<li>{metric}</li>' for metric in delta['metric'].unique()),
        '</ul>',
    ]
    return ''.join(fragments)


def csam_reports(ncmec: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the report counts for Meta and its brands from NCMEC's disclosures
    and enrich with percentage shares for Meta vs Total as well as WhatsApp vs
    Meta.
    """

    meta = ncmec[['Facebook', 'Instagram', 'Meta', 'WhatsApp']].sum(axis=1)
    return (
        ncmec['Total']
        .to_frame()
        .rename(columns={0: 'Total'})
        .assign(**{'%': lambda df: meta / df['Total'] * 100})
        .assign(Meta=meta)
        .assign(Facebook=ncmec['Facebook'])
        .assign(Instagram=ncmec['Instagram'])
        .assign(WhatsApp=ncmec['WhatsApp'])
        .assign(**{'% Meta': lambda df: df['WhatsApp'] / df['Meta'] * 100})
    )
