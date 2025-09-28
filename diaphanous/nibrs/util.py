import polars as pl
import great_tables as gt

from .model import Column, Entry, Id


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
    table: pl.DataFrame, name: str = Column.VARIANT, count: str = Column.COUNT
) -> pl.DataFrame:
    """
    Add a new row with the total count and a new column with percentage values
    to the data frame.
    """
    total = table.select(pl.col(count).sum()).item()

    data = {column: [None] for column in table.columns}
    data[name] = [Entry.TOTAL.value]
    data[count] = [total]
    total_row = pl.DataFrame(data).with_columns(pl.col(count).cast(pl.Int64))

    return pl.concat([table, total_row]).with_columns(
        (pl.col(count) / total).alias(Column.PERCENT)
    )


def humanize_frame(frame: pl.DataFrame) -> pl.DataFrame:
    """
    Humanize NIBRS data. This function converts numeric values and one/two
    letter codes to human-readable labels. It generally assumes that columns
    still have their original names.
    """
    baptism = {}

    for column in frame.columns:
        # Handle exceptional column names
        if column in ("age", "count"):
            baptism[column] = column.title()
            continue

        # Handle members of Id.
        try:
            ident = Id(column)
        except:
            continue

        baptism[ident] = ident.name.title()

        value_range = ident.value_range()
        if value_range is None:
            continue

        frame = frame.with_columns(
            pl.col(column).cast(pl.String).replace({
                str(v): to_title(k) for k, v in value_range.__members__.items()
            })
        )

    return frame.rename(baptism)


def format_table(frame: pl.DataFrame, title: None | str = None) -> gt.GT:
    """Format the given data frame as a good-looking table"""
    table = gt.GT(frame)
    if title is not None:
        table = table.tab_header(title)

    return (
        table
        .tab_stub(rowname_col=frame.columns[0])
        .fmt_integer(
            columns=[c for c in frame.columns if frame.schema[c].is_integer()]
        )
        .fmt_percent(
            columns=[c for c in frame.columns if Column.PERCENT in c or "%" in c],
            decimals=1,
        )
        .tab_options(table_font_names=gt.system_fonts("industrial"))
        .opt_horizontal_padding(scale=2)
    )
