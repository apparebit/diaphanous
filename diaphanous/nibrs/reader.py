from collections import defaultdict
from collections.abc import Mapping
import dataclasses
from pathlib import Path
import shutil
from typing import Callable, ClassVar, Literal
import zipfile

import polars as pl

from .model import (
    CriminalAct, Ethnicity, Id, OffenseCode, Race, Sex, SOURCE_FILES, Table
)
from ..util import (
    AGE_GROUP_ORDER, COUNTRIES, finish_age_distribution, MATERIALS, METRICS,
    METRIC_ORDER, OUTCOME_ORDER, OUTCOMES, ROLES
)


type FrameType = pl.DataFrame
_read_csv = pl.read_csv
_new_frame = pl.DataFrame


@dataclasses.dataclass
class Reader:
    """Ingest CSV files contained in a state-specific archive."""

    MATERIALIZED_TABLES: ClassVar[tuple[Table, ...]] = (
        Table.ARRESTEE,
        Table.INCIDENT,
        Table.OFFENDER,
        Table.VICTIM,
    )

    archive: Path
    tmp: Path
    year: int
    is_legacy_age: bool
    offense_type: None | FrameType

    def __init__(self, archive: Path) -> None:
        self.archive = archive
        self.tmp = tmp = self._unarchive(archive)
        self.year = year = int(self.tmp.parent.name)

        schema = Table.AGE.fit_schema(year, tmp)
        self.is_legacy_age = _read_csv(
            tmp / Table.AGE.csv_file,
            schema=pl.Schema(schema.value)
        ).filter(
            pl.col(Id.AGE).eq(4)
        ).get_column(
            Id.AGE_CODE
        ).item() == "00"

        if year <= 2020:
            schema = Table.OFFENSE_TYPE.fit_schema(year, tmp)
            self.offense_type = pl.read_csv(
                tmp / Table.OFFENSE_TYPE.csv_file,
                schema=pl.Schema(schema.value),
            ).select(
                pl.col(Id.OFFENSE_TYPE, Id.OFFENSE_CODE)
            )
        else:
            self.offense_type = None

    @classmethod
    def _unarchive(cls, archive: Path) -> Path:
        """
        Unarchive a state's CSV files into a subdirectory of the staging
        directory, returning said subdirectory.
        """
        staging = cls.make_staging()
        state = archive.name[:2]
        year = archive.name[3:7]
        csv_path = staging / year / state
        if csv_path.exists():
            shutil.rmtree(csv_path)
        csv_path.mkdir(parents=True)

        with zipfile.ZipFile(archive) as handle:
            for entry in handle.namelist():
                # Explicitly iterating over the contents and copying needed
                # files ensures that the materialized files all have the same
                # relative path (which is empty).
                if entry.endswith("/"):
                    continue

                _, _, name = entry.rpartition("/")
                name = name.lower()
                if name not in SOURCE_FILES:
                    continue

                with handle.open(entry, mode="r") as source:
                    with open(csv_path / name, mode="wb") as sink:
                        shutil.copyfileobj(source, sink)

        return csv_path

    @classmethod
    def make_staging(cls) -> Path:
        """Ensure the temporary directory exists."""
        path = Path.cwd() / ".nibrs.tmp"
        path.mkdir(exist_ok=True)
        return path

    def read_csv(self, table: Table) -> FrameType:
        """Read the CSV file for the given table."""
        schema = table.fit_schema(self.year, self.tmp)

        # For future reference: At least for CA, DC, and NY, the postgres_load.sql
        # script declares NIBRS_BIAS_LIST.csv to have the windows-1251 or cp1251
        # encoding.
        # For below: At least for CA, the agencies.csv file contains an invalid
        # UTF-8 sequence (\xa0 by itself on line 60), hence the lossy encoding.
        frame = _read_csv(
            self.tmp / table.csv_file,
            schema=pl.Schema(schema.value),
            encoding="utf8-lossy" if table is Table.AGENCIES else "utf8"
        )

        return schema.normalize(frame, self.offense_type, self.is_legacy_age)

    def read_all_csv(self) -> Mapping[Table, FrameType]:
        """Read the CSV files for all tables."""
        result = {}

        for table in Table:
            if table is Table.AGENCIES:
                result[table] = (
                    _new_frame({}, schema=table.latest_schema) if self.year <= 2015
                    else self.read_csv(table)
                )
            elif table is Table.OFFENSE_TYPE:
                pass
            else:
                result[table] = self.read_csv(table)

        return result

    def ingest_all(self) -> Mapping[Table, FrameType]:
        """Ingest arrestees, incidents, offenders, and victims."""
        frames = self.read_all_csv()

        agencies = frames[Table.AGENCIES]
        arrestees = frames[Table.ARRESTEE]
        criminal_acts = frames[Table.CRIMINAL_ACT]
        incidents = frames[Table.INCIDENT]
        offenders = frames[Table.OFFENDER]
        offenses = frames[Table.OFFENSE]
        # suspect_using = frames[Table.SUSPECT_USING]
        victims = frames[Table.VICTIM]

        # ------------------------------------------------------------------------------
        # Determine OFFENSES INVOLVING PORN and enrich with criminal acts
        porn_offenses = offenses.filter(
            pl.col(Id.OFFENSE_CODE).eq(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
        ).join(
            _prepare_criminal_acts(criminal_acts),
            on=(Id.YEAR, Id.OFFENSE),
            how="left",
        ).with_columns(
            pl.col(Id.MATERIAL).fill_null("Porn")
        )

        porn_offense_count = len(porn_offenses)
        offense_id_count = porn_offenses.select(
            pl.format("{} {}", pl.col(Id.YEAR), pl.col(Id.OFFENSE)).n_unique()
        ).item()
        incident_id_count = porn_offenses.select(
            pl.format("{} {}", pl.col(Id.YEAR), pl.col(Id.INCIDENT)).n_unique()
        ).item()

        # INVARIANT: Each offense involving porn should have a unique ID
        if porn_offense_count != offense_id_count:
            raise AssertionError(
                f"{porn_offense_count:,} porn offenses with {offense_id_count:,} IDs"
            )

        # INVARIANT: Each offense involving porn should reference a unique incident
        if porn_offense_count != incident_id_count:
            raise AssertionError(
                f"{porn_offense_count:,} porn offenses "
                f"with {incident_id_count:,} incidents"
            )

        # ------------------------------------------------------------------------------
        # Determine OFFENSES NOT INVOLVING PORN
        nonporn_offenses = offenses.filter(
            pl.col(Id.OFFENSE_CODE).ne(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
        ).group_by(
            Id.YEAR, Id.INCIDENT
        ).agg(
            pl.col(Id.OFFENSE_CODE).alias("other_offenses")
        )

        nonporn_offense_count = len(nonporn_offenses)
        incident_id_count = nonporn_offenses.select(
            pl.format("{} {}", pl.col(Id.YEAR), pl.col(Id.INCIDENT)).n_unique()
        ).item()

        # INVARIANT: Each list of offenses not involving porn has a unique incident
        if nonporn_offense_count != incident_id_count:
            raise AssertionError(
                f"{nonporn_offense_count:,} non-porn offenses "
                f"with {incident_id_count:,} incidents"
            )

        # ------------------------------------------------------------------------------
        # Extract AGENCY NAMES and eliminate duplicates
        agencies = agencies.select(
            "agency_id", "data_year", "ncic_agency_name", "state_abbr"
        ).group_by(
            "agency_id", "data_year"
        ).agg(
            pl.col("ncic_agency_name").first(),
            pl.col("state_abbr").first(),
        )

        agency_count = len(agencies)
        agency_id_count = agencies.select(
            pl.format("{} {}", pl.col(Id.YEAR), pl.col(Id.AGENCY)).n_unique()
        ).item()

        # INVARIANT: Each agency has a unique ID
        if agency_count != agency_id_count:
            raise AssertionError(
                f"{agency_count:,} agencies with {agency_id_count:,} IDs"
            )

        # ------------------------------------------------------------------------------
        # Determine INCIDENTS involving porn and enrich with offense data.
        incidents = incidents.join(
            porn_offenses,
            on=(Id.YEAR, Id.INCIDENT),
            how="inner",
        )
        incident_count = len(incidents)

        # Enrich incidents with offenses not involving porn
        incidents = incidents.join(
            nonporn_offenses,
            on=(Id.YEAR, Id.INCIDENT),
            how="left",
        )

        # INVARIANT: The number of incidents has not changed
        if incident_count != len(incidents):
            raise AssertionError(
                f"{len(incidents):,} not {incident_count:,} incidents "
                "after joining in non-porn offenses"
            )

        # Enrich incidents with agency names and states
        incidents = incidents.join(
            agencies,
            on=(Id.YEAR, Id.AGENCY),
            how="left",
        )

        # INVARIANT: The number of incidents has not changed
        if incident_count != len(incidents):
            raise AssertionError(
                f"{len(incidents):,} not {incident_count:,} incidents "
                "after joining agencies"
            )

        # ------------------------------------------------------------------------------
        # Determine ARRESTEES, OFFENDERS, and VICTIMS of interest
        def filter(frame: FrameType) -> FrameType:
            return frame.join(
                incidents,
                on=(Id.YEAR, Id.INCIDENT),
                how="inner",
            )

        arrestees = filter(arrestees)
        offenders = filter(offenders)
        victims = filter(victims)

        # INVARIANT: There are at most as many arrestees as offenders
        arrestee_count = len(arrestees)
        offender_count = len(offenders)

        if arrestee_count > offender_count:
            raise AssertionError(
                f"{arrestee_count:,} arrestees but {offender_count:,} offenders"
            )

        # ------------------------------------------------------------------------------
        # When changing this dictionary, also change MATERIALIZED_TABLES!
        return {
            Table.ARRESTEE: arrestees,
            Table.INCIDENT: incidents,
            Table.OFFENDER: offenders,
            Table.VICTIM: victims,
        }


def _prepare_criminal_acts[F: (pl.DataFrame, pl.LazyFrame)](frame: F) -> F:
    """
    Enrich criminal acts with columns for material and activity.

    After filtering offenses for pornography and joinings the filtered offenses
    with the result of this function, null values in the material column must be
    patched to be `Porn` entries.
    """
    return frame.filter(
        # Ignore unknown criminal acts
        pl.col(Id.CRIMINAL_ACT).ne(CriminalAct.UNKNOWN)
    ).group_by(
        Id.YEAR, Id.OFFENSE
    ).agg(
        Id.CRIMINAL_ACT
    ).with_columns(
        # Identify criminal acts involving the exploitation of children.
        pl.when(
            pl.col(Id.CRIMINAL_ACT).list.contains(CriminalAct.EXPLOITING_CHILDREN)
        ).then(
            pl.lit("CSAM")
        ).otherwise(
            pl.lit("Porn")
        ).cast(
            pl.Enum(MATERIALS)
        ).alias(Id.MATERIAL),

        # Distinguish criminal acts involving production from consumption.
        pl.when(
            pl.col(Id.CRIMINAL_ACT).list.eval(
                pl.element().is_in([
                    CriminalAct.CULTIVATING_MANUFACTURING_PUBLISHING,
                    CriminalAct.DISTRIBUTING_SELLING,
                    CriminalAct.OPERATING_PROMOTING_ASSISTING_ABETTING,
                    CriminalAct.TRANSPORTING_TRANSMITTING_IMPORTING,
                ])
            ).list.any()
        ).then(
            pl.lit("Producer")
        ).when(
            pl.col(Id.CRIMINAL_ACT).list.eval(
                pl.element().is_in([
                    CriminalAct.BUYING_RECEIVING,
                    CriminalAct.POSSESSING_CONCEALING,
                    CriminalAct.USING_CONSUMING,
                ])
            ).list.any()
        ).then(
            pl.lit("Consumer")
        ).otherwise(
            pl.lit(None)
        ).cast(
            pl.Enum(["Consumer", "Producer"])
        ).alias(Id.ACTIVITY)
    )


def step_ingestion(year: int, state: str) -> None:
    print("\x1b[G" f"Ingesting NIBRS data for {year} {state}...", end="", flush=True)


def done_ingestion() -> None:
    print()


_DATA_ROOT = Path(__file__).parent.parent.parent / "data" / "nibrs"
_TABLE_DIR = _DATA_ROOT / "tables"

def ingest_tables(
    step: None | Callable[[int, str], None] = None,
) -> Mapping[Table, FrameType]:
    """
    Build data frames with the un-accumulated case data for arrestees,
    incidents, offenders, and victims involving porn. The data frames are cached
    in parquet files.
    """
    if _TABLE_DIR.exists() and all(
        (_TABLE_DIR / tab.parquet_file).exists() for tab in Reader.MATERIALIZED_TABLES
    ):
        # Read tables
        tables = {
            tab: pl.read_parquet(
                _TABLE_DIR / tab.parquet_file
            ) for tab in Reader.MATERIALIZED_TABLES
        }
    else:
        # Actually ingest tables
        tables = _do_ingest_tables(step)

        # Write tables
        _TABLE_DIR.mkdir(exist_ok=True)
        for tab in Reader.MATERIALIZED_TABLES:
            tables[tab].write_parquet(_TABLE_DIR / tab.parquet_file)

    return tables


def _do_ingest_tables(
    step: None | Callable[[int, str], None] = None,
) -> Mapping[Table, FrameType]:
    """
    Build data frames with the un-accumulated case data for arrestees,
    incidents, offenders, and victims involving porn.
    """
    do_step = step or (lambda year, state: None)

    all_tables = defaultdict(list)
    for year in range(2015, 2025):
        path = _DATA_ROOT / f"{year}"
        for archive in sorted(path.glob("??-????.zip")):
            do_step(year, archive.name[:2])
            reader = Reader(archive)
            tables = reader.ingest_all()
            for tab, table in tables.items():
                all_tables[tab].append(table)

    return {tab: pl.concat(tables) for tab, tables in all_tables.items()}


def _normalize_name(name: str) -> str:
    parts = name.split()
    state = parts[-1]

    new_parts = []
    for part in parts[:-1]:
        has_comma = part.endswith(",")
        if has_comma:
            part = part[:-1]

        if not part in ("PD",):
            part = part.title()

        if has_comma:
            part = part + ","
        new_parts.append(part)

    new_parts.append(state)
    return " ".join(new_parts)


def analyze_offender_anomalies(
    step: None | Callable[[int, str], None] = None,
) -> pl.DataFrame:
    return ingest_tables(step)[Table.OFFENDER].filter(
        pl.col("material").eq("CSAM").and_(
            pl.col(Id.YEAR).ge(2021)
        ).and_(
            pl.col("age").eq(58)
        ).and_(
            pl.col("sex_code").is_in([Sex.UNKNOWN, Sex.NOT_SPECIFIED])
        )
    ).select(
        pl.format(
            "{}, {}", pl.col("ncic_agency_name"), pl.col("state_abbr")
        ).value_counts(sort=True)
    ).unnest("ncic_agency_name").with_columns(
        pl.col("ncic_agency_name").map_elements(
            _normalize_name,
            return_dtype=pl.String
        ),
        pl.col("count").truediv(pl.col("count").sum()).alias("fraction"),
    )


def ingest_age_distributions(
    step: None | Callable[[int, str], None] = None,
) -> pl.DataFrame:
    """Ingest the age distributions from the per year and state archives."""
    tables = ingest_tables(step)

    # Prepare age distributions for offenders and arrestees
    distribution = pl.concat([
        _prepare_age_distribution(tables[Table.OFFENDER], "Offender"),
        _prepare_age_distribution(tables[Table.ARRESTEE], "Arrestee"),
    ])

    # Update age distributions so that CSAM offenders and arrestees are proper
    # subsets of porn offenders and arrestees
    distribution = pl.concat([
        distribution.filter(
            pl.col(Id.MATERIAL).eq("CSAM")
        ),
        distribution.with_columns(
            pl.lit("Porn", dtype=pl.Enum(MATERIALS)).alias(Id.MATERIAL),
        ).group_by(
            Id.MATERIAL, Id.ROLE, Id.YEAR, "age", "sex", "ethnicity", Id.ACTIVITY,
        ).agg(
            pl.col("count").sum()
        ),
    ])

    print(len(distribution.filter(pl.col(Id.ROLE).is_null())), "out of", len(distribution))

    distribution = finish_age_distribution(
        distribution,
        country="United States",
        material=None,
        role=None,
        juvenile_min=11,
        juvenile_max=17,
    )

    if isinstance(distribution, pl.LazyFrame):
        distribution = distribution.collect()
    return distribution


def us_age_distributions(
    step: None | Callable[[int, str], None] = None,
    done: None | Callable[[], None] = None,
) -> pl.DataFrame:
    """
    Build a data frame with the age distributions for offenders and arrestees
    involved in either CSAM or porn offenses. This function stores the result.
    """
    cache = _DATA_ROOT / "age-distributions.parquet"
    if cache.exists():
        return pl.read_parquet(cache)

    distributions = ingest_age_distributions(step)
    distributions.write_parquet(cache)

    if done is not None:
        done()

    return distributions


def _prepare_age_distribution[F: (pl.DataFrame, pl.LazyFrame)](
    frame: F,
    role: Literal["Arrestee", "Offender"],
) -> F:
    # Simplify the frame
    frame = frame.with_columns(
        pl.col(Id.RACE).replace({
            Race.NOT_SPECIFIED: None,
            Race.UNKNOWN: None,
            Race.AMERICAN_INDIAN: Race.OTHER.value,
            Race.ASIAN: Race.OTHER.value,
            Race.HAWAIIAN: Race.OTHER.value,
            Race.MULTIPLE: Race.OTHER.value,
        }),
        pl.col(Id.SEX).replace({
            Sex.NOT_SPECIFIED: None,
            Sex.UNKNOWN: None,
        }),
    ).with_columns(
        pl.when(
            pl.col(Id.ETHNICITY).eq(Ethnicity.HISPANIC)
        ).then(
            pl.lit(Race.HISPANIC.value, dtype=pl.Int16)
        ).otherwise(
            pl.col(Id.RACE)
        ).alias(Id.RACE)
    )

    # Humanize column values and normalize column names
    frame = frame.with_columns(
        pl.col(Id.SEX).replace_strict(
            Id.SEX.humanized_values(),
            return_dtype=pl.String
        ),
        pl.col(Id.RACE).replace_strict(
            Id.RACE.humanized_values(),
            return_dtype=pl.String
        ),
    ).rename(
        {Id.SEX: "sex", Id.RACE.value: "ethnicity"}
    )

    # Add role
    frame = frame.with_columns(
        pl.lit(role, dtype=pl.Enum(ROLES)).alias(Id.ROLE)
    )

    # Tabulate counts
    return frame.group_by(
        Id.MATERIAL, Id.ROLE, Id.YEAR, "age", "sex", "ethnicity", Id.ACTIVITY,
    ).agg(
        pl.len().cast(pl.Float64).alias("count")
    )


def combine_offenders_and_arrestees(
    data: pl.DataFrame,
    material: Literal["CSAM", "Porn"] = "Porn",
) -> pl.DataFrame:
    def prep(frame: pl.DataFrame, metric: str) -> pl.DataFrame:
        return frame.filter(
            pl.col("metric").eq(metric)
        ).with_columns(
            pl.when(
                pl.col("age").lt(14)
            ).then(
                pl.lit("Child", dtype=pl.String)
            ).when(
                pl.col("age").le(17)
            ).then(
                pl.lit("Juvenile", dtype=pl.String)
            ).when(
                pl.col("age").gt(17)
            ).then(
                pl.lit("Adult", dtype=pl.String)
            ).alias("age_group"),
        ).with_columns(
            pl.col("age_group").replace_strict(
                AGE_GROUP_ORDER,
                return_dtype=pl.Int8,
            ).alias("age_group_order"),
        ).group_by(
            pl.col(
                "data_year",
                "age_group", "age_group_order",
                "sex", "sex_order"
            ),
        ).agg(
            pl.col("count").sum().round().cast(pl.Int64),
        )

    offender_metric = f"United States {material} Offenders"
    offenders = prep(data, offender_metric)
    arrestees = prep(data, f"United States {material} Arrestees")

    no_sanctions = offenders.join(
        arrestees,
        on=[
            "data_year",
            "age_group", "age_group_order",
            "sex", "sex_order",
        ],
        how="left",
        nulls_equal=True,
    ).with_columns(
        # If we don't fill the arrestee counts with 0, null values
        # effectively remove offender counts, resulting in data loss.
        pl.col("count_right").fill_null(0)
    ).with_columns(
        pl.lit("No Sanction", dtype=pl.Enum(OUTCOMES)).alias("outcome"),
        pl.lit(OUTCOME_ORDER["No Sanction"], dtype=pl.Int8).alias("outcome_order"),
        pl.col("count").sub(pl.col("count_right"))
    ).select(
        pl.exclude("count_right")
    )

    arrests = arrestees.with_columns(
        pl.lit("Arrest", dtype=pl.Enum(OUTCOMES)).alias("outcome"),
        pl.lit(OUTCOME_ORDER["Arrest"], dtype=pl.Int8).alias("outcome_order"),
    )

    result = pl.concat([no_sanctions, arrests]).select(
        pl.lit("United States", dtype=pl.Enum(COUNTRIES)).alias("country"),
        pl.lit(material, dtype=pl.Enum(MATERIALS)).alias("material"),
        pl.lit("Offender", dtype=pl.Enum(ROLES)).alias("role"),
        pl.lit(offender_metric, dtype=pl.Enum(METRICS)).alias("metric"),
        pl.lit(METRIC_ORDER[offender_metric], dtype=pl.Int8).alias("metric_order"),
        pl.col(
            "data_year",
            "age_group", "age_group_order",
            "sex", "sex_order",
            "outcome", "outcome_order",
            "count",
        ),
    ).sort(
        "data_year", "age_group_order", "sex_order", "outcome_order"
    )

    assert result.select(
        pl.col("count").ge(0).all()
    ).item()

    assert offenders.select(
        pl.col("data_year"),
        pl.col("count").sum().over("data_year").alias("old_totals"),
    ).join(
        result.select(
            pl.col("data_year"),
            pl.col("count").sum().over("data_year").alias("new_totals"),
        ),
        on="data_year",
        how="inner",
    ).select(
        pl.col("new_totals").eq(pl.col("old_totals")).all()
    ).item()

    return result
