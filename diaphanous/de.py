from pathlib import Path
import shutil
from typing import Literal\

import polars as pl

from .nibrs.model import Id
from .util import (
    AGE_GROUP_ORDER, COUNTRIES, finish_age_distribution, MATERIALS, METRICS,
    METRIC_ORDER, OUTCOME_COLUMNS, OUTCOME_ORDER, OUTCOMES, ROLES, SEX_ORDER,
    sort_age_distribution
)

_LATEST_YEAR = 2025

_ROOT = Path(__file__).parent.parent

_DEFAULT_COLUMNS = ["id", "description", "sex", "total"]
_CHILD_RANGES = ["<6", "6-8", "8-10", "10-12", "12-14"]
_JUVENILE_RANGES = ["14-16", "16-18"]
_ADULT_RANGES = ["18-21", "21-23", "23-25", "25-30", "30-40", "40-50", "50-60", ">=60"]
_OLD_ADULT_RANGES = ["60-65", "65-70", "70-75", "75-80", ">=80"]
_AGE_RANGES = [*_CHILD_RANGES, *_JUVENILE_RANGES, *_ADULT_RANGES, *_OLD_ADULT_RANGES]

# §§ 184b, 184c StGB
_PRODUCER_IDS_V1 = ["143200", "143400", "143500", "143700"]
_CONSUMER_IDS_V1 = ["143300", "143600"]
_CHILD_PORN_IDS_V1 = ["143200", "143300", "143400"]
_YOUTH_PORN_IDS_V1 = ["143500", "143600", "143700"]

_PRODUCER_IDS_V2 = ["143210", "143220", "143510", "143520"]
_CONSUMER_IDS_V2 = ["143230", "143530"]
_CHILD_PORN_IDS_V2 = ["143210", "143220", "143230"]
_YOUTH_PORN_IDS_V2 = ["143510", "143520", "143530"]

_READ_OPTIONS_SUSPECTS = dict(
    skip_rows=9,
    column_names=[
        *_DEFAULT_COLUMNS,
        *_CHILD_RANGES,
        "child",
        *_JUVENILE_RANGES,
        "adolescent",
        "18-21",
        "<21",
        "21-23",
        "23-25",
        "21-25",
        *_ADULT_RANGES[3:],
        ">=21",
    ],
)

_COLUMN_NAMES_OLD_SUSPECTS = [
    *_DEFAULT_COLUMNS,
    ">=21",
    ">=60",
    *_OLD_ADULT_RANGES,
]

_READ_OPTIONS_OLD_SUSPECTS = dict(
    skip_rows=9,
    column_names=_COLUMN_NAMES_OLD_SUSPECTS,
)

_USE_COLUMNS_POPULATION = "B:G,I,J,L,N,O,Q:U"

_COLUMN_NAMES_POPULATION = [
    "report_year",
    "census_year",
    "total",
    "8-10",
    "10-12",
    "12-14",
    "14-16",
    "16-18",
    "18-21",
    "21-23",
    "23-25",
    "25-30",
    "30-40",
    "40-50",
    "50-60",
    ">=60",
]


