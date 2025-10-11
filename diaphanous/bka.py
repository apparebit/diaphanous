from dataclasses import dataclass
from pathlib import Path
from typing import Self

import great_tables as gt
import polars as pl

from .nibrs.finish import finish_caseload, finish_severity
from .nibrs.model import Id, Column, Entry
from .nibrs.util import format_table


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
            ).insert_column(
                2,
                pl.col("id").is_in([
                    "143211", "143212", "143214", "143220",
                    "143511", "143512", "143514", "143520",
                ]).alias("supply"),
            ).insert_column(
                3,
                pl.col("id").is_in([
                    "143213", "143230", "143513", "143530",
                ]).alias("demand")
            ).with_columns(
                pl.col("18-21").add(pl.col(">=21")).alias("adult")
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
            ).insert_column(
                2,
                pl.col("id").is_in([
                    "143211", "143212", "143214", "143220",
                    "143511", "143512", "143514", "143520",
                ]).alias("supply"),
            ).insert_column(
                3,
                pl.col("id").is_in([
                    "143213", "143230", "143513", "143530",
                ]).alias("demand")
            ).select(
                pl.col(
                    Id.YEAR, "id", "description", "supply", "demand",
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
        frame = self.incidents.lazy().group_by(Id.YEAR).agg(
            pl.col("incidents").filter(pl.col("supply")).sum().alias("Supply"),
            pl.col("incidents").filter(pl.col("demand")).sum().alias("Demand"),
        ).with_columns(
            pl.col("Supply").add(pl.col("Demand")).alias(Entry.TOTAL)
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
        return format_table(
            self.severity(), "Offense Severity (Germany)"
        ).tab_spanner_delim(
            delim=" ", reverse=True
        )

    def age_distribution(self) -> pl.DataFrame:
        return self.suspects.filter(
            pl.col("id").is_in(["143200", "143500"]).and_(pl.col("sex").ne("X"))
        ).unpivot(
            on=_AGE_RANGES,
            index=[Id.YEAR, "sex"],
            variable_name="age_range",
            value_name="count",
        ).group_by(
            pl.col(Id.YEAR, "age_range", "sex"),
        ).agg(
            pl.col("count").sum(),
        ).with_columns(
            pl.col("age_range").replace(
                {r: "Child" for r in _CHILD_RANGES} |
                {r: "Adolescent" for r in _ADOLESCENT_RANGES} |
                {r: "Adult" for r in _ADULT_RANGES}
            ).alias(Id.GROUP),
            pl.col("sex").replace({
                "W": "Female",
                "M": "Male",
            }),
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
            pl.col(Id.YEAR, "count", Id.GROUP, "sex"),
            pl.int_ranges("age_first", "age_last").alias("age"),
        ).explode("age").sort("age")

    def demographics(self) -> pl.DataFrame:
        return self.suspects.filter(
            pl.col("id").is_in(["143200", "143500"]).and_(pl.col("sex").ne("X"))
        ).unpivot(
            on=["child", "adolescent", "adult"],
            index=[Id.YEAR, "sex"],
            variable_name=Id.GROUP,
            value_name="count",
        ).group_by(
            pl.col(Id.YEAR, Id.GROUP, "sex")
        ).agg(
            pl.col("count").sum()
        ).select(
            pl.col(Id.YEAR).alias("Year"),
            pl.col(Id.GROUP).replace_strict({
                "child": 1,
                "adolescent": 2,
                "adult": 3,
            }).alias("Group"),
            pl.col("sex").replace({
                "M": "Male",
                "W": "Female",
            }).alias("Sex"),
            pl.col("count").alias("Count"),
        ).sort(
            "Year", "Group", "Sex"
        ).with_columns(
            pl.col("Group").replace_strict({
                1: "Child",
                2: "Adolescent",
                3: "Adult",
            })
        )


if __name__ == "__main__":
    pl.Config.set_tbl_rows(200)
    pl.Config.set_thousands_separator(",")

    data = Data.ingest()
    print(data.incidents)
    print(data.caseload())
    print(data.severity())
    # print(data.suspects)
    # data.demographics().write_csv(_ROOT / "data" / "bka" / "suspects.csv")
