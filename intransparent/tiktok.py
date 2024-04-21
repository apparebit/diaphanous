from dataclasses import dataclass
from pathlib import Path
import re
from typing import Self

import pandas as pd


_QUARTER_LABELS = ["Jan-Mar", "Apr-Jun", "Jul-Sep", "Oct-Dec"]
_PERIOD_PATTERN = re.compile(rf"^(?:{'|'.join(_QUARTER_LABELS)}) 202[34]$")
_ALT_PERIOD_PATTERN = re.compile(r"^202[34][qQ][1234]$")


def parse_quarter(period: str | pd.Period) -> tuple[int, int]:
    if isinstance(period, pd.Period):
        return period.year, period.quarter
    if _PERIOD_PATTERN.match(period):
        quarter = None
        for index, label in enumerate(_QUARTER_LABELS):
            if period.startswith(label):
                quarter = index + 1
                break
        assert quarter is not None
        return int(period[-4:]), quarter
    if not _ALT_PERIOD_PATTERN.match(period):
        raise ValueError(f"Not a valid period \"{period}\"")
    return int(period[:4]), int(period[-1:])


@dataclass(frozen=True, slots=True)
class Processor:

    year: int
    quarter: int
    data: pd.DataFrame

    @classmethod
    def for_quarter(cls, period: str | pd.Period, directory: None | Path = None) -> Self:
        year, quarter = parse_quarter(period)
        if directory is None:
            directory = Path(__file__).parent.parent / "data" / "tiktok"
        path = directory / f"tiktok-{year}-q{quarter}.csv"
        data = pd.read_csv_directory(path)
        return cls(year, quarter, data)

    def focus(self) -> Self:
        return type(self)(self.year, self.quarter, self.data[
            self.data["Period"] == f"{_QUARTER_LABELS[self.quarter-1]} {self.year}"
            & self.data["Market"] == "All"
            & self.data["Task"] == "All"
        ])

    def total_videos_removed(self) -> int:
        """
        Retrieve the count of total videos removed. This processor must be
        `focus()`ed before invoking this method.
        """
        result = self.data.loc[self.data["Metric"] == "Total videos removed", "Result"]
        assert len(result) == 1
        return int(result.iat[0])

    def category_share(self) -> pd.DataFrame:
        return self.data.loc[self.data["Metric"] == "Category share"]
