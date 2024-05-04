from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
import re
from typing import cast, Callable, ClassVar, Literal, NamedTuple, TypeAlias

import pandas as pd
from pandas.api.types import is_integer_dtype

from .type import (
    CellType,
    DisclosureType,
    DisclosureCollectionType,
    RowType,
    SchemaEntryType,
)


# --------------------------------------------------------------------------------------
# Index Values


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


_InternalSchemaEntry: TypeAlias = Literal["Int64", "float64", "string"]

_SCHEMA_ENTRIES: dict[SchemaEntryType, _InternalSchemaEntry] = {
    "int": "Int64",
    "float": "float64",
    "string": "string",
}


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


def _ingest_cell(
    platform: str,
    cell: CellType,
    column: str,
    typed: _InternalSchemaEntry,
) -> CellType:
    # All columns are implicitly nullable.
    if cell is None:
        return None

    # If the schema requires strings, the cell must be a string.
    if typed == "string":
        if not isinstance(cell, str):
            raise ValueError(
                f'{platform}\'s "{column}" column contains non-string "{cell}"'
            )
        return cell

    # If the schema requires integers, the cell must be an integer.
    if typed == "Int64":
        if not isinstance(cell, int):
            raise ValueError(
                f'{platform}\'s "{column}" column contains non-integer "{cell}"'
            )
        return cell

    # The schema requires a float. Both int and float cells will do.
    if isinstance(cell, (int, float)):
        return cell

    # The cell better be a valid percentage expression.
    if not isinstance(cell, str):
        raise ValueError(
            f'{platform}\'s "{column}" contains invalidly typed "{cell}"'
        )

    match = Percentage.FORMAT.match(cell)
    if match is None:
        raise ValueError(
            f'{platform}\'s "{column}" contains invalid percentage expression "{cell}"'
        )
    percent, total = match.groups()
    return Percentage(float(percent), int(total.replace(",", "")))


# --------------------------------------------------------------------------------------
# Rows


_REDUNDANT = frozenset({"redundant"})


def _ingest_row(
    platform: str,
    row: RowType,
    columns: Sequence[str],
    schema: dict[str, _InternalSchemaEntry],
    include_redundant: bool = False,
) -> None | tuple[pd.Period, list[CellType]]:
    keys = row.keys() - _REDUNDANT
    if len(keys) != 1:
        raise ValueError(f'{platform}\'s row "{row}" does not have expected entries')
    if (is_redundant := row.get("redundant") is True) and not include_redundant:
        return None

    (index,) = keys
    cells = cast(list[CellType], row[index])
    if len(cells) != len(columns):
        raise ValueError(
            f"{platform}'s row has {len(cells)} cells instead of {len(columns)}"
        )

    row_index = _ingest_period(platform, index)
    row_data = [
        _ingest_cell(platform, cell, column, schema[column])
        for cell, column in zip(cells, columns)
    ]

    if include_redundant:
        return (row_index, [*row_data, is_redundant])
    return (row_index, row_data)


def _ingest_table(
    platform: str, data: DisclosureType, include_redundant: bool = False
) -> pd.DataFrame:
    # Warm up.
    columns = list(data["columns"])
    raw_schema = data.get("schema", {})

    # Elaborate schema.
    schema: dict[str, _InternalSchemaEntry] = {}
    for column in columns:
        if column == "redundant":
            raise ValueError(f'{platform} has column named "redundant"')

        type_name = raw_schema.get(column, "int")
        if type_name not in _SCHEMA_ENTRIES:
            raise ValueError(
                f'{platform}\'s schema for "{column}" has invalid type "{type_name}"'
            )
        schema[column] = _SCHEMA_ENTRIES[type_name]

    # Ingest rows.
    indexed_rows = []
    for row_data in data["rows"]:
        row = _ingest_row(
            platform, row_data, columns, schema, include_redundant=include_redundant
        )
        if row:
            indexed_rows.append(row)

    index, rows = zip(*indexed_rows) if indexed_rows else ([], [])

    # When preserving redundant rows, patch columns and schema.
    if include_redundant:
        columns.append("redundant")
        schema["redundant"] = "bool"

    # Leverage schema for better dataframe typing.
    df = pd.DataFrame(rows, index=index, columns=columns).astype(schema)
    df.index.name = 'period'
    return df


def _compute_columns(
    platform: str, data: DisclosureType, table: pd.DataFrame
) -> pd.DataFrame:
    if "sums" not in data and "products" not in data:
        return table

    for computation in ("sums", "products"):
        if computation not in data:
            continue

        for target, sources in data[computation].items():
            if target in table.columns:
                raise ValueError(f"{platform} tries to recompute {target} column")
            if len(sources) == 0:
                raise ValueError(f"{platform} tries to compute {target} from nothing")
            for source in sources:
                if source not in table.columns:
                    raise ValueError(
                        f"{platform} tries to compute {target} "
                        f"from non-existent {source} column"
                    )

    for computation in ("sums", "products"):
        if computation not in data:
            continue

        for target, sources in data[computation].items():
            if all(is_integer_dtype(table.dtypes[c]) for c in sources):
                dtype = "Int64"
            else:
                dtype = "float64"

            table[target] = (
                getattr(table[list(sources)], computation[:-1])(axis=1, min_count=1)
                .astype(dtype)
            )

    return table


