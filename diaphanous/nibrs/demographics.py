import enum
import functools
from typing import cast, Literal

import altair as alt
import polars as pl

from .data import CsamData
from .model import Column, Entry, Ethnicity, Group, Id, Race, Sex
from .util import humanize_frame


# _BG_PALETTE = "Greens"
# _CHILD_ADOLESCENT_ADULT = (
#     "<strong>Child</strong>: 0–13 years old;&ensp;"
#     "<strong>Adolescent</strong>: 14–17 years old;&ensp;"
#     "<strong>Adult</strong>: 18 years or older"
# )


class _Palette(enum.StrEnum):
    """
    Shantay's categorical color palette.

    This palette is based on and largely the same as [Observable's 2024 color
    palette](https://observablehq.com/blog/crafting-data-colors). This selection
    tends towards bright and saturated colors, which make charts "pop". That
    same quality can be a bit much at times, so manual curation still matters.
    """

    BLUE = "#4269d0"
    ORANGE = "#efb118"
    RED = "#ff725c"
    CYAN = "#6cc5b0"
    GREEN = "#3ca951"
    PINK = "#ff8ab7"
    PURPLE = "#a365ef"
    LIGHT_BLUE = "#97bbf5"
    BROWN = "#a57356"
    GRAY = "#9498a0"

    @classmethod
    def cycle(cls, index: int) -> str:
        """Cycle through the colors of the palette, ignoring gray."""
        return _COLORS[index % len(_COLORS)]

_COLORS = [c for c in _Palette.__members__.values() if c is not _Palette.GRAY]


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