def ingest_suspects() -> pl.DataFrame:
    suspects = []
    for year in range(2015, _LATEST_YEAR + 1):
        # https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/
        # PolizeilicheKriminalstatistik/2020/Bund/Tatverdaechtige/
        # BU-TV-01-T20-TV_xls.xlsx?__blob=publicationFile&v=4
        try:
            frame = pl.read_excel(
                _ROOT / "data" / "germany" / f"suspects-{year}.xlsx",
                sheet_name="T20",
                read_options=_READ_OPTIONS_SUSPECTS,
            )
        except ValueError:
            frame = pl.read_excel(
                _ROOT / "data" / "germany" / f"suspects-{year}.xlsx",
                sheet_name="BU-TV-01-T20-TV",
                read_options=_READ_OPTIONS_SUSPECTS,
            )

        if year == 2015:
            frame = frame.select(pl.exclude("__UNNAMED__24"))
            filter = pl.col("id").str.starts_with("143").and_(
                pl.col("id").str.starts_with("1430").not_()
            ).and_(
                pl.col("id").str.starts_with("1431").not_()
            )
            producers = _PRODUCER_IDS_V1
            consumers = _CONSUMER_IDS_V1
            child_porn = _CHILD_PORN_IDS_V1
            youth_porn = _YOUTH_PORN_IDS_V1
        else:
            filter = pl.col("id").str.starts_with("1432").or_(
                pl.col("id").str.starts_with("1435")
            )
            producers = _PRODUCER_IDS_V2
            consumers = _CONSUMER_IDS_V2
            child_porn = _CHILD_PORN_IDS_V2
            youth_porn = _YOUTH_PORN_IDS_V2

        suspects.append(frame.filter(
            filter
        ).insert_column(
            0,
            pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
        ).with_columns(
            pl.when(
                pl.col("id").is_in(child_porn)
            ).then(
                pl.lit("CSAM"),
            ).when(
                pl.col("id").is_in(youth_porn)
            ).then(
                pl.lit("Youth Porn"),
            ).alias(Id.MATERIAL),
            pl.col("18-21").add(pl.col(">=21")).alias("adult"),
            pl.when(
                pl.col("id").is_in(producers)
            ).then(
                pl.lit("Producer"),
            ).when(
                pl.col("id").is_in(consumers)
            ).then(
                pl.lit("Consumer"),
            ).alias(Id.ACTIVITY),
        ))

    all_suspects = pl.concat(suspects)

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Validate suspects

    assert all_suspects.select(
        pl.col("total").eq(
            pl.col("<21").add(pl.col(">=21"))
        ).all()
    ).item()

    assert all_suspects.select(
        pl.col("total").eq(
            pl.col("child").add(pl.col("adolescent")).add(pl.col("adult"))
        ).all()
    ).item()

    assert all_suspects.select(
        pl.col("<21").eq(
            pl.col("child").add(pl.col("adolescent")).add(pl.col("18-21"))
        ).all()
    ).item()

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Fill in detail for older suspects

    old_suspects = []
    for year in range(2019, _LATEST_YEAR + 1):
        if year == 2019:
            frame = pl.read_csv(
                _ROOT / "data" / "germany" / "old-suspects-2019.csv",
                encoding="latin_1",
                has_header=False,
                skip_lines=5,
                separator=";",
                new_columns=_COLUMN_NAMES_OLD_SUSPECTS,
                schema_overrides={
                    "column_1": pl.String,
                    "column_8": pl.String,
                    "column_9": pl.String,
                    "column_10": pl.String,
                    "column_11": pl.String,
                }
            ).with_columns(
                pl.col(
                    "total", ">=21", ">=60",
                    "60-65", "65-70", "70-75", "75-80", ">=80"
                ).str.replace_all(",", "").cast(pl.Int64)
            )
        else:
            frame = pl.read_excel(
                _ROOT / "data" / "germany" / f"old-suspects-{year}.xlsx",
                sheet_name="T20-TV_AK60",
                read_options=_READ_OPTIONS_OLD_SUSPECTS,
            )

        old_suspects.append(frame.filter(
            pl.col("id").str.starts_with("1432").or_(
                pl.col("id").str.starts_with("1435")
            )
        ).insert_column(
            0,
            pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
        ).drop(
            "description",
        ))

    all_suspects = all_suspects.join(
        pl.concat(old_suspects),
        on=[Id.YEAR, "id", "sex"],
        how="left",
    )

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Further validate suspects

    test_frame = all_suspects.drop_nulls([
        "total_right", ">=21_right", ">=60_right"
    ])

    assert test_frame.select(
        pl.col("total").eq(pl.col("total_right")).all()
    ).item()

    assert test_frame.select(
        pl.col(">=21").eq(pl.col(">=21_right")).all()
    ).item()

    assert test_frame.select(
        pl.col(">=60").eq(pl.col(">=60_right")).all()
    ).item()

    all_suspects = all_suspects.drop(
        "total_right", ">=21_right", ">=60_right"
    )

    return all_suspects


