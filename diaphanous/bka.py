from pathlib import Path

import polars as pl


_ROOT = Path(__file__).parent.parent

def ingest() -> pl.DataFrame:
    frames = []
    for year in range(2023, 2025):
        frames.append(pl.read_excel(
            _ROOT / "data" / "bka" / f"suspects-{year}.xlsx",
            sheet_name="BU-TV-01-T20-TV",
            read_options=dict(
                skip_rows=9,
                column_names=[
                    "id",
                    "description",
                    "sex",
                    "total",
                    "<6",
                    "6-8",
                    "8-10",
                    "10-12",
                    "12-14",
                    "child",
                    "14-16",
                    "16-18",
                    "adolescent",
                    "18-21",
                    "<21",
                    "21-23",
                    "23-25",
                    "21-25",
                    "25-30",
                    "30-40",
                    "40-50",
                    "50-60",
                    ">60",
                    ">21",
                ]
            ),
        ).filter(
            pl.col("id").str.starts_with("1432").or_(
                pl.col("id").str.starts_with("1435")
            )
        ).insert_column(
            0,
            pl.lit(year, dtype=pl.Int16).alias("data_year")
        ).with_columns(
            pl.col("18-21").add(pl.col(">21")).alias("adult")
        ))

    frame = pl.concat(frames)

    assert frame.select(
        pl.col("total").eq(
            pl.col("<21").add(pl.col(">21"))
        ).all()
    ).item()

    assert frame.select(
        pl.col("total").eq(
            pl.col("child").add(pl.col("adolescent")).add(pl.col("adult"))
        ).all()
    ).item()

    assert frame.select(
        pl.col("<21").eq(
            pl.col("child").add(pl.col("adolescent")).add(pl.col("18-21"))
        ).all()
    ).item()

    return frame


_CHILD_RANGES = ["<6", "6-8", "8-10", "10-12", "12-14"]
_ADOLESCENT_RANGES = ["14-16", "16-18"]
_ADULT_RANGES = ["18-21", "21-23", "23-25", "25-30", "30-40", "40-50", "50-60", ">60"]
_AGE_RANGES = [*_CHILD_RANGES, *_ADOLESCENT_RANGES, *_ADULT_RANGES]

def age_distribution(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.filter(
        pl.col("id").is_in(["143200", "143500"]).and_(pl.col("sex").eq("X"))
    ).unpivot(
        on=_AGE_RANGES,
        index="data_year",
        variable_name="age_range",
        value_name="count",
    ).group_by(
        pl.col("data_year", "age_range"),
    ).agg(
        pl.col("count").sum(),
    ).with_columns(
        pl.col("age_range").replace(
            {r: "Child" for r in _CHILD_RANGES} |
            {r: "Adolescent" for r in _ADOLESCENT_RANGES} |
            {r: "Adult" for r in _ADULT_RANGES}
        ).alias("age_group"),
        pl.when(
            pl.col("age_range").is_in(["<6", ">60"])
        ).then(
            pl.col("age_range").replace({
                "<6": 0,
                ">60": 60,
            })
        ).otherwise(
            pl.col("age_range").str.extract(r"(\d+)-")
        ).cast(pl.Int8).alias("age_first"),
        pl.when(
            pl.col("age_range").is_in(["<6", ">60"])
        ).then(
            pl.col("age_range").replace({
                "<6": 6,
                ">60": 100,
            })
        ).otherwise(
            pl.col("age_range").str.extract(r"-(\d+)")
        ).cast(pl.Int8).alias("age_last"),
    ).with_columns(
        pl.col("count").truediv(
            pl.col("age_last").sub(pl.col("age_first"))
        )
    ).select(
        pl.col("data_year", "count", "age_group"),
        pl.int_ranges("age_first", "age_last").alias("age"),
    ).explode("age").sort("age")


def demographics(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.filter(
        pl.col("id").is_in(["143200", "143500"]).and_(pl.col("sex").ne("X"))
    ).unpivot(
        on=["child", "adolescent", "adult"],
        index=["data_year", "sex"],
        variable_name="age_group",
        value_name="count",
    ).group_by(
        pl.col("data_year", "age_group", "sex")
    ).agg(
        pl.col("count").sum()
    ).select(
        pl.col("data_year").alias("Year"),
        pl.col("age_group").replace_strict({
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
    demographics(ingest()).write_csv(_ROOT / "data" / "bka" / "suspects.csv")
