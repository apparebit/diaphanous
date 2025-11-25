import dataclasses
from pathlib import Path
import shutil
from typing import Callable, Literal, Self, TYPE_CHECKING
import zipfile

import great_tables as gt
import polars as pl

from ..finish import finish_caseload, finish_severity
from .model import (
    AGE_IN_YEARS_V1, AGE_IN_YEARS_V2, Column, CriminalAct, Entry, Ethnicity, Id,
    NIBRS_SOURCE_FILES, NibrsSchema, NibrsTable, OffenseCode, Race, Sex
)
from ..util import finish_age_distribution, format_table

if TYPE_CHECKING:
    from .demographics import Demographics


def _associated_offenses(
    incidents: pl.LazyFrame, offenses: pl.LazyFrame, label: str
) -> pl.LazyFrame:
    """Determine the offenses associated with incidents."""
    return incidents.select(
        pl.col(Id.INCIDENT)
    ).join(
        offenses.select(
            pl.col(Id.INCIDENT, Id.OFFENSE)
        ),
        on=Id.INCIDENT,
        how="inner",
    ).group_by(
        pl.col(Id.INCIDENT)
    ).agg(
        pl.col(Id.OFFENSE).alias(label)
    )


@dataclasses.dataclass
class _Reader:

    path: Path
    year: int
    is_legacy_age: bool
    offense_type: None | pl.LazyFrame

    def __init__(self, path: Path, year: int) -> None:
        self.path = path
        self.year = year

        self.is_legacy_age = pl.read_csv(
            path / NibrsTable.AGE.csv_file,
            schema=NibrsSchema.AGE.pick(year, path).value,
        ).filter(
            pl.col("age_id").eq(4)
        ).get_column(
            "age_code"
        ).item() == "00"

        if year <= 2020:
            effective_schema = NibrsSchema.OFFENSE_TYPE.pick(year, path)
            self.offense_type = pl.scan_csv(
                path / NibrsTable.OFFENSE_TYPE.csv_file,
                schema=effective_schema.value,
            ).select(
                pl.col("offense_type_id", "offense_code")
            )
        else:
            self.offense_type = None

    def read(self, schema: NibrsSchema) -> pl.LazyFrame:
        effective_schema = schema.pick(self.year, self.path)

        # For future reference: At least for CA, DC, and NY, the postgres_load.sql
        # script declares NIBRS_BIAS_LIST.csv to have the windows-1251 or cp1251
        # encoding.
        # For below: At least for CA, the agencies.csv file contains an invalid
        # UTF-8 sequence (\xa0 by itself on line 60), hence the lossy encoding.
        frame = pl.scan_csv(
            self.path / schema.csv_file(),
            schema=effective_schema.value,
            encoding="utf8-lossy" if schema is NibrsSchema.AGENCIES else "utf8"
        )

        if (to_drop := effective_schema.columns_to_drop()) is not None:
            frame = frame.drop(*to_drop)

        select_columns = False
        if effective_schema.requires_data_year():
            frame = frame.with_columns(
                pl.lit(self.year, dtype=pl.Int16).alias("data_year")
            )
            select_columns = True

        if effective_schema.requires_offense_code():
            assert self.offense_type is not None
            frame = frame.join(
                self.offense_type,
                on="offense_type_id",
                how="left",
            )
            select_columns = True

        if select_columns:
            frame = frame.select(
                schema.columns()
            )

        if schema.has_demographics():
            frame = frame.with_columns(
                AGE_IN_YEARS_V1 if self.is_legacy_age else AGE_IN_YEARS_V2
            )

            if self.year <= 2020:
                frame = frame.with_columns(
                    pl.col(Id.ETHNICITY).replace_strict(
                        Ethnicity.legacy_value_map(),
                        return_dtype=pl.Int16,
                    ),
                    pl.col(Id.RACE).replace_strict(
                        Race.legacy_value_map(),
                        return_dtype=pl.Int16,
                    ),
                    pl.col(Id.SEX).replace({"": Sex.NOT_SPECIFIED})
                )

        return frame


