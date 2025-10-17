import dataclasses
from pathlib import Path
import shutil
from typing import Callable, Self, TYPE_CHECKING
import zipfile

import great_tables as gt
import polars as pl

from ..finish import finish_caseload, finish_severity
from .model import (
    Column, CriminalAct, Entry, Id, NIBRS_SOURCE_FILES,
    NibrsSchema, NibrsTable, OffenseCode
)
from ..util import format_table

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


def _ingest_csam_data(path: Path) -> list[pl.LazyFrame]:
    """
    Ingest all incidents involving CSAM from the given directory with NIBRS
    tables.
    """
    # For future reference: At least for CA, DC, and NY, the postgres_load.sql
    # script declares NIBRS_BIAS_LIST.csv to have the windows-1251 or cp1251
    # encoding.
    # For below: At least for CA, the agencies.csv file contains an invalid
    # UTF-8 sequence (\xa0 by itself on line 60), hence the lossy encoding.
    read = pl.scan_csv
    agencies = read(
        path / NibrsTable.AGENCIES.csv_file,
        schema=NibrsSchema.AGENCIES.value,
        encoding="utf8-lossy",
    )
    arrestee = read(
        path / NibrsTable.ARRESTEE.csv_file,
        schema=NibrsSchema.ARRESTEE.value,
    )
    criminal_act = read(
        path / NibrsTable.CRIMINAL_ACT.csv_file,
        schema=NibrsSchema.CRIMINAL_ACT.value,
    )
    incident = read(
        path / NibrsTable.INCIDENT.csv_file,
        schema=NibrsSchema.INCIDENT.value,
    )
    offender = read(
        path / NibrsTable.OFFENDER.csv_file,
        schema=NibrsSchema.OFFENDER.value,
    )
    offense = read(
        path / NibrsTable.OFFENSE.csv_file,
        schema=NibrsSchema.OFFENSE.value,
    )
    suspect_using = read(
        path / NibrsTable.SUSPECT_USING.csv_file,
        schema=NibrsSchema.SUSPECT_USING.value,
    )
    victim = read(
        path / NibrsTable.VICTIM.csv_file,
        schema=NibrsSchema.VICTIM.value,
    )
    victim_offense = read(
        path / NibrsTable.VICTIM_OFFENSE.csv_file,
        schema=NibrsSchema.VICTIM_OFFENSE.value,
    )

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
    offenses_exploiting_children = exploiting_children.join(
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
        ).with_columns(
            pl.col("other_criminal_act_ids").list.eval(
                pl.element().is_in([
                    CriminalAct.CULTIVATING_MANUFACTURING_PUBLISHING,
                    CriminalAct.DISTRIBUTING_SELLING,
                    CriminalAct.OPERATING_PROMOTING_ASSISTING_ABETTING,
                    CriminalAct.TRANSPORTING_TRANSMITTING_IMPORTING,
                ])
            ).list.any().alias("activity"),
        ),
        on=Id.OFFENSE,
        how="left",
    ).with_columns(
        pl.col("activity").fill_null(False)
    )

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
        offense,
        on=Id.INCIDENT,
        how="inner",
    ).filter(
        pl.col("offense_code").ne(OffenseCode.PORNOGRAPHY_OBSCENE_MATERIAL)
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
    def unarchive(cls, archive: Path, staging: Path) -> list[str]:
        """
        Unarchive needed source files into the staging directory from the
        NIBRS archive.
        """
        files = []
        with zipfile.ZipFile(archive) as handle:
            for entry in handle.namelist():
                if entry.endswith("/"):
                    continue

                _, _, name = entry.rpartition("/")
                if name not in NIBRS_SOURCE_FILES:
                    continue

                # Explicitly copying the file data ensures that the materialized
                # file is not nested in arbitrary directories.
                with handle.open(entry, mode="r") as source:
                    with open(staging / name, mode="wb") as sink:
                        shutil.copyfileobj(source, sink)

                files.append(name)

        return files

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
        staging = Path.cwd() / ".nibrs.tmp"
        staging.mkdir(exist_ok=True)
        data = []

        for archive_path in sorted(path.glob(f"??-????.zip")):
            progress(archive_path)

            state = archive_path.name[:2]
            year = archive_path.name[3:7]
            csv_path = staging / year / state
            if csv_path.exists():
                shutil.rmtree(csv_path)
            csv_path.mkdir(parents=True)

            cls.unarchive(archive_path, csv_path)
            data.append(cls.ingest_csv(csv_path))
            shutil.rmtree(csv_path)

        return cls.merge(*data)

    @classmethod
    def ingest_csv(cls, path: Path) -> Self:
        """Ingest CSAM data from directory with NIBRS CSV files."""
        data = cls(*pl.collect_all(_ingest_csam_data(path)))

        assert data.incidents.select(
            (pl.col(Id.OFFENSE).list.len() == 1).all()
        ).item(), (
            "each incident is associated with exactly one offense"
        )

        # Since the instance hasn't been visible outside of this method yet,
        # we can safely update the incidents.
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
            pl.col("activity").sum().alias("Production"),
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
            pl.col("attempted_complete_flag").value_counts(),
        ).explode(
            "attempted_complete_flag"
        ).unnest(
            "attempted_complete_flag"
        ).select(
            pl.col(Id.YEAR).cast(pl.String),
            pl.col("attempted_complete_flag").replace({
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


def load(year: int) -> CsamData:
    """Load NIBRS data involving CSAM for the given year."""
    def trace(path: Path) -> None:
        print(str(path))

    root = Path(__file__).parent.parent.parent
    archives = root / "data" / "nibrs" / f"{year}"
    ingested = root / "data" / "nibrs" / "ingested" / archives.name

    if not ingested.exists():
        data = CsamData.ingest_zip(archives, trace)
        data.save(ingested)
    else:
        data = CsamData.load(ingested)

    return data


def load_all() -> CsamData:
    """Load all NIBRS data involving CSAM."""
    return CsamData.merge(*(load(y) for y in range(2023, 2025)))