def ingest_incidents() -> pl.DataFrame:
    incidents = []
    for year in range(2015, _LATEST_YEAR + 1):
        if year == 2015:
            filter = pl.col("id").str.starts_with("143").and_(
                pl.col("id").str.starts_with("1430").not_()
            ).and_(
                pl.col("id").str.starts_with("1431").not_()
            )
            producers = _PRODUCER_IDS_V1
            consumers = _CONSUMER_IDS_V1
            child_porn = _CHILD_PORN_IDS_V1
            youth_porn = _YOUTH_PORN_IDS_V1
        else:
            filter = pl.col("id").str.starts_with("1432").or_(
                pl.col("id").str.starts_with("1435")
            )
            producers = _PRODUCER_IDS_V2
            consumers = _CONSUMER_IDS_V2
            child_porn = _CHILD_PORN_IDS_V2
            youth_porn = _YOUTH_PORN_IDS_V2

        incidents.append(pl.read_excel(
            _ROOT / "data" / "germany" / f"incidents-{year}.xlsx",
            sheet_name="T01",
            read_options=dict(
                skip_rows=8,
                column_names=[
                    "id",
                    "description",
                    "incidents",
                    "pct_of_total",
                    "attempted",
                    "attempted_pct",
                    "__column-7",
                    "__column-8",
                    "__column-9",
                    "__column-10",
                    "__column-11",
                    "__column-12",
                    "__column-13",
                    "solved",
                    "__column-15",
                    "suspects",
                    "male_suspects",
                    "female_suspects",
                    "__column-19",
                    "__column-20",
                ],
            ),
            schema_overrides={
                "pct_of_total": pl.Float64,
                "attempted_pct": pl.Float64,
                "__column-15": pl.Float64,
                "__column-20": pl.Float64,
            },
        ).filter(
            filter
        ).insert_column(
            0,
            pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
        ).with_columns(
            pl.when(
                pl.col("id").is_in(child_porn)
            ).then(
                pl.lit("CSAM"),
            ).when(
                pl.col("id").is_in(youth_porn)
            ).then(
                pl.lit("Youth Porn"),
            ).alias(Id.MATERIAL),
            pl.when(
                pl.col("id").is_in(producers)
            ).then(
                pl.lit("Producer"),
            ).when(
                pl.col("id").is_in(consumers)
            ).then(
                pl.lit("Consumer"),
            ).alias(Id.ACTIVITY),
        ).select(
            pl.col(
                Id.YEAR, "id", "description", Id.ACTIVITY, Id.MATERIAL,
                "incidents", "attempted", "solved",
                "suspects", "male_suspects", "female_suspects",
            )
        ))

    return pl.concat(incidents)


