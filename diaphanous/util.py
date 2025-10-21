import math

import polars as pl
import great_tables as gt

from ._const import TOTAL


def configure() -> None:
    """Configure Pola.rs to print readable tables."""
    pl.Config.set_tbl_cols(20)
    pl.Config.set_thousands_separator(",")
    pl.Config.set_float_precision(1)
    pl.Config.set_tbl_cell_numeric_alignment('RIGHT')
    pl.Config.set_tbl_rows(200)


def to_schema(frame: pl.DataFrame) -> pl.DataFrame:
    """Get the data frame's schema as a data frame."""
    return pl.DataFrame({
        "column": frame.schema.names(),
        "dtype": frame.schema.dtypes(),
    })


def to_title(label: str) -> str:
    """
    Convert a label or similar string into a human-readable title.

    This function replaces underscores with spaces and capitalizes each word,
    unless it is a well-known acronym or connective.
    """
    words = []
    for word in label.replace("_", " ").split():
        word = word.lower()
        if word in ("and", "in", "of", "or"):
            pass
        elif word in ("pd",):
            word = word.upper()
        else:
            word = word.capitalize()
        words.append(word)
    return " ".join(words)


def with_total_and_percent(
    table: pl.DataFrame, name: str = "Variant", count: str = "Count"
) -> pl.DataFrame:
    """
    Add a new row with the total count and a new column with percentage values
    to the data frame.
    """
    total = table.select(pl.col(count).sum()).item()

    data: dict[str, list[None | str]] = {column: [None] for column in table.columns}
    data[name] = [TOTAL]
    data[count] = [total]
    total_row = pl.DataFrame(data).with_columns(pl.col(count).cast(pl.Int64))

    return pl.concat([table, total_row]).with_columns(
        (pl.col(count) / total).alias("Percent")
    )


def format_table(frame: pl.DataFrame, title: None | str = None) -> gt.GT:
    """Format the given data frame as a good-looking table"""
    table = gt.GT(frame)
    if title is not None:
        table = table.tab_header(title)

    first = frame.columns[0]
    if first.casefold() in ("variant", "year"):
        table = table.tab_stub(rowname_col=first)

    percent_columns = []
    for column in frame.columns:
        name = column.casefold()
        if "percent" in name or "pct" in name or "%" in name:
            percent_columns.append(column)

    return (
        table
        .fmt_integer(
            columns=[c for c in frame.columns if frame.schema[c].is_integer()]
        )
        .fmt_percent(
            columns=percent_columns,
            decimals=1,
        )
        .tab_options(table_font_names=gt.system_fonts("industrial"))
        .sub_missing(missing_text="")
        .opt_horizontal_padding(scale=2)
    )


def add_group_rank(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.with_columns(
        pl.col("age_group").replace({
            "Child": 1,
            "Juvenile": 2,
            "Adult": 3,
        }, return_dtype=pl.Int8).alias("group_rank")
    )


def add_age_group(
    frame: pl.DataFrame,
    juvenile_min: int,
    juvenile_max: int,
) -> pl.DataFrame:
    return frame.with_columns(
        pl.when(
            pl.col("age").lt(juvenile_min)
        ).then(
            pl.lit("Child", dtype=pl.String),
        ).otherwise(
            pl.when(
                pl.col("age").le(juvenile_max)
            ).then(
                pl.lit("Juvenile", dtype=pl.String),
            ).otherwise(
                pl.lit("Adult", dtype=pl.String)
            )
        ).alias("age_group"),
    ).pipe(
        add_group_rank
    )


def add_country_entity(frame: pl.DataFrame, country: str, entity: str) -> pl.DataFrame:
    return frame.insert_column(
        0, pl.lit(country, dtype=pl.String).alias("country")
    ).insert_column(
        1, pl.lit(entity, dtype=pl.String).alias("entity")
    )


def arrange_age_distribution(frame: pl.DataFrame) -> pl.DataFrame:
    prefix = []
    if "country" in frame.columns:
        prefix.append("country")
    if "entity" in frame.columns:
        prefix.append("entity")

    return frame.select(
        pl.col(
            *prefix,
            "data_year",
            "age", "age_group", "group_rank",
            "sex", "ethnicity", "activity",
            "count"
        )
    )


def to_step_and_limit(num: float) -> tuple[int, int]:
    for limit in (10, 50, 100, 500, 1_000, 5_000):
        if num <= limit:
            factor = limit // 10
            return factor, math.ceil(num / factor) * factor
    return 1_000, math.ceil(num / 1_000) * 1_000
