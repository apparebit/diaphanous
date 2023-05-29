from pathlib import Path

import pandas as pd


COUNT = (
    'Content Actioned',
    'Content Appealed',
    'Content Restored with appeal',
    'Content Restored without appeal',
)

PERCENT = (
    'Proactive rate',
    'UBP',
    'Prevalence',
    'Lowerbound Prevalence',
    'Upperbound Prevalence',
)

SCHEMA = {
    'app': 'category',
    'policy_area': 'category',
    'metric': 'category',
    'period': 'period[Q]',
    'value': 'string',
}


def parse_counts(df) -> pd.DataFrame:
    return (
        df.loc[df['metric'].isin(COUNT), 'value']
        .str.replace(',', '')
        .astype('Float64')
    )


def parse_percents(df) -> pd.DataFrame:
    return (
        df.loc[df['metric'].isin(PERCENT), 'value']
        .str.rstrip('%')
        .astype('Float64')
    )


_Q4_2022 = pd.Period('2022q4')


def read(path: str | Path, quarter: str | pd.Period) -> pd.DataFrame:
    if isinstance(quarter, str):
        quarter = pd.Period(quarter)

    path = Path(path) / f'meta-q{quarter.quarter}-{quarter.year}.csv'
    # mypy madness: read_csv's dtype accepts defaultdict but not dict.
    data = pd.read_csv(path, dtype=SCHEMA) # type: ignore[arg-type]

    # Quick and dirty mitigation against unusual value "4%-5%":
    if quarter == _Q4_2022:
        data.loc[
            (data['policy_area'] == 'Fake Accounts') & (data['metric'] == 'Prevalence'),
            'value'
        # More mypy madness: loc[] accepts scalar values, just not pd.NA.
        ] = pd.NA # type: ignore[call-overload]

    return (
        data
        .assign(count=parse_counts)
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
