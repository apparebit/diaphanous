from pathlib import Path
from typing import Callable

import pandas as pd

from show import BlockContent, mx


# Metrics with integer counts as values.
COUNT = (
    'Content Actioned',
    'Content Appealed',
    'Content Restored with appeal',
    'Content Restored without appeal',
)

# Metrics with percentages as values.
PERCENT = (
    'Proactive rate',
    'UBP',
    'Prevalence',
    'Lowerbound Prevalence',
    'Upperbound Prevalence',
)

# The schema of Meta's transparency disclosures.
SCHEMA = {
    'app': 'category',
    'policy_area': 'category',
    'metric': 'category',
    'period': 'period[Q]',
    'value': 'string',
}


def parse_counts(df: pd.DataFrame) -> pd.Series:
    """Parse all values that are integer counts."""
    return (
        df.loc[df['metric'].isin(COUNT), 'value'].str.replace(',', '').astype('Float64')
    )


def parse_percents(df: pd.DataFrame) -> pd.Series:
    """Parse all values that are percentages."""
    return df.loc[df['metric'].isin(PERCENT), 'value'].str.rstrip('%').astype('Float64')


_Q4_2022 = pd.Period('2022q4')
_Q1_2023 = pd.Period('2023q1')


def read(path: str | Path, quarter: str | pd.Period) -> pd.DataFrame:
    """
    Read Meta's transparency disclosures for the given quarter. The prevalence
    of fake accounts for Q4 2022 and Q1 2023 is not a percentage but the range
    "4%-5%". This function normalizes the value to 4.5%.
    """
    if isinstance(quarter, str):
        quarter = pd.Period(quarter)

    path = Path(path) / f'meta-q{quarter.quarter}-{quarter.year}.csv'
    # mypy madness: read_csv's dtype accepts defaultdict but not dict.
    data = pd.read_csv(path, dtype=SCHEMA)  # type: ignore[arg-type]

    # Quick and dirty mitigation against unusual value "4%-5%":
    if quarter == _Q4_2022 or quarter == _Q1_2023:
        fake_account_prevalence = (data['policy_area'] == 'Fake Accounts') & (
            data['metric'] == 'Prevalence'
        )
        assert len(data[fake_account_prevalence]) == 1
        data.loc[fake_account_prevalence, 'value'] = "4.5%"

    return (
        data.assign(count=parse_counts)
        .assign(percent=parse_percents)
        .assign(value=lambda df: df['count'].fillna(df['percent']))
        .drop(columns=['count', 'percent'])
    )


def read_all(
    path: str | Path, first: str | pd.Period, last: str | pd.Period
) -> dict[pd.Period, pd.DataFrame]:
    if isinstance(first, str):
        first = pd.Period(first)
    if isinstance(last, str):
        last = pd.Period(last)

    disclosures = {}

    cursor = first
    while cursor <= last:
        disclosures[cursor] = read(path, cursor)
        cursor += 1

    return disclosures


def diff(
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


def period2label(period: pd.Period) -> str:
    return f'_q{period.quarter}_{period.year}'


def diff_all(
    disclosures: dict[pd.Period, pd.DataFrame]
) -> dict[pd.Period, pd.DataFrame]:
    """
    Compute the difference between a period's dataframe and the next period's
    dataframe, starting with the earliest one. This function assumes that the
    given disclosures cover a range of consecutive periods.
    """
    cursor = min(*disclosures.keys())
    last = max(*disclosures.keys())

    label1 = period2label(cursor)
    data1 = disclosures[cursor]
    differences = {}

    while cursor < last:
        next_cursor = cursor + 1
        label2 = period2label(next_cursor)
        data2 = disclosures[next_cursor]

        differences[cursor] = diff(label1, data1, label2, data2)

        cursor = next_cursor
        label1 = label2
        data1 = data2

    return differences


def quarterly_divergent(delta: pd.DataFrame) -> pd.DataFrame:
    return delta.groupby('period').size().to_frame().rename(columns={0: 'divergent'})


def print_divergent_descriptors(delta: pd.DataFrame, *, use_sgr: bool = False) -> None:
    sgr: Callable[[int], str] = (lambda v: f'\x1b[{v}m') if use_sgr else (lambda _: '')

    print('\n' + sgr(1) + 'Divergent policy areas:' + sgr(0))
    for policy_area in delta['policy_area'].unique():
        print('  •', policy_area)

    print('\n' + sgr(1) + 'Divergent metrics:' + sgr(0))
    for metric in delta['metric'].unique():
        print('  •', metric)

    print()


def divergent_descriptors(delta: pd.DataFrame) -> list[BlockContent]:
    blocks: list[BlockContent] = [
        mx.p('There are ', mx.strong(f'{len(delta)} divergent values'),
             '. They differ in these policy areas:')
    ]
    policies = [mx.li(policy) for policy in delta['policy_area'].unique()]
    blocks.append(mx.ul(*policies))
    blocks.append(mx.p('They also differ in these metrics:'))
    metrics = [mx.li(metric) for metric in delta['metric'].unique()]
    blocks.append(mx.ul(*metrics))
    return blocks


def fraction_of_reports(ncmec: pd.DataFrame) -> pd.DataFrame:
    return (
        ncmec[['Facebook', 'Instagram', 'Meta', 'WhatsApp']]
        .sum(axis=1)
        .to_frame()
        .rename(columns={0: 'Meta'})
        .assign(Total=ncmec['Total'])
        .assign(**{'Meta Percent': lambda df: df['Meta'] / df['Total'] * 100})
    )