def compute_age_distribution(
    suspects: pl.DataFrame,
    incidents: pl.DataFrame,
    with_material: bool = False
) -> pl.LazyFrame:
    # Validate that incidents and suspects tables agree on numbers of suspects
    # ------------------------------------------------------------------------
    assert suspects.filter(
        pl.col(Id.ACTIVITY).is_not_null().and_(pl.col("sex").eq("X"))
    ).select(
        pl.col(Id.YEAR, "id", "total")
    ).join(
        incidents.filter(
            pl.col(Id.ACTIVITY).is_not_null(),
        ).select(
            pl.col(Id.YEAR, "id", "suspects")
        ),
        on=[Id.YEAR, "id"],
        how="inner",
    ).select(
        pl.col("total").eq(pl.col("suspects")).all()
    ).item()

    if not with_material:
        # Override material so that group_by()'s below effectively ignore it
        suspects = suspects.with_columns(
            pl.lit("CSAM").alias(Id.MATERIAL)
        )
        incidents = incidents.with_columns(
            pl.lit("CSAM").alias(Id.MATERIAL)
        )

    # Build actual age distribution
    known_suspects = suspects.lazy().filter(
        pl.col(Id.ACTIVITY).is_not_null().and_(pl.col("sex").ne("X"))
    ).with_columns(
        pl.col("sex").replace({"M": "Male", "W": "Female"}),
        pl.col(">=80").is_null().alias("requires_sixty_plus"),
    ).unpivot(
        on=_AGE_RANGES,
        index=[Id.YEAR, "sex", Id.ACTIVITY, Id.MATERIAL, "requires_sixty_plus"],
        variable_name="age_range",
        value_name="count",
    ).filter(
        pl.col("requires_sixty_plus").or_(
            pl.col("age_range").ne(">=60")
        )
    ).group_by(
        pl.col(Id.YEAR, "age_range", "sex", Id.ACTIVITY, Id.MATERIAL),
    ).agg(
        pl.col("count").sum(),
    ).with_columns(
        pl.when(
            pl.col("age_range").is_in(["<6", ">=60", ">=80"])
        ).then(
            pl.col("age_range").replace({
                "<6": 0,
                ">=60": 60,
                ">=80": 80,
            })
        ).otherwise(
            pl.col("age_range").str.extract(r"(\d+)-")
        ).cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age_range").is_in(["<6", ">=60", ">=80"])
        ).then(
            pl.col("age_range").replace({
                "<6": 6,
                ">=60": 100,
                ">=80": 100,
            })
        ).otherwise(
            pl.col("age_range").str.extract(r"-(\d+)")
        ).cast(pl.Int8).alias("age_last"),
    ).with_columns(
        pl.col("count").truediv(
            pl.col("age_last").sub(pl.col("age_first"))
        )
    ).select(
        pl.col(Id.YEAR),
        pl.int_ranges("age_first", "age_last", dtype=pl.Int8).alias("age"),
        pl.col("sex"),
        pl.lit(None, dtype=pl.String).alias("ethnicity"),
        pl.col(Id.ACTIVITY, Id.MATERIAL, "count"),
    ).explode("age")

    # Between 2015 and 2025 (inclusive), the number of suspects per solved
    # incident ranges from 0.979 to 1.041. Likewise, the number of solved
    # incidents per suspect ranges from 0.960 to 1.022. In other words,
    # there is an almost one-to-one correspondence between incidents and
    # suspects. We assume that this relationship also holds for unresolved
    # incidents and extend the age distribution with these counts.
    unknown_suspects = incidents.lazy().filter(
        pl.col(Id.ACTIVITY).is_not_null(),
    ).group_by(
        Id.YEAR, Id.ACTIVITY, Id.MATERIAL
    ).agg(
        pl.col("incidents", "solved").sum(),
    ).select(
        pl.col(Id.YEAR),
        pl.lit(None).cast(pl.Int8).alias("age"),
        pl.lit(None).cast(pl.String).alias("sex"),
        pl.lit(None).cast(pl.String).alias("ethnicity"),
        pl.col(Id.ACTIVITY, Id.MATERIAL),
        pl.col("incidents").sub(pl.col("solved")).cast(pl.Float64).alias("count"),
    )

    return finish_age_distribution(
        pl.concat([known_suspects, unknown_suspects]),
        country="Germany",
        material=None,
        role="Offender",
        juvenile_min=14,
        juvenile_max=17,
    )


def de_age_distribution(with_material: bool = False) -> pl.LazyFrame:
    return compute_age_distribution(
        ingest_suspects(),
        ingest_incidents(),
        with_material=with_material,
    )


def restrict_offenders[F: (pl.DataFrame, pl.LazyFrame)](frame: F) -> F:
    frame = frame.filter(
        pl.col("age").ge(18).or_(
            pl.col(Id.MATERIAL).eq("Youth Porn")
        )
    ).with_columns(
        pl.lit("CSAM", dtype=pl.Enum(MATERIALS)).alias(Id.MATERIAL),
        pl.lit("Germany CSAM Offenders", dtype=pl.Enum(METRICS)).alias("metric"),
    ).group_by(
        pl.col(
            "country", "material", "role", "metric", "metric_order",
            Id.YEAR,
            "age", "age_group", "age_group_order",
            "sex", "sex_order",
            "ethnicity",
            Id.ACTIVITY, "activity_order"
        )
    ).agg(
        pl.col("count").sum()
    )

    return sort_age_distribution(frame)


