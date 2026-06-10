from dataclasses import dataclass
from pathlib import Path
from typing import Self

import great_tables as gt
import polars as pl

from ._const import TOTAL
from .finish import finish_caseload, finish_severity
from .nibrs.model import Id, Column
from .util import finish_age_distribution, format_table

_LATEST_YEAR = 2024

_ROOT = Path(__file__).parent.parent

_DEFAULT_COLUMNS = ["id", "description", "sex", "total"]
_CHILD_RANGES = ["<6", "6-8", "8-10", "10-12", "12-14"]
_JUVENILE_RANGES = ["14-16", "16-18"]
_ADULT_RANGES = ["18-21", "21-23", "23-25", "25-30", "30-40", "40-50", "50-60", ">=60"]
_OLD_ADULT_RANGES = ["60-65", "65-70", "70-75", "75-80", ">=80"]
_AGE_RANGES = [*_CHILD_RANGES, *_JUVENILE_RANGES, *_ADULT_RANGES, *_OLD_ADULT_RANGES]

_PRODUCER_IDS_V1 = ["143200", "143400", "143500", "143700"]
_CONSUMER_IDS_V1 = ["143300", "143600"]
_PRODUCER_IDS_V2 = ["143210", "143220", "143510", "143520"]
_CONSUMER_IDS_V2 = ["143230", "143530"]

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


