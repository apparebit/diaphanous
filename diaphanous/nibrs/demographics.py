from typing import cast, Literal

import polars as pl

from .data import CsamData
from .model import Entry, Ethnicity, Group, Id, Race, Sex

# _BG_PALETTE = "Greens"
# _CHILD_ADOLESCENT_ADULT = (
#     "<strong>Child</strong>: 0–13 years old;&ensp;"
#     "<strong>Adolescent</strong>: 14–17 years old;&ensp;"
#     "<strong>Adult</strong>: 18 years or older"
# )


_AGE_ID_TO_AGE = (
    pl.when(pl.col(Id.AGE).le(3))
    .then(pl.lit(0))
    .otherwise(
        pl.when(pl.col(Id.AGE).le(102))
        .then(pl.col(Id.AGE) - 3)
        .otherwise(None)
    ).cast(
        pl.Int16
    ).alias("age")
)


_AGE_ID_TO_GROUP = (
    pl.when(pl.col(Id.AGE).lt(17))
    .then(pl.lit(Group.CHILD, dtype=pl.Int16))
    .otherwise(
        pl.when(pl.col(Id.AGE).lt(21))
        .then(pl.lit(Group.ADOLESCENT, dtype=pl.Int16))
        .otherwise(
            pl.when(pl.col(Id.AGE).le(102))
            .then(pl.lit(Group.ADULT, dtype=pl.Int16))
            .otherwise(pl.lit(None))
        )
    ).alias(
        Id.GROUP
    )
)


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
        # Replace age_id with age and age_group
        frame = cast(pl.DataFrame, getattr(csam_data, source)).with_columns(
            _AGE_ID_TO_AGE,
            _AGE_ID_TO_GROUP,
        ).drop(Id.AGE)

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

        self._csam_data = csam_data
        self._source = source
        self._frame = frame.select(
            pl.col(Id.YEAR, "age", Id.GROUP, Id.SEX, Id.RACE, Id.INCIDENT, Id.OFFENDER)
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
        Valid identifiers are `AGE`, `CLEARED_EXCEPT`, `ETHNICITY`, `GROUP`,
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
            elif criterion in (Id.LOCATION, Id.SUPPLY, Id.SUSPECT_USING):
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
        return self.by(
            Id.YEAR, Id.AGE, Id.GROUP, Id.SEX, Id.SUPPLY, sorted=True
        ).with_columns(
            pl.col(Id.GROUP).replace_strict({
                Group.CHILD: Entry.CHILD,
                Group.ADOLESCENT: Entry.ADOLESCENT,
                Group.ADULT: Entry.ADULT,
            }, return_dtype=pl.String),
            pl.col(Id.SEX).replace(
                Id.SEX.humanized_values(),
                return_dtype=pl.String
            ),
            pl.col(Id.SUPPLY).cast(pl.String).replace(
                Id.SUPPLY.humanized_values(),
                return_dtype=pl.String
            )
        ).rename({
            Id.SEX: "sex"
        })