def ingest_outcomes() -> pl.DataFrame:
    # ------------------------------------------------------------------------------
    # Read outcomes data
    # ------------------------------------------------------------------------------

    outcomes = []

    # TODO: Read file for 2025 when it becomes available
    for year in range(2015, _LATEST_YEAR):
        if year < 2022:
            height = 4
            frame = pl.read_excel(
                _ROOT / "data" / "germany" / f"prosecutions-{year}.xlsx",
                sheet_name="Tab2_1_Lang",
                read_options=dict(
                    header_row=None,
                    skip_rows=9,
                    use_columns="A,D:K,T:X",
                    column_names=[
                        "crime",
                        "sex",
                        *OUTCOME_COLUMNS,
                    ],
                ),
            ).with_columns(
                pl.col("sex").replace({
                    "m": "Male",
                    "i": "*",
                }),
            )
        else:
            height = 6
            frame = pl.read_excel(
                _ROOT / "data" / "germany" / f"prosecutions-{year}.xlsx",
                sheet_name="24311-05",
                read_options=dict(
                    header_row=None,
                    skip_rows=9,
                    use_columns="C:K,T:X",
                    column_names=[
                        "crime",
                        "sex",
                        *OUTCOME_COLUMNS,
                    ],
                )
            ).with_columns(
                pl.col("crime").replace({
                    "StGB § 184 b": "184b",
                    "StGB § 184 c": "184c",
                }),
                pl.col("sex").replace({
                    "F": "Female",
                    "M": "Male",
                    "I": "*",
                }),
            )

        frame = frame.slice(
            # Select only child/youth pornography; empty rows in pre-2022 frames
            # are not materialized.
            frame.select(
                pl.col("crime").index_of("184b")
            ).item(),
            height
        ).insert_column(
            # Add year
            0,
            pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
        ).with_columns(
            # Normalize crime: Null out entries other than paragraph numbers
            pl.when(
                pl.col("crime").ne("184b").and_(pl.col("crime").ne("184c"))
            ).then(
                pl.lit(None).alias("crime")
            ).otherwise(
                pl.col("crime")
            ),
        ).with_columns(
            # Normalize crime: Fill in nulled out entries
            pl.col("crime").forward_fill(),
        )

        if year <= 2021:
            frame = pl.concat([
                frame,
                pl.concat([
                    frame.filter(
                        pl.col("sex").eq("*")
                    ),
                    frame.filter(
                        pl.col("sex").eq("Male")
                    ).with_columns(
                        pl.exclude(Id.YEAR, "crime", "sex").mul(-1),
                    )
                ]).group_by(
                    Id.YEAR, "crime"
                ).agg(
                    pl.lit("Female").alias("sex"),
                    pl.exclude(Id.YEAR, "crime", "sex").sum(),
                ),
            ]).sort(
                Id.YEAR, "crime", "sex"
            )
        else:
            frame = frame.with_columns(
                # Normalize numeric columns: Null out empty or dashed calls
                pl.exclude(Id.YEAR, "crime", "sex").replace({"-": None, " ": None}),
            ).with_columns(
                # Normalize numeric columns: Cast to Integer
                pl.exclude(Id.YEAR, "crime", "sex").cast(pl.Int64),
            )

        outcomes.append(frame)

    all_outcomes = pl.concat(outcomes)

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Validate that larger populations are the sum of constituent populations

    def assert_total_equals_sum_of_parts(prefix: Literal["adjudicated", "convicted"]):
        sum_of_parts = all_outcomes.select(
            pl.col(f"{prefix}_adults").add(
                pl.col(f"{prefix}_as_adults")
            ).add(
                pl.col(f"{prefix}_as_juveniles")
            ).add(
                pl.col(f"{prefix}_juveniles")
            ).alias("sum")
        ).get_column("sum")

        if not all_outcomes.select(
            pl.col(prefix).eq(sum_of_parts).all()
        ).item():
            faulty = all_outcomes.with_row_index().filter(
                pl.col(prefix).ne(sum_of_parts)
            )
            raise AssertionError(
                f"{prefix.capitalize()} total does not equal sum of parts: {faulty}"
            )

    assert_total_equals_sum_of_parts("adjudicated")
    assert_total_equals_sum_of_parts("convicted")

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Validate that rows with data on men have the correct crime labels and
    # that each label appears the exact number of times

    outcomes_for_men = all_outcomes.filter(
        pl.col("sex").eq("Male")
    )

    assert outcomes_for_men.select(
        pl.col("crime").eq("184b").or_(pl.col("crime").eq("184c")).all()
    ).item()

    assert outcomes_for_men.select(
        pl.col("crime").eq("184b").sum().alias("child"),
        pl.col("crime").eq("184c").sum().alias("juvenile"),
    ).select(
        pl.col("child").eq(pl.col("juvenile")).all()
    ).item()

    # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
    # Validate that male and female detail rows ("F" and "M") add up to
    # total rows ("I"). Alas, the source data does not always observe that
    # rule. We patch total rows, since we don't know whether the row with
    # female or male detail is inacurate.

    outcome_totals = all_outcomes.filter(
        pl.col("sex").eq("*")
    ).select(
        pl.exclude("sex"),
    ).join(
        pl.DataFrame({
            Id.YEAR: [2024],
            "crime": ["184b"],
            "Δ_adjudicated": [-1],
            "Δ_adjudicated_as_adults": [-1],
        }),
        on=[Id.YEAR, "crime"],
        how="left",
    ).with_columns(
        pl.col("Δ_adjudicated", "Δ_adjudicated_as_adults").fill_null(0),
    ).with_columns(
        pl.col("adjudicated").add(
            pl.col("Δ_adjudicated")
        ),
        pl.col("adjudicated_as_adults").add(
            pl.col("Δ_adjudicated_as_adults")
        ),
    ).select(
        pl.exclude("Δ_adjudicated", "Δ_adjudicated_as_adults")
    )

    outcome_sums = all_outcomes.filter(
        pl.col("sex").ne("*")
    ).select(
        pl.exclude("sex"),
    ).group_by(
        pl.col(Id.YEAR, "crime"),
        maintain_order=True,
    ).agg(
        pl.selectors.integer().sum()
    )

    for column in OUTCOME_COLUMNS:
        c1 = outcome_sums.get_column(column)
        c2 = outcome_totals.get_column(column)
        if c1.ne(c2).any():
            raise AssertionError(f"values for column {column} diverge:\n{c1}\n{c2}")

    return all_outcomes