_FOLD_HISPANIC_INTO_RACE = (
    pl.when(
        pl.col(Id.ETHNICITY).eq(Ethnicity.HISPANIC)
    ).then(
        pl.lit(Race.HISPANIC, dtype=pl.Int16)
    ).otherwise(
        pl.col(Id.RACE)
    ).alias(Id.RACE),
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

        self._source = source
        self._frame = frame.select(
            pl.col(Id.YEAR, "age", Id.GROUP, Id.SEX, Id.RACE)
        )

    @property
    def name(self) -> str:
        """Get the name of the source table."""
        return self._source.capitalize()[:-1]

    def data(self) -> pl.DataFrame:
        """Get the raw data."""
        return self._frame

    def humanized(self) -> pl.DataFrame:
        """
        Get the humanized data. This method drops unused columns, folds
        ethnicity into race, and coarsens the combined race/ethnicity column. It
        also replaces NIBRS coded values with meaningful labels.
        """
        return humanize_frame(self._frame)

    @functools.cache
    def with_incidents(self) -> pl.DataFrame:
        """Get the source table joined with incidents."""
        return self.data().join(
            self._csam_data.incidents.drop(Id.YEAR),
            on=Id.INCIDENT,
            how="left",
        )

    @functools.cache
    def with_offenses(self) -> pl.DataFrame:
        """Get the source table joined with offenses."""
        return self.data().join(
            self._csam_data.offenses.drop(Id.YEAR),
            on=Id.OFFENSE,
            how="left",
        )

    def by(self, *criteria: Id, sorted: bool = False) -> pl.DataFrame:
        """
        Tabulate this demographic by the combination of the given criteria.
        Valid identifiers are `AGE`, `CLEARED_EXCEPT`, `ETHNICITY`, `GROUP`,
        `LOCATION`, `RACE`, `SEX`, `SUSPECT_USING`, and `YEAR`. In fact, you
        probably want to always use `YEAR` as the first argument.
        """
        requires_incidents = False
        requires_offenses = False
        groups = []

        for criterion in criteria:
            if criterion == Id.AGE:
                groups.append("age")
            elif criterion == Id.GROUP:
                if Id.AGE not in criteria:
                    groups.append(Id.GROUP)
            elif criterion in (
                Id.AGENCY, Id.ARRESTEE, Id.INCIDENT, Id.OFFENDER, Id.OFFENSE, Id.VICTIM
            ):
                raise ValueError(f"criterion {criterion} is unsupported")
            elif criterion == Id.CLEARED_EXCEPT:
                requires_incidents = True
                groups.append(criterion)
            elif criterion in (Id.LOCATION, Id.SUSPECT_USING):
                requires_offenses = True
                groups.append(criterion)
            else:
                groups.append(criterion)

        if requires_incidents:
            assert not requires_offenses, (
                "CLEARED_EXCEPT and LOCATION/SUSPECT_USING are unsupported"
            )
            frame = self.with_incidents().lazy()
        elif requires_offenses:
            frame = self.with_offenses().lazy()
        else:
            frame = self.data().lazy()

        frame = frame.group_by(
            *groups, maintain_order=True
        ).agg(
            pl.struct(pl.col(*groups)).first().alias("criteria"),
            pl.len().alias("count"),
        ).select(
            pl.col("criteria").struct.unnest(),
            pl.col("count"),
        ).collect()

        if sorted:
            frame = frame.sort([c for c in criteria if c != Id.AGE])

        return frame

    # def race_vs_sex(self) -> pl.DataFrame:
    #     """Get a data frame with demographical data about race and sex."""
    #     frame = self._stats.filter(
    #         pl.col(Column.CATEGORY).eq("race_sex")
    #         .and_(pl.col(Column.GROUP).ne(Entry.UNKNOWN))
    #     ).group_by(
    #         pl.col(Id.YEAR, Column.GROUP), maintain_order=True
    #     ).agg(
    #         *(
    #             pl.col(Column.COUNT)
    #             .filter(pl.col(Column.VARIANT).eq(label))
    #             .sum()
    #             .alias(label)
    #             for label in _RACE_SEX_LABELS
    #         ),

    #         pl.col(Column.COUNT)
    #         .filter(pl.col(Column.VARIANT).is_in(_RACE_SEX_LABELS).not_())
    #         .sum()
    #         .alias("Other"),

    #         pl.col(Column.COUNT).sum().alias(Entry.TOTAL),
    #     )

    #     totals = frame.get_column(Entry.TOTAL)

    #     return frame.select(
    #         pl.exclude(Column.GROUP)
    #     ).transpose(
    #         include_header=True,
    #         header_name=Column.VARIANT,
    #         column_names=["Child Count", "Adolescent Count", "Adult Count"],
    #     ).select(
    #         pl.col(Id.YEAR, Column.VARIANT),
    #         *(
    #             selection
    #             for index, group in enumerate(AGE_GROUPS)
    #             for selection in [
    #                 pl.col(f"{group} Count"),
    #                 (pl.col(f"{group} Count") / totals[index])
    #                 .alias(f"{group} Percent"),
    #             ]
    #         ),

    #         pl.sum_horizontal(
    #             Count.CHILD, Count.ADOLESCENT, Count.ADULT
    #         ).alias(Count.TOTAL),
    #     ).with_columns(
    #         pl.col(Count.TOTAL).truediv(
    #             pl.col(Count.TOTAL).filter(
    #                 pl.col(Column.VARIANT).ne(Entry.TOTAL)
    #             ).sum()
    #         ).alias(Percent.TOTAL)
    #     )

    # def race_vs_sex_table(self) -> gt.GT:
    #     """
    #     Get a nicely formatted table with demographical data on race and
    #     sex.
    #     """
    #     frame = self.race_vs_sex()
    #     domain = [
    #         [0, mx] for mx in frame.filter(
    #             pl.col(Column.VARIANT).eq(Entry.TOTAL)
    #         ).select(
    #             pl.col(*Count.__members__.values())
    #         ).row(0)
    #     ]

    #     return (
    #         format_table(
    #             frame,
    #             f"{self.source} Race & Sex"
    #         )
    #         .data_color(
    #             columns=[*Percent.__members__.values()],
    #             domain=[0, 1],
    #             palette=_BG_PALETTE,
    #         )
    #         .data_color(columns=Count.CHILD, domain=domain[0], palette=_BG_PALETTE)
    #         .data_color(
    #             columns=Count.ADOLESCENT, domain=domain[1], palette=_BG_PALETTE,
    #         )
    #         .data_color(columns=Count.ADULT, domain=domain[2], palette=_BG_PALETTE)
    #         .data_color(columns=Count.TOTAL, domain=domain[3], palette=_BG_PALETTE)
    #         .tab_spanner_delim(" ")
    #         .tab_source_note(source_note=gt.html(_CHILD_ADOLESCENT_ADULT))
    #         .tab_style(
    #             style=gt.style.text(color="#fff"),
    #             locations=gt.loc.body(
    #                 columns=[Count.ADULT, Percent.ADULT],
    #                 rows=["White Male"],
    #             ),
    #         )
    #     )

    def chart_counts(
        self, overlay_label: None | str = None, overlay: None | pl.DataFrame = None
    ) -> alt.Chart:
        _, frame = self.age_distribution(grouped=True)
        if overlay is None:
            domain=[Entry.CHILD, Entry.ADOLESCENT, Entry.ADULT]
            range=[_Palette.ORANGE, _Palette.RED, _Palette.PURPLE]
        else:
            assert overlay_label is not None
            frame = pl.concat([frame, overlay])
            domain=[Entry.CHILD, Entry.ADOLESCENT, Entry.ADULT, overlay_label]
            range=[_Palette.ORANGE, _Palette.RED, _Palette.PURPLE, "#00000088"]

        return alt.Chart(
            frame,
            title=f"{self.source} Age Distribution"
        ).mark_bar().encode(
            alt.X("Age:Q").title("Age (Years)"),
            alt.Y("sum(Count):Q", stack=None).title("Offenders (Count)"),
            alt.Color(
                "Variant:N",
                legend=alt.Legend(title="Attribute", orient="top-right"),
            ).scale(
                domain=domain,
                range=range,
            ),
            #alt.Order("color_count_sort_index"),
        ).properties(
            width=600,
            height=300,
        )

    def chart_ratios(
        self, *distributions: tuple[str, pl.DataFrame], smooth: bool = False
    ) -> alt.Chart:
        """
        Create a line chart.
        """
        baseline = (lambda pair: pair[1])(self.age_distribution(grouped=False)).select(
            pl.col(Column.AGE),
            pl.col(Column.COUNT).alias("Total")
        )

        labels = []
        frames = []
        for label, frame in distributions:
            labels.append(label)

            frame = baseline.join(
                frame, on=Column.AGE, how="left"
            ).select(
                pl.col(Column.AGE, Column.VARIANT),
                pl.when(pl.col("Total") == 0)
                .then(pl.lit(0))
                .otherwise(pl.col(Column.COUNT) / pl.col("Total"))
                .alias("Fraction")
            )

            if smooth:
                frame = frame.with_columns(
                    pl.col("Fraction").rolling_mean(
                        window_size=3,
                    )
                )

            frames.append(
                frame.filter(
                    pl.col(Column.AGE).ge(5).and_(pl.col(Column.AGE).le(75))
                )
            )

        rule = alt.Chart().mark_rule(
            color=_Palette.GRAY
        ).encode(
            x=alt.X(datum=18)
        )

        return rule + alt.Chart(
            pl.concat(frames),
        ).mark_line().encode(
            alt.X("Age:Q").title("Age (Years)"),
            alt.Y("Fraction:Q").title(
                "Offenders with Attribute (Fraction)"
            ).scale(
                domain=(0, 1),
            ),
            alt.Color(
                "Variant:N",
                legend=alt.Legend(title="Attribute"),
            ).scale(
                domain=labels,
                range=[_Palette.cycle(i) for i in range(len(labels))],
            )
        ).properties(
            width=600,
            height=400,
        )