def _add_activity(frame: pl.LazyFrame, criminal_act_column: str) -> pl.LazyFrame:
    return frame.with_columns(
        pl.when(
            pl.col(criminal_act_column).list.eval(
                pl.element().is_in([
                    CriminalAct.CULTIVATING_MANUFACTURING_PUBLISHING,
                    CriminalAct.DISTRIBUTING_SELLING,
                    CriminalAct.OPERATING_PROMOTING_ASSISTING_ABETTING,
                    CriminalAct.TRANSPORTING_TRANSMITTING_IMPORTING,
                ])
            ).list.any()
        ).then(
            pl.lit("Producer", dtype=pl.String)
        ).when(
            pl.col(criminal_act_column).list.eval(
                pl.element().is_in([
                    CriminalAct.BUYING_RECEIVING,
                    CriminalAct.POSSESSING_CONCEALING,
                    CriminalAct.USING_CONSUMING,
                ])
            ).list.any()
        ).then(
            pl.lit("Consumer", dtype=pl.String)
        ).alias("activity")
    )


def _ingest_csam_data(path: Path, year: int) -> list[pl.LazyFrame]:
    """
    Ingest all incidents involving CSAM from the given directory with NIBRS
    tables.
    """
    reader = _Reader(path, year)

    if year == 2015:
        agencies = pl.LazyFrame({}, schema=NibrsSchema.AGENCIES.value)
    else:
        agencies = reader.read(NibrsSchema.AGENCIES)

    arrestee = reader.read(NibrsSchema.ARRESTEE)
    criminal_act = reader.read(NibrsSchema.CRIMINAL_ACT)
    incident = reader.read(NibrsSchema.INCIDENT)
    offender = reader.read(NibrsSchema.OFFENDER)
    offense = reader.read(NibrsSchema.OFFENSE)
    suspect_using = reader.read(NibrsSchema.SUSPECT_USING)
    victim = reader.read(NibrsSchema.VICTIM)
    victim_offense = reader.read(NibrsSchema.VICTIM_OFFENSE)

    # Drop year from auxiliary tables
    criminal_act = criminal_act.select(pl.col(Id.CRIMINAL_ACT, Id.OFFENSE))
    suspect_using = suspect_using.select(pl.col(Id.SUSPECT_USING, Id.OFFENSE))
    victim_offense = victim_offense.select(pl.col(Id.VICTIM, Id.OFFENSE))

    # Determine all offense IDs that are associated with the criminal act ID for
    # exploiting children ...
    exploiting_children = criminal_act.filter(
        pl.col(Id.CRIMINAL_ACT).eq(CriminalAct.EXPLOITING_CHILDREN)
    )

    # Combine with criminal act IDs other than exploiting children for the same
    # offense ID ...
    offenses_exploiting_children = _add_activity(exploiting_children.join(
        exploiting_children.select(
            pl.col(Id.OFFENSE)
        ).join(
            criminal_act.filter(
                pl.col(Id.CRIMINAL_ACT).ne(CriminalAct.EXPLOITING_CHILDREN)
            ),
            on=Id.OFFENSE,
            how="inner",
        ).group_by(
            pl.col(Id.OFFENSE)
        ).agg(
            pl.col(Id.CRIMINAL_ACT).alias("other_criminal_act_ids")
        ),
        on=Id.OFFENSE,
        how="left",
    ), "other_criminal_act_ids")

    # Combine with offenses that involve pornography or obscene materials to
    # arrive at table of offenses involving CSAM. Then enrich with using column.
    offenses_involving_csam = offense.filter(
        pl.col("offense_code").eq(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
    ).join(
        offenses_exploiting_children,
        on=Id.OFFENSE,
        how="inner",
    ).join(
        suspect_using.group_by(
            pl.col(Id.OFFENSE)
        ).agg(
            pl.col(Id.SUSPECT_USING).alias("using_ids")
        ),
        on=Id.OFFENSE,
        how="left",
    )

    # Derive incidents involving CSAM from offenses involving CSAM.
    incidents_involving_csam = offenses_involving_csam.select(
        pl.col(Id.INCIDENT).unique()
    ).join(
        incident,
        on=Id.INCIDENT,
        how="inner",
    )

    # Derive other offenses from all the offenses associated with incidents
    # involving CSAM, filtering out pornography.
    other_offenses = incidents_involving_csam.select(
        pl.col(Id.INCIDENT)
    ).join(
        offense.filter(
            pl.col("offense_code").ne(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
        ),
        on=Id.INCIDENT,
        how="inner",
    )

    # Derive offenders involving CSAM.
    offenders_involving_csam = incidents_involving_csam.select(
        pl.col(Id.INCIDENT)
    ).join(
        offender,
        on=Id.INCIDENT,
        how="inner",
    )

    # Likewise, derive arrestees involving CSAM.
    arrestees_involving_csam = incidents_involving_csam.select(
        pl.col(Id.INCIDENT)
    ).join(
        arrestee,
        on=Id.INCIDENT,
        how="inner"
    )

    # Derive victims involving CSAM by chaining incident to offense to victim ID.
    victims_involving_csam = incidents_involving_csam.select(
        pl.col(Id.INCIDENT)
    ).join(
        offenses_involving_csam.select(
            pl.col(Id.INCIDENT, Id.OFFENSE)
        ),
        on=Id.INCIDENT,
        how="inner",
    ).join(
        victim_offense,
        on=Id.OFFENSE,
        how="inner",
    ).join(
        victim,
        on=[Id.VICTIM, Id.INCIDENT],
        how="inner",
    )

    # Enrich incidents involving CSAM with columns listing associated arrestees,
    # offenders, offenses involving CSAM, offenses other than CSAM, and victims.
    incidents_involving_csam = incidents_involving_csam.join(
        offenders_involving_csam.select(
            pl.col(Id.INCIDENT, Id.OFFENDER)
        ).group_by(
            pl.col(Id.INCIDENT)
        ).agg(
            pl.col(Id.OFFENDER).alias("offenders")
        ),
        on=Id.INCIDENT,
        how="left",
    ).join(
        arrestees_involving_csam.select(
            pl.col(Id.INCIDENT, Id.ARRESTEE)
        ).group_by(
            pl.col(Id.INCIDENT)
        ).agg(
            pl.col(Id.ARRESTEE).alias("arrestees")
        ),
        on=Id.INCIDENT,
        how="left",
    ).join(
        _associated_offenses(
            incidents_involving_csam,
            offenses_involving_csam,
            Id.OFFENSE,
        ),
        on=Id.INCIDENT,
        how="left",
    ).join(
        _associated_offenses(
            incidents_involving_csam,
            other_offenses,
            "other_offenses",
        ),
        on=Id.INCIDENT,
        how="left",
    ).join(
        victims_involving_csam.select(
            pl.col(Id.INCIDENT, Id.VICTIM)
        ).group_by(
            pl.col(Id.INCIDENT)
        ).agg(
            pl.col(Id.VICTIM).alias("victims")
        ),
        on=Id.INCIDENT,
        how="left",
    )

    return [
        agencies,
        arrestees_involving_csam,
        incidents_involving_csam,
        offenders_involving_csam,
        offenses_involving_csam,
        other_offenses,
        victims_involving_csam,
    ]


def _ingest_porn_data(path: Path, year: int) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    reader = _Reader(path, year)

    arrestee = reader.read(NibrsSchema.ARRESTEE)
    criminal_act = reader.read(NibrsSchema.CRIMINAL_ACT)
    incident = reader.read(NibrsSchema.INCIDENT)
    offender = reader.read(NibrsSchema.OFFENDER)
    offense = reader.read(NibrsSchema.OFFENSE)

    criminal_act = _add_activity(criminal_act.group_by(
        Id.OFFENSE
    ).agg(
        Id.CRIMINAL_ACT
    ), Id.CRIMINAL_ACT).select(
        Id.OFFENSE, Id.ACTIVITY
    )

    offenses_involving_porn = offense.filter(
        pl.col("offense_code").eq(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
    ).join(
        criminal_act,
        on=Id.OFFENSE,
        how="left",
    )

    incidents_involving_porn = offenses_involving_porn.select(
        pl.col(Id.INCIDENT).unique()
    ).join(
        incident,
        on=Id.INCIDENT,
        how="inner",
    ).join(
        offenses_involving_porn.select(Id.INCIDENT, Id.ACTIVITY),
        on=Id.INCIDENT,
        how="left",
    )

    offenders_involving_porn = incidents_involving_porn.select(
        Id.INCIDENT, Id.ACTIVITY
    ).join(
        offender,
        on=Id.INCIDENT,
        how="inner",
    )

    arrestees_involving_porn = incidents_involving_porn.select(
        Id.INCIDENT, Id.ACTIVITY
    ).join(
        arrestee,
        on=Id.INCIDENT,
        how="inner"
    )

    return arrestees_involving_porn, offenders_involving_porn


def prepare(
    frame: pl.DataFrame,
    /,
    fold_ethnicity: bool = True,
    simplify_race: bool = True,
    nullify_unknown: bool = True,
) -> pl.DataFrame:
    # Map NOT_SPECIFIED and UNKNOWN to null
    if nullify_unknown:
        frame = frame.with_columns(
            pl.col(Id.ETHNICITY).replace({
                Ethnicity.NOT_SPECIFIED: None,
                Ethnicity.UNKNOWN: None,
            }),
            pl.col(Id.RACE).replace({
                Race.NOT_SPECIFIED: None,
                Race.UNKNOWN: None,
            }),
            pl.col(Id.SEX).replace({
                Sex.NOT_SPECIFIED: None,
                Sex.UNKNOWN: None,
            }),
        )

    if simplify_race:
        frame = frame.with_columns(
            pl.col(Id.RACE).replace({
                Race.AMERICAN_INDIAN: Race.OTHER.value,
                Race.ASIAN: Race.OTHER.value,
                Race.HAWAIIAN: Race.OTHER.value,
                Race.MULTIPLE: Race.OTHER.value,
            })
        )

    if fold_ethnicity:
        frame = frame.with_columns(
            pl.when(
                pl.col(Id.ETHNICITY).eq(Ethnicity.HISPANIC)
            ).then(
                pl.lit(Race.HISPANIC.value, dtype=pl.Int16)
            ).otherwise(
                pl.col(Id.RACE)
            ).alias(Id.RACE)
        )

    selection = [Id.YEAR, "age", Id.SEX, Id.RACE]

    if Id.ACTIVITY in frame.columns:
        selection.append(Id.ACTIVITY)
    selection.append(Id.INCIDENT)
    if Id.OFFENDER in frame.columns:
        selection.append(Id.OFFENDER)
    if Id.ARRESTEE in frame.columns:
        selection.append(Id.ARRESTEE)

    return frame.select(pl.col(*selection))


def finish(
    frame: pl.DataFrame,
    material: Literal["Porn", "CSAM"],
    role: Literal["Offender", "Arrestee"],
) -> pl.DataFrame:
    frame = frame.with_columns(
        pl.col("age").cast(pl.Int8),
        pl.col(Id.SEX).replace(
            Id.SEX.humanized_values(),
            return_dtype=pl.String
        ),
        pl.col(Id.RACE).replace_strict(
            Id.RACE.humanized_values(),
            return_dtype=pl.String
        ),
        pl.col("count").cast(pl.Float64),
    ).rename(
        {Id.SEX: "sex", Id.RACE.value: "ethnicity"}
    )

    return finish_age_distribution(frame, "United States", material, role, 11, 17)


@dataclasses.dataclass(frozen=True, slots=True)
class CsamData:
    """
    NIBRS records regarding CSAM.

    This datastructure collects incidents, offenders, offenses, other offenses,
    and victims involving CSAM from NIBRS. It extracts this information from
    NIBRS by first determining all offenses involving the exploitation of
    children, then narrowing that down to offenses also involving pornography,
    then determining associated incidents, then determining associated
    offenders, and finally determining associated victims.

    Note that the victims information is next to useless because NIBRS does not
    record any characteristics of the actual victims appearing in CSAM but
    rather treats "society" as the generic victim.
    """
    agencies: pl.DataFrame
    arrestees: pl.DataFrame
    incidents: pl.DataFrame
    offenders: pl.DataFrame
    offenses: pl.DataFrame
    other_offenses: pl.DataFrame
    victims: pl.DataFrame

    @classmethod
    def unarchive(cls, archive: Path) -> Path:
        """
        Unarchive needed source files into the staging directory from the
        NIBRS archive.
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
                if entry.endswith("/"):
                    continue

                _, _, name = entry.rpartition("/")
                name = name.lower()
                if name not in NIBRS_SOURCE_FILES:
                    continue

                # Explicitly copying the file data ensures that the materialized
                # file is not nested in arbitrary directories.
                with handle.open(entry, mode="r") as source:
                    with open(csv_path / name, mode="wb") as sink:
                        shutil.copyfileobj(source, sink)

        return csv_path

    @classmethod
    def make_staging(cls) -> Path:
        path = Path.cwd() / ".nibrs.tmp"
        path.mkdir(exist_ok=True)
        return path

    @classmethod
    def list_zip(cls, path: Path) -> list[Path]:
        return sorted(path.glob("??-????.zip"))

    @classmethod
    def ingest_zip(cls, path: Path, progress: Callable[[Path], None]) -> Self:
        """
        Ingest CSAM data from directory with NIBRS zip files.

        This method uses the ".nibrs.tmp" subdirectory of the current working
        directory as the root directory for temporary files. Before processing
        an archive, this method invokes the progress callback with the file's
        full path. During processing, it uses a subdirectory named after the
        year and US state for the archive. Upon successful ingestion, it deletes
        the nested subdirectory again, otherwise leaving it in place for
        inspection.
        """
        data = []

        for archive_path in cls.list_zip(path):
            progress(archive_path)

            csv_path = cls.unarchive(archive_path)
            data.append(cls.ingest_csv(csv_path, int(csv_path.parent.name)))
            shutil.rmtree(csv_path)

        return cls.merge(*data)

    @classmethod
    def ingest_csv(cls, path: Path, year: int) -> Self:
        """Ingest CSAM data from directory with NIBRS CSV files."""
        data = cls(*pl.collect_all(
            _ingest_csam_data(path, year)
        ))

        # Since the instance hasn't been visible outside of this method yet,
        # we can safely update the incidents.
        assert data.incidents.select(
            (pl.col(Id.OFFENSE).list.len() == 1).all()
        ).item(), (
            "each incident is associated with exactly one offense"
        )

        object.__setattr__(
            data,
            "incidents",
            data.incidents.explode(Id.OFFENSE)
        )

        return data

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load CSAM data from directory with Parquet files."""
        return cls(*(
            pl.read_parquet(path / f"{f.name}.parquet") for f in dataclasses.fields(cls)
        ))

    @classmethod
    def merge(cls, *data: Self) -> Self:
        """Merge the given CSAM data instances into one."""
        frame_rows = (dt.as_list() for dt in data)
        merged_frames = []
        for frame_column in zip(*frame_rows):
            frame = pl.concat(frame_column).rechunk()
            merged_frames.append(frame)
        return cls(*merged_frames)

    def caseload(self) -> pl.DataFrame:
        """
        Generate a data frame with the number of offenders, incidents, and
        arrestees.
        """
        frames = [
            getattr(self, label.lower()).lazy().group_by(
                pl.col(Id.YEAR), maintain_order=True,
            ).agg(
                pl.len().alias(Column.COUNT),
            ).select(
                pl.col(Id.YEAR).cast(pl.String),
                pl.lit(label, dtype=pl.String).alias(Column.VARIANT),
                pl.col(Column.COUNT),
            )
            for label in ("Incidents", "Offenders", "Arrestees")
        ]

        frame = pl.concat(
            frames,
            how="vertical"
        ).collect().pivot(
            on=Id.YEAR,
            index=Column.VARIANT,
            values=Column.COUNT,
            maintain_order=True,
        )

        return finish_caseload(frame)

    def caseload_table(self) -> gt.GT:
        """Generate a table from the `caseload` data frame."""
        return format_table(
            self.caseload(), "CSAM Caseload (US)"
        ).tab_spanner_delim(
            delim=" ", reverse=True
        )

    def severity(self) -> pl.DataFrame:
        """
        Generate a data frame with the number of offenses that are supply-side
        vs demand-side. The former include production, distribution, promotion,
        and transmission, whereas the latter include buying, possessing, and
        using.
        """
        frame = self.offenses.lazy().group_by(
            Id.YEAR, maintain_order=True
        ).agg(
            pl.col("activity").eq("Producer").sum().alias("Production"),
            pl.len().alias(Entry.TOTAL),
        ).select(
            pl.col(Id.YEAR).cast(pl.String),
            pl.col(Entry.TOTAL).sub(pl.col("Production")).alias("Consumption"),
            pl.col("Production"),
            pl.col(Entry.TOTAL),
        ).unpivot(
            index=Id.YEAR,
            variable_name=Column.VARIANT,
            value_name=Column.COUNT,
        ).collect().pivot(
            on=Id.YEAR,
            index=Column.VARIANT,
            values=Column.COUNT,
            maintain_order=True,
            separator=" ",
        )

        return finish_severity(frame)

    def severity_table(self) -> gt.GT:
        """Generate a table from the `severity` data frame."""
        return format_table(
            self.severity(), "Offense Severity (US)"
        ).tab_spanner_delim(
            delim=" ", reverse=True
        )

    def completion(self) -> pl.DataFrame:
        """
        Generate a data frame with the numbers of offenses that have been
        attempted, that have been completed, and that turned out to be
        unfounded.
        """
        return self.offenses.lazy().group_by(
            Id.YEAR, maintain_order=True,
        ).agg(
            pl.col("attempt_complete_flag").value_counts(),
        ).explode(
            "attempt_complete_flag"
        ).unnest(
            "attempt_complete_flag"
        ).select(
            pl.col(Id.YEAR).cast(pl.String),
            pl.col("attempt_complete_flag").replace({
                "A": "Attempted", "C": "Completed", "U": "Unfounded",
            }).alias(Column.VARIANT),
            pl.col("count").alias(Column.COUNT),
        ).collect().pivot(
            on=Id.YEAR,
            index=Column.VARIANT,
            values=Column.COUNT,
        )

    def completion_table(self) -> gt.GT:
        """Generate a table from the `completion` data frame."""
        return format_table(self.completion(), "Offense Completion")

    def arrestee_demographics(
        self,
        /,
        fold_ethnicity: bool = True,
        simplify_race: bool = True,
        nullify_unknown: bool = True,
    ) -> "Demographics":
        """Generate a demographic summary of arrestees."""
        from .demographics import Demographics
        return Demographics(
            self,
            "arrestees",
            fold_ethnicity=fold_ethnicity,
            simplify_race=simplify_race,
            nullify_unknown=nullify_unknown,
        )

    def offender_demographics(
        self,
        /,
        fold_ethnicity: bool = True,
        simplify_race: bool = True,
        nullify_unknown: bool = True,
    ) -> "Demographics":
        """Generate a demographic summary of offenders."""
        from .demographics import Demographics
        return Demographics(
            self,
            "offenders",
            fold_ethnicity=fold_ethnicity,
            simplify_race=simplify_race,
            nullify_unknown=nullify_unknown,
        )

    def as_list(self) -> list[pl.DataFrame]:
        """
        Return a list with this instance's data frames. Unlike
        `dataclasses.aslist`, this method does not copy the data frames.
        """
        return [
            self.agencies,
            self.arrestees,
            self.incidents,
            self.offenders,
            self.offenses,
            self.other_offenses,
            self.victims,
        ]

    def as_dict(self) -> dict[str, pl.DataFrame]:
        """
        Return a dict with this instance's data frames. Unlike
        `dataclasses.asdict`, this method does *not* copy the data frames.
        """
        return {
            "agencies": self.agencies,
            "arrestees": self.arrestees,
            "incidents": self.incidents,
            "offenders": self.offenders,
            "offenses": self.offenses,
            "other_offenses": self.other_offenses,
            "victims": self.victims,
        }

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for field in dataclasses.fields(self):
            getattr(self, field.name).write_parquet(path / f"{field.name}.parquet")


ROOT = Path(__file__).parent.parent.parent
ARCHIVES = ROOT / "data" / "nibrs"
INGESTED = ROOT / "data" / "nibrs" / "ingested"


def load(year: int) -> CsamData:
    """Load NIBRS data involving CSAM for the given year."""
    def trace(path: Path) -> None:
        print(str(path))

    archive = ARCHIVES / f"{year}"
    ingested = INGESTED / archive.name

    if not ingested.exists():
        data = CsamData.ingest_zip(archive, trace)
        data.save(ingested)
    else:
        data = CsamData.load(ingested)

    assert data.arrestees.select(
        pl.col(Id.ARRESTEE).n_unique()
    ).item() == data.arrestees.height, (
        "each arrestee appears exactly once"
    )

    assert data.offenders.select(
        pl.col(Id.OFFENDER).n_unique()
    ).item() == data.offenders.height, (
        "each offender appears exactly once"
    )

    assert data.victims.select(
        pl.col(Id.VICTIM).n_unique()
    ).item() == data.victims.height, (
        "each victim appears exactly once"
    )

    return data


def load_all_us_csam() -> CsamData:
    """Load all NIBRS data involving CSAM."""
    return CsamData.merge(*(load(y) for y in range(2015, 2025)))


def load_all_us_porn() -> tuple[pl.DataFrame, pl.DataFrame]:
    def trace(path: Path) -> None:
        print(str(path))

    ingested_arrestees = ARCHIVES / "porn-arrestees.parquet"
    ingested_offenders = ARCHIVES / "porn-offenders.parquet"

    if not ingested_arrestees.exists() or not ingested_offenders.exists():
        data = []
        for year in range(2015, 2025):
            for archive in CsamData.list_zip(ARCHIVES / f"{year}"):
                trace(archive)
                csv_path = CsamData.unarchive(archive)
                data.append(
                    pl.collect_all(
                        _ingest_porn_data(csv_path, int(csv_path.parent.name))
                    )
                )
                shutil.rmtree(csv_path)

        arrestees, offenders = [pl.concat(frames) for frames in zip(*data)]
        arrestees.write_parquet(ingested_arrestees)
        offenders.write_parquet(ingested_offenders)
    else:
        arrestees = pl.read_parquet(ingested_arrestees)
        offenders = pl.read_parquet(ingested_offenders)

    return arrestees, offenders


def compute_us_age_distribution(
    frame: pl.DataFrame,
    material: Literal["CSAM", "Porn"],
    role: Literal["Offender", "Arrestee"],
) -> pl.DataFrame:
    frame = prepare(frame).group_by(
        Id.YEAR, "age", Id.SEX, Id.RACE, Id.ACTIVITY,
    ).agg(
        pl.len().alias("count"),
    )
    return finish(frame, material, role)
