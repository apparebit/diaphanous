import enum
import functools
from typing import Literal

import altair as alt
import great_tables as gt
import polars as pl

from .data import CsamData
from .model import (
    AGE_GROUPS, Column, Entry, Ethnicity, Id, Location, Race, Sex, Clearance,
    Using
)
from .util import format_table, to_title, with_total_and_percent


_RACE_SEX_LABELS = [
    "Black Female",
    "White Female",
    "Black Male",
    "White Male",
]


_AGE_ID_TO_AGE = (
    pl.when(pl.col(Id.AGE).le(3))
    .then(pl.lit(0))
    .otherwise(
        pl.when(pl.col(Id.AGE).le(102))
        .then(pl.col(Id.AGE) - 3)
        .otherwise(None)
    ).cast(
        pl.Int16
    ).alias(Column.AGE)
)

_AGE_ID_TO_GROUP = (
    pl.when(pl.col(Id.AGE).lt(17))
    .then(pl.lit(Entry.CHILD))
    .otherwise(
        pl.when(pl.col(Id.AGE).lt(21))
        .then(pl.lit(Entry.ADOLESCENT))
        .otherwise(
            pl.when(pl.col(Id.AGE).le(102))
            .then(pl.lit(Entry.ADULT))
            .otherwise(pl.lit(Entry.UNKNOWN))
        )
    ).cast(
        pl.String
    ).alias(
        Column.GROUP
    )
)


def _summarize_demographics(table: pl.DataFrame) -> pl.DataFrame:
    """Summarize the demographics of arrestees, offenders, and victims."""
    return table.lazy().group_by(
        pl.col(Id.AGE)
    ).agg(
        # For each offender age, break down demographics
        pl.len().cast(pl.Int64).alias(Entry.SIZE),
        *(
            pl.col(Id.ETHNICITY).eq(ethnicity).sum()
            .alias(f"Ethnicity: {to_title(ethnicity.name)}")
            for ethnicity in Ethnicity.__members__.values()
        ),
        *(
            pl.col(Id.RACE).eq(race).sum().alias(f"Race: {to_title(race.name)}")
            for race in Race.__members__.values()
        ),
        *(
            pl.col(Id.SEX).eq(sex).sum().alias(f"Sex: {to_title(sex.name)}")
            for sex in Sex.__members__.values()
        ),
        *(
            pl.col(Id.RACE).eq(race).and_(pl.col(Id.SEX).eq(sex)).sum()
            .alias(f"Race/Sex: {to_title(race.name)} {to_title(sex.name)}")
            for race in (Race.BLACK, Race.WHITE)
            for sex in Sex.__members__.values()
        ),
        *(
            pl.col(Id.RACE).is_in([Race.BLACK, Race.WHITE]).not_()
            .and_(pl.col(Id.SEX).eq(sex))
            .sum()
            .alias(f"Race/Sex: Other {to_title(sex.name)}")
            for sex in Sex.__members__.values()
        ),
    ).with_columns(
        # Turn age_id into age and age group
        _AGE_ID_TO_GROUP,
        _AGE_ID_TO_AGE,
    ).unpivot(
        # Turn into long frame with variant and count columns
        on=pl.exclude(Id.AGE, Column.AGE, Column.GROUP),
        index=[Id.AGE, Column.AGE, Column.GROUP],
        variable_name=Column.VARIANT,
        value_name=Column.COUNT,
    ).with_columns(
        # Extract category column from variant
        pl.when(pl.col(Column.VARIANT).eq(Entry.SIZE))
        .then(pl.lit("age_group"))
        .otherwise(
            pl.when(pl.col(Column.VARIANT).str.starts_with("Ethnicity: "))
            .then(pl.lit("ethnicity"))
            .otherwise(
                pl.when(pl.col(Column.VARIANT).str.starts_with("Race: "))
                .then(pl.lit("race"))
                .otherwise(
                    pl.when(pl.col(Column.VARIANT).str.starts_with("Sex: "))
                    .then(pl.lit("sex"))
                    .otherwise(pl.lit("race_sex"))
                )
            )
        ).alias(Column.CATEGORY),
    ).with_columns(
        # Drop now redundant prefix
        pl.col(Column.VARIANT).str.strip_prefix("Ethnicity: ")
        .str.strip_prefix("Race: ")
        .str.strip_prefix("Sex: ")
        .str.strip_prefix("Race/Sex: ")
    ).sort(
        Id.AGE, Column.CATEGORY, Column.VARIANT
    ).select(
        pl.col(
            Id.AGE, Column.AGE, Column.GROUP,
            Column.CATEGORY, Column.VARIANT,
            Column.COUNT,
        )
    ).collect()


