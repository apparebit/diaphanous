from typing import cast, Literal

import polars as pl

from .data import CsamData, finish, prepare
from .model import Id


class Demographics:
    """
    A wrapper for extracting demographic information from arrestees,
    offenders, and victims.
    """

    def __init__(
        self,
        csam_data: CsamData,
        source: Literal["arrestees", "offenders"],
        /,
        fold_ethnicity: bool = True,
        simplify_race: bool = True,
        nullify_unknown: bool = True,
    ) -> None:
        self._csam_data = csam_data
        self._source = source
        self._frame = prepare(
            cast(pl.DataFrame, getattr(csam_data, source)),
            fold_ethnicity=fold_ethnicity,
            simplify_race=simplify_race,
            nullify_unknown=nullify_unknown,
        )

    def name(self) -> str:
        """Get the name of the source table."""
        return self._source.capitalize()[:-1]

    def data(self) -> pl.DataFrame:
        """Get the raw data."""
        return self._frame

    def with_incidents(self, frame: None | pl.DataFrame = None) -> pl.DataFrame:
        """Get the source table joined with incidents."""
        return (self.data() if frame is None else frame).join(
            self._csam_data.incidents.drop(Id.YEAR),
            on=Id.INCIDENT,
            how="left",
        )

    def with_offenses(self, frame: None | pl.DataFrame = None) -> pl.DataFrame:
        """Get the source table joined with offenses."""
        frame = self.data() if frame is None else frame
        if Id.OFFENSE not in frame.columns:
            frame = frame.join(
                self._csam_data.incidents.select(Id.INCIDENT, Id.OFFENSE),
                on=Id.INCIDENT,
                how="left",
            )
        return frame.join(
            self._csam_data.offenses.drop(Id.YEAR),
            on=Id.OFFENSE,
            how="left",
        )

    def by(
        self,
        *criteria: Id,
        sorted: bool = False,
        only_year: None | int = None
    ) -> pl.DataFrame:
        """
        Tabulate this demographic by the combination of the given criteria.
        Valid identifiers are `AGE`, `CLEARED_EXCEPT`, `ETHNICITY`,
        `LOCATION`, `RACE`, `SEX`, `SUPPLY`, `SUSPECT_USING`, and `YEAR`. In
        fact, you probably want to always use `YEAR` as the first argument.
        """
        requires_incidents = False
        requires_offenses = False
        groups = []

        for criterion in criteria:
            if criterion in (
                Id.AGENCY, Id.ARRESTEE, Id.INCIDENT, Id.OFFENDER, Id.OFFENSE, Id.VICTIM
            ):
                raise ValueError(f"criterion {criterion} is unsupported")
            elif criterion == Id.CLEARED_EXCEPT:
                requires_incidents = True
            elif criterion in (Id.LOCATION, Id.ACTIVITY, Id.SUSPECT_USING):
                requires_offenses = True
            groups.append("age" if criterion is Id.AGE else criterion)

        frame = self.data() if only_year is None else self.data().filter(
            pl.col(Id.YEAR).eq(only_year)
        )
        if requires_incidents:
            frame = self.with_incidents(frame)
        if requires_offenses:
            frame = self.with_offenses(frame)

        frame = frame.group_by(
            *groups, maintain_order=not sorted
        ).agg(
            pl.len().alias("count"),
        )

        if sorted:
            frame = frame.sort(*groups)

        return frame

    def age_distribution(self) -> pl.DataFrame:
        frame = self.by(Id.YEAR, Id.AGE, Id.SEX, Id.RACE, Id.ACTIVITY)
        frame = finish(
            frame,
            "CSAM",
            "Offender" if self._source == "offenders" else "Arrestee",
        )
        return frame