@dataclass(frozen=True)
class Data:

    incidents: pl.DataFrame
    suspects: pl.DataFrame

    @classmethod
    def ingest(cls) -> Self:
        suspects = []
        for year in range(2015, _LATEST_YEAR + 1):
            # https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/
            # PolizeilicheKriminalstatistik/2020/Bund/Tatverdaechtige/
            # BU-TV-01-T20-TV_xls.xlsx?__blob=publicationFile&v=4
            try:
                frame = pl.read_excel(
                    _ROOT / "data" / "bka" / f"suspects-{year}.xlsx",
                    sheet_name="T20",
                    read_options=_READ_OPTIONS_SUSPECTS,
                )
            except ValueError:
                frame = pl.read_excel(
                    _ROOT / "data" / "bka" / f"suspects-{year}.xlsx",
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
            else:
                filter = pl.col("id").str.starts_with("1432").or_(
                    pl.col("id").str.starts_with("1435")
                )
                producers = _PRODUCER_IDS_V2
                consumers = _CONSUMER_IDS_V2

            suspects.append(frame.filter(
                filter
            ).insert_column(
                0,
                pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
            ).with_columns(
                pl.col("18-21").add(pl.col(">=21")).alias("adult"),
                pl.when(
                    pl.col("id").is_in(producers)
                ).then(
                    pl.lit("Producer"),
                ).when(
                    pl.col("id").is_in(consumers)
                ).then(
                    pl.lit("Consumer"),
                ).alias("activity"),
            ))

        all_suspects = pl.concat(suspects)

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

        old_suspects = []
        for year in range(2019, _LATEST_YEAR + 1):
            if year == 2019:
                frame = pl.read_csv(
                    _ROOT / "data" / "bka" / "old-suspects-2019.csv",
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
                    _ROOT / "data" / "bka" / f"old-suspects-{year}.xlsx",
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
            else:
                filter = pl.col("id").str.starts_with("1432").or_(
                    pl.col("id").str.starts_with("1435")
                )
                producers = _PRODUCER_IDS_V2
                consumers = _CONSUMER_IDS_V2

            incidents.append(pl.read_excel(
                _ROOT / "data" / "bka" / f"incidents-{year}.xlsx",
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
                    pl.col("id").is_in(producers)
                ).then(
                    pl.lit("Producer"),
                ).when(
                    pl.col("id").is_in(consumers)
                ).then(
                    pl.lit("Consumer"),
                ).alias("activity"),
            ).select(
                pl.col(
                    Id.YEAR, "id", "description", "activity",
                    "incidents", "attempted", "solved",
                    "suspects", "male_suspects", "female_suspects",
                )
            ))

        all_incidents = pl.concat(incidents)

        # Validate that incidents and suspects agree on numbers of suspects
        assert all_suspects.filter(
            pl.col("activity").is_not_null().and_(pl.col("sex").eq("X"))
        ).select(
            pl.col(Id.YEAR, "id", "total")
        ).join(
            all_incidents.filter(
                pl.col("activity").is_not_null(),
            ).select(
                pl.col(Id.YEAR, "id", "suspects")
            ),
            on=[Id.YEAR, "id"],
            how="inner",
        ).select(
            pl.col("total").eq(pl.col("suspects")).all()
        ).item()

        return cls(all_incidents, all_suspects)

    def caseload(self) -> pl.DataFrame:
        frame = self.incidents.filter(
            pl.col("id").is_in(["143200", "143500"])
        ).group_by(
            pl.col(Id.YEAR)
        ).agg(
            pl.col("incidents", "suspects").sum(),
        ).unpivot(
            index=Id.YEAR,
            variable_name=Column.VARIANT,
            value_name=Column.COUNT,
        ).with_columns(
            pl.col(Column.VARIANT).replace({
                "incidents": "Incidents",
                "suspects": "Suspects",
            })
        ).pivot(
            on=Id.YEAR,
            index=Column.VARIANT,
            values=Column.COUNT,
            maintain_order=True,
        )

        return finish_caseload(frame)

    def caseload_table(self) -> gt.GT:
        return format_table(
            self.caseload(), "CSAM Caseload (Germany)"
        ).tab_spanner_delim(
            delim=" ", reverse=True
        )

    def severity(self) -> pl.DataFrame:
        frame = self.incidents.filter(
            pl.col("activity").is_not_null()
        ).rename({
            "activity": "Variant",
        }).group_by(
            Id.YEAR, "Variant"
        ).agg(
            pl.col("incidents").sum().alias("Count")
        )

        total = frame.group_by(
            Id.YEAR
        ).agg(
            pl.lit(TOTAL).alias("Variant"),
            pl.col("Count").sum()
        )

        return finish_severity(pl.concat([frame, total]).pivot(
            on=Id.YEAR,
            values="Count",
            maintain_order=True,
        ))

    def severity_table(self) -> gt.GT:
        return format_table(
            self.severity(), "Offense Severity (Germany)"
        ).tab_spanner_delim(
            delim=" ", reverse=True
        )

    def age_distribution(self) -> pl.LazyFrame:
        frame = self.suspects.lazy().filter(
            pl.col("activity").is_not_null().and_(pl.col("sex").ne("X"))
        ).with_columns(
            pl.col("sex").replace({"M": "Male", "W": "Female"}),
            pl.col(">=80").is_null().alias("requires_sixty_plus"),
        ).unpivot(
            on=_AGE_RANGES,
            index=[Id.YEAR, "sex", "activity", "requires_sixty_plus"],
            variable_name="age_range",
            value_name="count",
        ).filter(
            pl.col("requires_sixty_plus").or_(
                pl.col("age_range").ne(">=60")
            )
        ).group_by(
            pl.col(Id.YEAR, "age_range", "sex", "activity"),
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
            pl.col("activity", "count"),
        ).explode("age")

        # Between 2015 and 2025 (inclusive), the number of suspects per solved
        # incident ranges from 0.979 to 1.041. Likewise, the number of solved
        # incidents per suspect ranges from 0.960 to 1.022. In other words,
        # there is an almost one-to-one correspondence between incidents and
        # suspects. We assume that this relationship also holds for unresolved
        # incidents and extend the age distribution with these counts.
        unsolved = self.incidents.lazy().filter(
            pl.col("activity").is_not_null(),
        ).group_by(
            Id.YEAR, "activity",
        ).agg(
            pl.col("incidents", "solved").sum(),
        ).select(
            pl.col(Id.YEAR),
            pl.lit(None).cast(pl.Int8).alias("age"),
            pl.lit(None).cast(pl.String).alias("sex"),
            pl.lit(None).cast(pl.String).alias("ethnicity"),
            pl.col("activity"),
            pl.col("incidents").sub(pl.col("solved")).cast(pl.Float64).alias("count"),
        )

        return finish_age_distribution(
            pl.concat([frame, unsolved]),
            "Germany",
            "CSAM",
            "Offender",
            14,
            17
        )


def de_age_distribution() -> pl.LazyFrame:
    return Data.ingest().age_distribution()


if __name__ == "__main__":
    pl.Config.set_tbl_cols(10)
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    data = Data.ingest()
    incidents = data.incidents.filter(
        pl.col("activity").is_not_null(),
    ).group_by(
        Id.YEAR,
    ).agg(
        pl.col("incidents", "solved", "suspects").sum()
    ).with_columns(
        pl.col("suspects").truediv(pl.col("solved")).alias("suspects_per_incident"),
        pl.col("solved").truediv(pl.col("suspects")).alias("incidents_per_suspect"),
    )

    print(incidents)
    print(data.age_distribution().collect())
