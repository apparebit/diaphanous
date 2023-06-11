from dataclasses import dataclass
import re
from typing import cast, Callable, ClassVar

import pandas as pd

from .type import (
    CellType,
    DisclosureType,
    DisclosureCollectionType,
    RowType,
)

# --------------------------------------------------------------------------------------
# Index Values


def _ingest_name(platform: str, name: str) -> str:
    return name


_PERIOD_FORMAT = re.compile(r"^(?P<year>\d{4})(?:[ ](?P<tag>(?:H[12])|(?:Q[1-4])))?$")


def _ingest_period(platform: str, period: str) -> pd.Period:
    match = _PERIOD_FORMAT.match(period)
    if match is None:
        raise ValueError(f'{platform}\'s "{period}" is not a valid period')

    year, tag = match.groups()
    if tag is None:
        return pd.Period(year, freq="Y")
    if tag[0] == "H":
        return pd.Period(f"{year}-0{1 + (int(tag[1]) - 1) * 6}", freq="6M")
    return pd.Period(year + tag, freq="Q")


# --------------------------------------------------------------------------------------
# Cell Values


@dataclass(frozen=True)
class Percentage(float):
    FORMAT: ClassVar[re.Pattern] = re.compile(
        r"^(?P<percent>\d+\.\d+)\s*/\s*100\s*\*\s*(?P<total>\d[\d,]*\d|\d)$"
    )

    percent: float
    total: int

    def __new__(cls, percent: float, total: int) -> "Percentage":
        return float.__new__(cls, percent / 100.0 * total)

    def __str__(self) -> str:
        return f"{self.percent} / 100 * {self.total}"


def _ingest_number(
    platform: str, number: None | int | float | str
) -> None | int | float:
    if not isinstance(number, str):
        return number

    match = Percentage.FORMAT.match(number)
    if match is None:
        raise ValueError(
            f'{platform}\'s string "{number}" is not a valid percentage expression'
        )

    percent, total = match.groups()
    return Percentage(float(percent), int(total.replace(",", "")))


# --------------------------------------------------------------------------------------
# Rows


def _is_redundant(row: RowType) -> bool:
    return row.get("redundant") is True


def _ingest_row(
    platform: str,
    width: int,
    row: RowType,
    ingest_index: Callable[[str, str], str | pd.Period],
    include_redundant: bool = False,
) -> None | tuple[str | pd.Period, list[None | int | float]]:
    if len(row) == 2 and "redundant" in row:
        if not include_redundant and row["redundant"]:
            return None
    elif len(row) != 1:
        raise ValueError(f'{platform}\'s row "{row}" should have exactly one entry')

    for index, numbers in row.items():
        if index == "redundant":
            continue

        numbers = cast(list[CellType], numbers)
        if len(numbers) != width:
            raise ValueError(
                f"{platform}'s row has {len(numbers)} elements instead of {width}"
            )

        row_index = ingest_index(platform, index)
        row_data = [_ingest_number(platform, num) for num in numbers]
        if include_redundant:
            return (row_index, [*row_data, _is_redundant(row)])
        return (row_index, row_data)

    assert False, "unreachable statement"


def _ingest_table(
    platform: str, data: DisclosureType, include_redundant: bool = False
) -> pd.DataFrame:
    # Determine columns and function to ingest index values.
    columns: list[str | pd.Period]
    ingest_index: Callable[[str, str], str | pd.Period]

    if data["row_index"] == "period":
        columns = [column for column in data["columns"]]
        ingest_index = _ingest_period
    elif include_redundant:
        raise ValueError(
            f"{platform}: including redundant rows requires periods as row index"
        )
    else:
        columns = [_ingest_period(platform, period) for period in data["columns"]]
        ingest_index = _ingest_name
    width = len(columns)

    # Ingest rows.
    all_rows = []
    for row_data in data["rows"]:
        labelled_row = _ingest_row(
            platform, width, row_data, ingest_index, include_redundant=include_redundant
        )
        if labelled_row:
            all_rows.append(labelled_row)
    index, plain_rows = zip(*all_rows)

    # Create dataframe and then coerce integer columns to more restrictive type.
    nonintegers = set(data["nonintegers"]) if "nonintegers" in data else set()
    schema = {c: ("float64" if c in nonintegers else "Int64") for c in columns}
    if include_redundant:
        schema['redundant'] = 'bool'
        columns.append('redundant')
    return pd.DataFrame(plain_rows, index=index, columns=columns).astype(schema)


_TABLE_FIELD = set(["row_index", "columns", "rows", "nonintegers"])


def ingest_reports_per_platform(
    raw_data: DisclosureCollectionType,
    include_redundant: bool = False,
    logger: None | Callable[..., None] = None,
) -> dict[str, pd.DataFrame]:
    # Define verbose logger.
    if logger is None:
        logger = lambda *args, **kwargs: None

    disclosures = {}
    for platform, record in raw_data.items():
        # Skip metadata and platforms without disclosure record.
        if platform == "@":
            logger("Skipping metadata")
            continue
        if record is None:
            logger("Skipping {}: no transparency disclosures", platform)
            continue

        # Check that disclosure record has either no or all required table properties.
        record = cast(DisclosureType, record)
        missing = []
        for field in _TABLE_FIELD:
            if field not in record:
                missing.append(field)

        if len(missing) == len(_TABLE_FIELD):
            logger("Skipping {}: no CSAM data", platform)
            continue
        if len(missing) > 1 or (len(missing) == 1 and missing[0] != "nonintegers"):
            s = ", ".join(set(missing) - set(["noninteger"]))
            raise ValueError(f"{platform}'s disclosure record lacks field(s) {s}")

        # Ingest table with platform's CSAM disclosures.
        logger("Ingesting CSAM data for {}", platform)
        redundant = include_redundant
        if record['row_index'] != 'period':
            redundant = False
        table = _ingest_table(platform, record, include_redundant=redundant)
        if record["row_index"] != "period":
            table = table.transpose()
            table.index.name = 'period'
        if platform == 'NCMEC':
            table = table.sort_index()
        disclosures[platform] = table

    return disclosures