def combine_offenders_and_outcomes(
    offenders: pl.DataFrame,
    outcomes: pl.DataFrame,
) -> pl.DataFrame:
    if offenders.select(
        pl.col("metric").eq("German Youth Porn Offenders").any()
    ).item():
        raise ValueError(
            "unable to process German offenders with granular material attribute"
        )

    # Reduce offenders to one row per age_group and sex
    offenders = offenders.filter(
        pl.col("metric").eq("Germany CSAM Offenders")
    ).group_by(
        Id.YEAR, Id.GROUP, "sex"
    ).agg(
        pl.col("count").sum().round().cast(pl.Int64)
    )

    # Normalize outcome data, incl. reducing it to one row per age_group and sex
    adjudicated = _normalize_outcomes(outcomes, "Adjudication")
    convicted = _normalize_outcomes(outcomes, "Conviction")

    no_sanction = offenders.join(
        adjudicated.select(
            pl.exclude("outcome")
        ),
        on=[Id.YEAR, Id.GROUP, "sex"],
        how="left",
        nulls_equal=True,
    ).select(
        pl.col(Id.YEAR, Id.GROUP, "sex"),
        pl.lit("No Sanction", dtype=pl.Enum(OUTCOMES)).alias("outcome"),
        pl.col("count").sub(pl.col("count_right").fill_null(0)),
    )

    adjudicated = adjudicated.join(
        convicted.select(
            pl.exclude("outcome")
        ),
        on=[Id.YEAR, Id.GROUP, "sex"],
        how="left",
        nulls_equal=True,
    ).select(
        pl.col(Id.YEAR, Id.GROUP, "sex", "outcome"),
        pl.col("count").sub(pl.col("count_right").fill_null(0)),
    )

    result = pl.concat([no_sanction, adjudicated, convicted]).select(
        pl.lit("Germany", dtype=pl.Enum(COUNTRIES)).alias("country"),
        pl.lit("CSAM", dtype=pl.Enum(MATERIALS)).alias("material"),
        pl.lit("Offender", dtype=pl.Enum(ROLES)).alias("role"),
        pl.lit("Germany CSAM Offenders", dtype=pl.Enum(METRICS)).alias("metric"),
        pl.lit(METRIC_ORDER["Germany CSAM Offenders"], dtype=pl.Int8)
        .alias("metric_order"),
        pl.col(Id.YEAR, Id.GROUP),
        pl.col(Id.GROUP).replace_strict(
            AGE_GROUP_ORDER,
            return_dtype=pl.Int8,
        ).alias("age_group_order"),
        pl.col("sex"),
        pl.col("sex").replace_strict(
            SEX_ORDER,
            return_dtype=pl.Int8,
        ).alias("sex_order"),
        pl.col("outcome"),
        pl.col("outcome").replace_strict(
            OUTCOME_ORDER,
            return_dtype=pl.Int8,
        ).alias("outcome_order"),
        pl.col("count"),
    ).sort(
        Id.YEAR, "age_group_order", "sex_order", "outcome_order"
    )

    assert result.select(
        pl.col("count").ge(0).all()
    ).item()

    return result


