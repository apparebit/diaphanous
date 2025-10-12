from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

import great_tables as gt
import polars as pl

from ._const import TOTAL
from .finish import finish_caseload, finish_severity
from .nibrs.model import Id, Column, Entry
from .util import format_table


_ROOT = Path(__file__).parent.parent

_CHILD_RANGES = ["<6", "6-8", "8-10", "10-12", "12-14"]
_ADOLESCENT_RANGES = ["14-16", "16-18"]
_ADULT_RANGES = ["18-21", "21-23", "23-25", "25-30", "30-40", "40-50", "50-60", ">=60"]
_AGE_RANGES = [*_CHILD_RANGES, *_ADOLESCENT_RANGES, *_ADULT_RANGES]


@dataclass(frozen=True)
class Data:

    incidents: pl.DataFrame
    suspects: pl.DataFrame

    @classmethod
    def ingest(cls) -> Self:
        suspects = []
        for year in range(2023, 2025):
            suspects.append(pl.read_excel(
                _ROOT / "data" / "bka" / f"suspects-{year}.xlsx",
                sheet_name="BU-TV-01-T20-TV",
                read_options=dict(
                    skip_rows=9,
                    column_names=[
                        "id",
                        "description",
                        "sex",
                        "total",
                        *_CHILD_RANGES,
                        "child",
                        *_ADOLESCENT_RANGES,
                        "adolescent",
                        "18-21",
                        "<21",
                        "21-23",
                        "23-25",
                        "21-25",
                        *_ADULT_RANGES[3:],
                        ">=21",
                    ]
                ),
            ).filter(
                pl.col("id").str.starts_with("1432").or_(
                    pl.col("id").str.starts_with("1435")
                )
            ).insert_column(
                0,
                pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
            ).with_columns(
                pl.col("18-21").add(pl.col(">=21")).alias("adult"),
                pl.when(
                    pl.col("id").is_in(["143210", "143220", "143510", "143520"])
                ).then(
                    pl.lit("Producer"),
                ).otherwise(
                    pl.when(
                        pl.col("id").is_in(["143230", "143530"])
                    ).then(
                        pl.lit("Consumer"),
                    ).otherwise(
                        None
                    ),
                ).alias("supply"),
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

        incidents = []
        for year in range(2023, 2025):
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
                pl.col("id").str.starts_with("1432").or_(
                    pl.col("id").str.starts_with("1435")
                )
            ).insert_column(
                0,
                pl.lit(year, dtype=pl.Int16).alias(Id.YEAR)
            ).with_columns(
                pl.when(
                    pl.col("id").is_in(["143210", "143220", "143510", "143520"])
                ).then(
                    pl.lit("Production"),
                ).otherwise(
                    pl.when(
                        pl.col("id").is_in(["143230", "143530"])
                    ).then(
                        pl.lit("Consumption"),
                    ).otherwise(
                        None
                    ),
                ).alias("supply"),
            ).select(
                pl.col(
                    Id.YEAR, "id", "description", "supply",
                    "incidents", "attempted", "solved",
                    "suspects", "male_suspects", "female_suspects",
                )
            ))

        all_incidents = pl.concat(incidents)
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
            pl.col("supply").is_not_null()
        ).rename({
            "supply": "Variant",
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

    def age_distribution(self) -> pl.DataFrame:
        return self.suspects.filter(
            pl.col("supply").is_not_null().and_(pl.col("sex").ne("X"))
        ).with_columns(
            pl.col("sex").replace({"M": "Male", "W": "Female"}),
        ).unpivot(
            on=_AGE_RANGES,
            index=[Id.YEAR, "sex", "supply"],
            variable_name="age_range",
            value_name="count",
        ).group_by(
            pl.col(Id.YEAR, "age_range", "sex", "supply"),
        ).agg(
            pl.col("count").sum(),
        ).with_columns(
            pl.col("age_range").replace(
                {r: "Child" for r in _CHILD_RANGES} |
                {r: "Adolescent" for r in _ADOLESCENT_RANGES} |
                {r: "Adult" for r in _ADULT_RANGES}
            ).alias(Id.GROUP),
            pl.col("age_range").replace(
                {r: 1 for r in _CHILD_RANGES} |
                {r: 2 for r in _ADOLESCENT_RANGES} |
                {r: 3 for r in _ADULT_RANGES}
            ).alias("group_rank"),
            pl.col("sex", "supply"),
            pl.when(
                pl.col("age_range").is_in(["<6", ">=60"])
            ).then(
                pl.col("age_range").replace({
                    "<6": 0,
                    ">=60": 60,
                })
            ).otherwise(
                pl.col("age_range").str.extract(r"(\d+)-")
            ).cast(pl.Int8).alias("age_first"),
            pl.when(
                pl.col("age_range").is_in(["<6", ">=60"])
            ).then(
                pl.col("age_range").replace({
                    "<6": 6,
                    ">=60": 100,
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
            pl.int_ranges("age_first", "age_last").alias("age"),
            pl.col(Id.GROUP, "group_rank", "sex", "supply", "count")
        ).explode("age").sort(
            Id.YEAR, "age", "sex", "supply"
        )


if __name__ == "__main__":
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    data = Data.ingest()
    print(data.incidents)
    print(data.caseload())
    print(data.severity())
    print(data.age_distribution())

    # print(data.suspects)
    # data.demographics().write_csv(_ROOT / "data" / "bka" / "suspects.csv")
