import polars as pl

from ._const import TOTAL


def finish_caseload(frame: pl.DataFrame) -> pl.DataFrame:
    first_year = frame.columns[1]
    return frame.select(
        pl.col("Variant"),
        pl.col(first_year).alias(f"Count {first_year}"),
        *(
            selection
            for i, c in enumerate(frame.columns[2:])
            for selection in (
                pl.col(c).sub(
                    pl.col(frame.columns[i + 2 - 1])
                ).truediv(
                    pl.col(frame.columns[i + 2 - 1])
                ).alias(f"∆% {c}"),
                pl.col(c).alias(f"Count {c}"),
            )
        )
    )


def finish_severity(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(
        pl.col("Variant"),
        *(
            selection
            for c in frame.columns[1:] #if c != Column.VARIANT
            for selection in (
                pl.col(c).alias(f"Count {c}"),
                pl.col(c).truediv(
                    pl.col(c).filter(pl.col("Variant").eq(TOTAL)).first()
                ).alias(f"Percent {c}"),
            )
        )
    )