def ingest_population_sizes() -> pl.DataFrame:
    parts = []
    for sex, skip_rows, n_rows in (
        ("*", 10, 18),
        ("Male", 39, 18),
        ("Female", 69, 18),
    ):
        parts.append(
            pl.read_excel(
                _ROOT / "data" / "germany" / "population-sizes-2025.xlsx",
                sheet_name="WBVab8_insg_männl_weibl_Bund",
                read_options=dict(
                    header_row=None,
                    skip_rows=skip_rows,
                    n_rows=n_rows,
                    use_columns=_USE_COLUMNS_POPULATION,
                    column_names=_COLUMN_NAMES_POPULATION,
                )
            ).with_columns(
                pl.lit(sex).alias("sex"),
            )
        )

    data = pl.concat(parts).sort(
        pl.col("report_year", "sex")
    ).filter(
        pl.col("census_year").is_in([
            "2009", "2010", "2011", "2012 vZ", "2023 Z22"
        ]).not_()
    ).with_columns(
        pl.col("report_year").replace({
            "2013 nZ": "2013",
            "2024 Z11": "2024",
        }),
        pl.col("census_year").replace({
            "2012 nZ": "2012",
            "2023 Z11": "2023",
        }),
    ).with_columns(
        pl.col("report_year", "census_year").cast(pl.Int64),
    ).with_columns(
        pl.col("total").eq(
            pl.sum_horizontal(
                pl.exclude("report_year", "census_year", "total", "sex")
            )
        ).alias("total_equals_sum")
    )

    # The breakdown for everyone and for women in 2019 does not compute!
    assert data.filter(
        pl.col("census_year").ne(2019).or_(
            pl.col("sex").eq("Male")
        ).all()
    ).select(
        pl.col("total_equals_sum").all()
    ).item()

    return data


