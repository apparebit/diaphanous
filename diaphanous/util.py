from collections import defaultdict
import math
from typing import Literal

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


def make_empty_year(year: int) -> pl.DataFrame:
    """Create a new data frame for the given year without providing an actual
    age distribution."""
    return pl.DataFrame().with_columns(
        pl.lit(year, dtype=pl.Int16).alias("data_year"),
        pl.lit(None, dtype=pl.Int8).alias("age"),
        pl.lit(None, dtype=pl.String).alias("sex"),
        pl.lit(None, dtype=pl.String).alias("ethnicity"),
        pl.lit(None, dtype=pl.String).alias("activity"),
        pl.lit(None, dtype=pl.Float64).alias("count"),
    )


def add_empty_year(frame: pl.DataFrame, year: int) -> pl.DataFrame:
    """Append a data frame for an empty year."""
    return pl.concat([frame, make_empty_year(year)])


def add_group_rank[F: (pl.DataFrame, pl.LazyFrame)](frame: F) -> F:
    return frame.with_columns(
        pl.col("age_group").replace({
            "Child": 1,
            "Juvenile": 2,
            "Adult": 3,
        }, return_dtype=pl.Int8).alias("group_rank")
    )


def add_age_group[F: (pl.DataFrame, pl. LazyFrame)](
    frame: F,
    juvenile_min: int,
    juvenile_max: int,
) -> F:
    frame = frame.with_columns(
        pl.when(
            pl.col("age").lt(juvenile_min)
        ).then(
            pl.lit("Child", dtype=pl.String)
        ).when(
            pl.col("age").le(juvenile_max)
        ).then(
            pl.lit("Juvenile", dtype=pl.String)
        ).when(
            pl.col("age").gt(juvenile_max)
        ).then(
            pl.lit("Adult", dtype=pl.String)
        ).alias("age_group"),
    )
    return add_group_rank(frame)


def add_country_material_role(
    frame: pl.DataFrame,
    country: str,
    material: Literal["Porn", "CSAM"],
    role: Literal["Suspect", "Offender", "Arrestee"],
) -> pl.DataFrame:
    return frame.insert_column(
        0, pl.lit(country, dtype=pl.String).alias("country")
    ).insert_column(
        1, pl.lit(material, dtype=pl.String).alias("material")
    ).insert_column(
        2, pl.lit(role, dtype=pl.String).alias("role")
    )


def arrange_age_distribution(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(
        pl.col(
            *grouping_columns(frame),
            "age", "age_group", "group_rank",
            "sex", "ethnicity", "activity",
            "count"
        )
    )


def regularize_age_distribution(frame: pl.DataFrame, *variables: str) -> pl.DataFrame:
    # Preserving the index columns means retaining them in the template or the
    # frame. While retaining them in the template results in redundant rows that
    # must be removed again, retaining them in the frame results in cells with
    # null values, which would have to be refilled. Removing redundant rows
    # seems easier.
    index = [
        c for c in ("country", "material", "role", "metric") if c in frame.columns
    ]

    # Compute lists with unique variable values.
    template = frame.select(
        pl.col(*index),
        pl.col(*variables).unique().implode(),
    )

    # Explode each list into a column. Index columns cause redundant rows.
    for variable in variables:
        template = template.explode(variable)

    # Remove redundant rows again before joining.
    return template.unique().join(
        frame.drop(*index),
        on=list(variables),
        how="left",
        nulls_equal=True,
    ).with_columns(
        pl.col("count").fill_null(0)
    ).group_by(
        *index, *variables
    ).agg(
        pl.col("count").sum()
    )


def compute_age_cdfs(frame: pl.DataFrame) -> pl.DataFrame:
    frame = frame.drop_nulls(["age", "sex"])
    group = grouping_columns(frame)

    males = _compute_age_cdf(
        frame.filter(pl.col("sex").eq("Male")), group, "male_cdf"
    )
    females = _compute_age_cdf(
        frame.filter(pl.col("sex").eq("Female")), group, "female_cdf"
    )

    return males.join(
        females,
        on=[*group, "age"],
        how="inner",
        maintain_order="left",
    )


def _compute_age_cdf(
    frame: pl.DataFrame, index_columns: list[str], cdf_column: str
) -> pl.DataFrame:
    # Create a blueprint for full range of age values
    table = defaultdict(list)
    for row in frame.select(*index_columns).unique().rows():
        for name, value in zip(index_columns, row):
            table[name].extend([value] * 101)
        table["age"].extend([y for y in range(101)])

    # Build CDF from counts shifted by one row: (age, cdf): (0, 0.0) -> (100, 1.0)
    return pl.DataFrame(table).join(
        frame.group_by(
            *index_columns, "age",
            maintain_order=True,
        ).agg(
            pl.col("count").sum().alias(cdf_column)
        ),
        on=[*index_columns, "age"],
        how="left",
        maintain_order="left",
    ).fill_null(
        0
    ).sort(
        *index_columns, "age"
    ).with_columns(
        pl.col(cdf_column).shift(fill_value=0).cum_sum().over(*index_columns)
    ).with_columns(
        pl.col(cdf_column).truediv(pl.col(cdf_column).max()).over(*index_columns)
    )


def compute_age_sex_cdf_extrema(frame: pl.DataFrame) -> pl.DataFrame:
    group = grouping_columns(frame)[:-1]
    return _compute_cdf_extrema(frame, group, "male_cdf").join(
        _compute_cdf_extrema(frame, group, "female_cdf"),
        on=[*group, "age"],
        how="inner",
    )


def _compute_cdf_extrema(
    frame: pl.DataFrame, group: list[str], column: str
) -> pl.DataFrame:
    return frame.group_by(
        *group, "age", maintain_order=True
    ).agg(
        pl.col(column).min().alias(f"min_{column}"),
        pl.col(column).max().alias(f"max_{column}"),
    )


def grouping_columns(frame: pl.DataFrame) -> list[str]:
    group = []
    for candidate in ("country", "material", "role", "metric", "data_year"):
        if candidate in frame.columns:
            group.append(candidate)
    return group


def get_year_range(frame: pl.DataFrame) -> tuple[int, int]:
    return frame.select(
        pl.col("data_year").min().alias("min"),
        pl.col("data_year").max().add(1).alias("max"),
    ).row(0)


def to_axis_range(min: float, max: float) -> tuple[int, int, int]:
    assert min <= 0, "minimum must be non-positive"
    min_sign = -1 if min < 0 else 0
    min_magnitude = abs(min)
    diff = max - min

    for limit in (10, 50, 100, 200, 500, 1_000, 5_000):
        if diff <= limit:
            factor = limit // 10
            return (
                min_sign * math.ceil(min_magnitude / factor) * factor,
                factor,
                math.ceil(max / factor) * factor,
            )

    return (
        min_sign * math.ceil(min_magnitude / 1_000) * 1_000,
        1_000,
        math.ceil(max / 1_000) * 1_000
    )


def rate_pvalue(pvalue: float) -> str:
    if pvalue <= 0.0001:
        return "★★★★"
    elif pvalue <= 0.001:
        return "★★★"
    elif pvalue <= 0.01:
        return "★★"
    elif pvalue <= 0.05:
        return "★"
    else:
        return "p > 0.05"