class PlatformData(NamedTuple):
    disclosures: dict[str, pd.DataFrame]
    brands: dict[str, tuple[str,...]]
    features: pd.DataFrame


_TABLE_FIELDS = frozenset(["columns", "rows", "schema"])
_FEATURE_FIELDS = frozenset([
    "data", "history", "terms", "quantities", "granularity", "frequency", "coverage"])


def ingest_reports_per_platform(
    raw_data: DisclosureCollectionType,
    include_redundant: bool = False,
    logger: None | Callable[..., None] = None,
) -> PlatformData:
    # Define verbose logger.
    if logger is None:
        logger = lambda *args, **kwargs: None

    disclosures = {}
    brands = {}
    all_features = {}

    for platform, record in raw_data.items():
        # Skip metadata and platforms without disclosure record.
        if platform == "@":
            logger("Skipping metadata")
            continue
        if record is None:
            logger("❌ {} (no transparency disclosures)", platform)
            all_features[platform] = {}
            continue

        # Record brand relationships.
        record = cast(DisclosureType, record)
        if "brands" in record:
            brands[platform] = record["brands"]

        # Record (a copy of the) features.
        features = dict(record.get("features", {}))
        if len(features):
            if _FEATURE_FIELDS != features.keys():
                raise ValueError(
                    f'feature keys are {", ".join(features.keys())} and not '
                    f'{", ".join(_FEATURE_FIELDS)}'
                )
            features["terms"] = "; ".join(features["terms"])
            features["has_reports"] = (
                "reports" in record.get("columns", [])
                or "reports" in record.get("sums", {})
                or "reports" in record.get("products", {})
            )

        all_features[platform] = features

        # Check that disclosure record has either none or all required table properties.
        missing = _TABLE_FIELDS - record.keys()
        if missing == _TABLE_FIELDS or len(record["rows"]) == 0:
            logger("❌ {} (no CSAM data)", platform)
            continue
        if len(missing) > 0 and missing != {"schema"}:
            s = ", ".join(set(missing) - set(["schema"]))
            raise ValueError(f"{platform}'s disclosure record lacks field(s) {s}")

        # Ingest table with platform's CSAM disclosures.
        logger("✅ {}", platform)
        table = _ingest_table(platform, record, include_redundant=include_redundant)

        # Compute sums and products.
        table = _compute_columns(platform, record, table)

        if platform == 'NCMEC':
            table = table.sort_index()

        disclosures[platform] = table

    features = pd.DataFrame(all_features).transpose()
    features.index.name = 'platform'

    # Drop notifications_sent and response_time columns.
    # Combine rows for same year and platform.
    disclosures["NCMEC"] = (
        disclosures["NCMEC"]
        .groupby(["period", "platform"])
        ["reports"]
        .sum(min_count=1)
        .reset_index(level="platform")
    )

    return PlatformData(disclosures, brands, features)


def combine_brands(data: PlatformData) -> dict[str, pd.DataFrame]:
    """
    Compute a new version of the disclosures that has the same entries as the
    original version but with only entries for individual firms and not brands.
    """
    disclosures = dict(data.disclosures)
    for firm_name, brands in data.brands.items():
        firm_data = disclosures.get(firm_name)
        schema = None if firm_data is None else firm_data.dtypes

        for brand in brands:
            if brand not in disclosures:
                continue

            table = disclosures[brand]
            if firm_data is None:
                firm_data = table
                schema = table.dtypes
            else:
                firm_data = firm_data.add(table, fill_value=0)

            del disclosures[brand]

        if firm_data is not None:
            disclosures[firm_name] = firm_data.astype(schema)

    return disclosures


def wide_ncmec_reports(
    data: PlatformData,
    combine_brands: bool = True,
    drop_brands: bool = True,
) -> pd.DataFrame:
    # Pivot without dropna so that placeholder columns for brands can be
    # combined. Force type to Int64 b/c Pandas gets confused by NA, typing
    # columns as float64 (for pivot) or object (for sum).
    ncmec = (
        data.disclosures['NCMEC']
        .pivot_table(values='reports', index='period', columns='platform', dropna=False)
        .astype('Int64')
    )

    if combine_brands:
        for firm, brands in data.brands.items():
            ncmec = ncmec.assign(**{
                firm: lambda df: (
                    df[[firm, *brands]]
                    .sum(axis=1, min_count=1)
                    .astype('Int64')
                )
            })

            if drop_brands:
                ncmec = ncmec.drop(columns=list(brands))

    return ncmec


def long_ncmec_reports(
    data: PlatformData,
    combine_brands: bool = True,
    drop_brands: bool = True,
) -> pd.DataFrame:
    ncmec = (
        data.disclosures['NCMEC']
        #.drop(columns=['notifications_sent', 'response_time'])
    )

    if combine_brands:
        for firm, brands in data.brands.items():
            ncmec.loc[ncmec['platform'] == firm, 'reports'] = (
                ncmec
                .loc[ncmec['platform'].isin([firm, *brands]), 'reports']
                .groupby('period')
                .sum(min_count=1)
            )
            if drop_brands:
                ncmec = ncmec.loc[~ncmec['platform'].isin(brands)]

    return ncmec.sort_values(['period', 'platform'])
