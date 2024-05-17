from typing import Self
import pandas as pd


def annualize(series: pd.Series) -> pd.Series:
    """
    Annualize the data in the series. The resulting series has yearly periods as
    index. The corresponding values are only non-null if there are values
    covering the entire year in the original series.
    """
    coverage: dict[int, bool | list[bool]] = {}

    def add(period: pd.Period) -> None:
        entry = coverage.setdefault(period.year, [False, False, False, False])
        if entry is True:
            return

        freq = period.freqstr
        if freq == 'A-DEC':
            for index in range(4):
                entry[index] = True
        elif freq == '6M':
            if period.quarter == 1:
                entry[0] = True
                entry[1] = True
            else:
                entry[2] = True
                entry[3] = True
        elif freq == 'Q-DEC':
                entry[period.quarter] = True

        if all(*entry):
            coverage[period.year] = True

    for period, value in series.items():
        if not pd.isnull(value):
            add(period)

    years = []
    counts = []
    for current_period, current_value in series.items():
        current_year = current_period.year
        if len(years) == 0 or years[-1] != current_year:
            years.append(current_year)
            counts.append(0 if coverage[current_year] is True else None)

        current_count = counts[-1]
        if current_count is not None and not pd.isnull(value):
            counts[-1] = current_count + value

    return pd.Series(counts, index=[pd.Period(f'{y}') for y in years])