def _normalize_outcomes(
    data: pl.DataFrame,
    outcome: Literal["Adjudication", "Conviction"],
) -> pl.DataFrame:
    prefix = "adjudicated" if outcome == "Adjudication" else "convicted"

    # The outcome data has two rows per data_year, age_group, and sex, one for
    # child and one juvenile pornography. We need to reduce the data to one row
    # before returning the result.
    return data.filter(
        pl.col("sex").ne("*")
    ).select(
        pl.col(Id.YEAR, "sex"),
        pl.lit(0, dtype=pl.Int64).alias("Child"),
        pl.col(f"{prefix}_juveniles").alias("Juvenile"),
        pl.col(f"{prefix}_adults").add(
            pl.col(f"{prefix}_as_adults")
        ).add(
            pl.col(f"{prefix}_as_juveniles")
        ).alias(f"Adult"),
    ).unpivot(
        on=["Child", "Juvenile", "Adult"],
        index=[Id.YEAR, "sex"],
        variable_name=Id.GROUP,
        value_name="count",
    ).group_by(
        Id.YEAR, Id.GROUP, "sex"
    ).agg(
        pl.col("count").sum()
    ).select(
        pl.col(Id.YEAR, Id.GROUP, "sex"),
        pl.lit(outcome, dtype=pl.Enum(OUTCOMES)).alias("outcome"),
        pl.col("count"),
    )


def age_crime_curves(age_distribution: pl.DataFrame) -> pl.DataFrame:
    frame = age_distribution.lazy().filter(
        pl.col("country").eq("Germany")
    ).group_by(
        pl.col(Id.YEAR, "age", "sex"),
        maintain_order=True,
    ).agg(
        pl.col("count").sum()
    ).filter(
        pl.col("age").ge(8)
    )

    pop = ingest_population_sizes().lazy().select(
        pl.exclude("census_year", "total", "total_equals_sum")
    ).filter(
        pl.col("sex").ne("*")
    ).unpivot(
        index=["report_year", "sex"],
        variable_name="age_range",
        value_name="capita",
    ).with_columns(
        pl.when(
            pl.col("age_range").eq(">=60")
        ).then(
            pl.lit(60)
        ).otherwise(
            pl.col("age_range").str.extract(r"(\d+)-")
        ).cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age_range").eq(">=60")
        ).then(
            pl.lit(100)
        ).otherwise(
            pl.col("age_range").str.extract(r"-(\d+)")
        ).cast(pl.Int8).alias("age_last"),
    ).with_columns(
        pl.col("capita").truediv(
            pl.col("age_last").sub(pl.col("age_first"))
        )
    ).select(
        pl.col("report_year").alias(Id.YEAR),
        pl.int_ranges("age_first", "age_last", dtype=pl.Int8).alias("age"),
        pl.col("sex", "capita"),
    ).explode("age")

    return frame.join(
        pop,
        on=[Id.YEAR, "age", "sex"],
        how="left",
    ).select(
        pl.col(Id.YEAR, "age", "sex"),
        pl.col("count").truediv(pl.col("capita")).mul(100_000).alias("rate"),
    ).sort(
        Id.YEAR, "age", "sex"
    ).collect()


if __name__ == "__main__":
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_rows(100)
    pl.Config.set_thousands_separator(",")

    WIDTH, _ = shutil.get_terminal_size()
    DASH = "━"

    def section(title: str) -> None:
        print(f"\n\n{DASH * 4}{title}{DASH * (WIDTH - 4 - len(title))}\n")

    section("Age Distributions")
    offenders = de_age_distribution().collect()
    print(offenders)

    section("With Outcomes")
    outcomes = ingest_outcomes()
    data = combine_offenders_and_outcomes(offenders, outcomes)
    print(data)

    section("Capita")
    population = ingest_population_sizes()
    print(population)

    section("Age Crime Curves")
    curve = age_crime_curves(offenders)
    print(curve)

    section("Age Distributions With Material")
    offenders_with_material = de_age_distribution(with_material=True).collect()
    print(offenders_with_material)

    assert offenders_with_material.select(
        pl.col(Id.MATERIAL).is_not_null().all()
    ).item()

    section("Age Distributions Restricted by Age and Material")
    restricted_offenders = restrict_offenders(offenders_with_material)
    print(restricted_offenders)