_BG_PALETTE = "Greens"
_CHILD_ADOLESCENT_ADULT = (
    "Children are 0-13 years old, adolescents are 14-17 years old, and adults "
    "are 18 years or older."
)


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


class Demographics:
    """
    A wrapper for extracting demographic information from arrestees,
    offenders, and victims.
    """

    def __init__(
        self, csam_data: CsamData, source: Literal["arrestees", "offenders"]
    ) -> None:
        self._csam_data = csam_data
        self._source = source
        self._stats = _summarize_demographics(getattr(csam_data, source))

    def source(self) -> str:
        """Get the name of the source table."""
        return self._source.capitalize()[:-1]

    def age_group_sex_race(self) -> pl.DataFrame:
        """Get the 3-way frequency table for age group, sex, and race"""
        return getattr(self._csam_data, self._source).lazy().with_columns(
            _AGE_ID_TO_GROUP,
        ).group_by(
            Column.GROUP, Id.SEX, Id.RACE
        ).agg(
            pl.len().alias(Column.COUNT),
        ).with_columns(
            pl.col(Id.SEX).replace(
                {v.value: v.name for v in Sex.__members__.values()},
                return_dtype=pl.String,
                default="NOT_SPECIFIED",
            ),
            pl.col(Id.RACE).replace(
                {v.value: v.name for v in Race.__members__.values()},
                return_dtype=pl.String,
                default="NOT_SPECIFIED"
            ),
            pl.when(pl.col(Column.GROUP).eq("Child"))
            .then(pl.lit(1))
            .otherwise(
                pl.when(pl.col(Column.GROUP).eq("Adolescent"))
                .then(pl.lit(2))
                .otherwise(
                    pl.when(pl.col(Column.GROUP).eq("Adult"))
                    .then(pl.lit(3))
                    .otherwise(pl.lit(4))
                )
            ).alias(Column.RANK)
        ).sort(
            [Column.RANK, Id.SEX, Id.RACE]
        ).select(
            pl.col(Column.RANK),
            pl.col(Column.GROUP),
            pl.col(Id.SEX).alias("Sex"),
            pl.col(Id.RACE).alias("Race"),
            pl.col(Column.COUNT),
        ).collect()

    def age_groups(self) -> pl.DataFrame:
        """Get a data frame with the size of age groups."""
        return with_total_and_percent(self._stats.filter(
            pl.col(Column.CATEGORY).eq("age_group")
            .and_(pl.col(Column.VARIANT).eq(Entry.SIZE))
        ).group_by(
            pl.col(Column.GROUP), maintain_order=True,
        ).agg(
            pl.col(Column.COUNT).sum()
        ).select(
            pl.col(Column.GROUP).alias(Column.VARIANT),
            pl.col(Column.COUNT),
        ))

    def age_group_table(self) -> gt.GT:
        """Get a nicely formatted overview table comprising the age groups."""
        return format_table(self.age_groups(), f"{self.source()} Age Groups")

    def race_vs_sex(self) -> pl.DataFrame:
        """Get a data frame with demographical data about race and sex."""
        frame = self._stats.filter(
            pl.col(Column.CATEGORY).eq("race_sex")
            .and_(pl.col(Column.GROUP).ne(Entry.UNKNOWN))
        ).group_by(
            pl.col(Column.GROUP), maintain_order=True
        ).agg(
            *(
                pl.col(Column.COUNT)
                .filter(pl.col(Column.VARIANT).eq(label))
                .sum()
                .alias(label)
                for label in _RACE_SEX_LABELS
            ),

            pl.col(Column.COUNT)
            .filter(pl.col(Column.VARIANT).is_in(_RACE_SEX_LABELS).not_())
            .sum()
            .alias("Other"),

            pl.col(Column.COUNT).sum().alias(Entry.TOTAL),
        )

        totals = frame.get_column(Entry.TOTAL)

        return frame.select(
            pl.exclude(Column.GROUP)
        ).transpose(
            include_header=True,
            header_name=Column.VARIANT,
            column_names=["Child Count", "Adolescent Count", "Adult Count"]
        ).select(
            pl.col(Column.VARIANT),
            *(
                selection
                for index, group in enumerate(AGE_GROUPS)
                for selection in [
                    pl.col(f"{group} Count"),
                    (pl.col(f"{group} Count") / totals[index])
                    .alias(f"{group} Percent"),
                ]
            ),
        )

    def race_vs_sex_table(self) -> gt.GT:
        """
        Get a nicely formatted table with demographical data on race and
        sex.
        """
        frame = self.race_vs_sex()
        domain = [
            [0, mx] for mx in frame.filter(
                pl.col(Column.VARIANT).eq(Entry.TOTAL)
            ).select(
                pl.col("Child Count", "Adolescent Count", "Adult Count")
            ).row(0)
        ]

        return (
            format_table(
                frame,
                f"{self.source()} Race & Sex"
            )
            .data_color(
                columns=["Child Percent", "Adolescent Percent", "Adult Percent"],
                domain=[0, 1],
                palette=_BG_PALETTE,
            )
            .data_color(columns="Child Count", domain=domain[0], palette=_BG_PALETTE)
            .data_color(
                columns="Adolescent Count", domain=domain[1], palette=_BG_PALETTE,
            )
            .data_color(columns="Adult Count", domain=domain[2], palette=_BG_PALETTE)
            .tab_spanner_delim(" ")
            .tab_source_note(source_note=_CHILD_ADOLESCENT_ADULT)
            .tab_style(
                style=gt.style.text(color="#fff"),
                locations=gt.loc.body(
                    columns=["Adult Count", "Adult Percent"],
                    rows=["White Male"],
                ),
            )
        )

    def age_distribution(self, grouped: bool = True) -> tuple[str, pl.DataFrame]:
        """Get the age distribution of people, optionally with groups."""
        if grouped:
            variant = pl.col(Column.GROUP).alias(Column.VARIANT)
        else:
            variant = pl.lit(self.source()).alias(Column.VARIANT)

        return self.source(), self._stats.filter(
            pl.col(Column.GROUP).ne(Entry.UNKNOWN).and_(
                pl.col(Column.VARIANT).eq(Entry.SIZE)
            )
        ).select(
            pl.col(Column.AGE),
            variant,
            pl.col(Column.COUNT),
        )

    def variant_distribution(self, variant: str) -> tuple[str, pl.DataFrame]:
        """
        Get the age distribution for the given variant values. Valid values
        include `Black`, `White`, `Female`, and `Male`.
        """
        return variant, self._stats.filter(
            pl.col(Column.VARIANT).eq(variant)
        ).select(
            pl.col(Column.AGE, Column.VARIANT, Column.COUNT)
        )

    @functools.cache
    def _with_incidents(self) -> pl.DataFrame:
        """
        Return the data frame resulting from the original, individual arrestee,
        offender, or victim records being joined with their incidents.
        """
        return getattr(
            self._csam_data,
            self._source,
        ).filter(
            pl.col(Id.AGE).is_in([103, 104]).not_()
        ).join(
            self._csam_data.incidents.drop("data_year"),
            on=Id.INCIDENT,
            how="inner",
        )

    @functools.cache
    def _with_offenses(self) -> pl.DataFrame:
        """
        Return the data frame resulting from the original, individual arrestee,
        offender, or victim records being joined with their incidents and then
        offenses.
        """
        return self._with_incidents().join(
            self._csam_data.offenses.drop("data_year"),
            on=Id.OFFENSE,
            how="inner"
        )

    def clearance_distribution(
        self, label: str, *clearance: Clearance
    ) -> tuple[str, pl.DataFrame]:
        return label, self._with_incidents().select(
            _AGE_ID_TO_AGE,
            pl.col("cleared_except_id"),
        ).group_by(
            pl.col(Column.AGE)
        ).agg(
            pl.lit(label).alias(Column.VARIANT),
            pl.col("cleared_except_id").is_in(clearance)
            .sum()
            .cast(pl.Int64)
            .alias(Column.COUNT),
        ).sort(
            pl.col(Column.AGE),
        )

    def location_distribution(
        self, label: str, *location: Location
    ) -> tuple[str, pl.DataFrame]:
        return label, self._with_offenses().select(
            _AGE_ID_TO_AGE,
            pl.col(Id.LOCATION),
        ).group_by(
            pl.col(Column.AGE)
        ).agg(
            pl.lit(label).alias(Column.VARIANT),
            pl.col(Id.LOCATION).is_in(location)
            .sum()
            .cast(pl.Int64)
            .alias(Column.COUNT),
        ).sort(
            pl.col(Column.AGE)
        )

    def using_distribution(self, label: str, *using: Using) -> tuple[str, pl.DataFrame]:
        return label, self._with_offenses().select(
            _AGE_ID_TO_AGE,
            pl.col("using_ids")
        ).group_by(
            pl.col(Column.AGE)
        ).agg(
            pl.lit(label).alias(Column.VARIANT),
            pl.col("using_ids").list.eval(pl.element().is_in(using)).list.any()
            .sum()
            .cast(pl.Int64)
            .alias(Column.COUNT),
        ).sort(
            pl.col(Column.AGE)
        )

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
            title=f"{self.source()} Age Distribution"
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
