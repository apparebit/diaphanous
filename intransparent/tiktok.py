from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal, Self

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
    status: Literal["all", "quarter", "shares"]
    data: pd.DataFrame

    @classmethod
    def for_period(cls, period: str | pd.Period, directory: None | Path = None) -> Self:
        year, quarter = parse_quarter(period)
        if directory is None:
            directory = Path(__file__).parent.parent / "data" / "tiktok"
        path = directory / f"tiktok-{year}-q{quarter}.csv"
        data = pd.read_csv(path)
        return cls(year, quarter, "all", data)

    def quarter_only(self) -> Self:
        assert self.status == "all"
        return type(self)(self.year, self.quarter, "quarter", self.data[
            (self.data["Period"] == f"{_QUARTER_LABELS[self.quarter-1]} {self.year}")
            & (self.data["Market"] == "All")
            & (self.data["Task"] == "All")
        ])

    def total_videos_removed(self) -> int:
        """
        Retrieve the count of total videos removed. This processor must be
        `focus()`ed before invoking this method.
        """
        assert self.status == "quarter"
        result = self.data.loc[self.data["Metric"] == "Total videos removed", "Result"]
        assert len(result) == 1
        return int(result.iat[0])

    def category_shares(self) -> Self:
        assert self.status == "quarter"
        return type(self)(self.year, self.quarter, "shares", self.data[
            (self.data["Metric"] == "Category share")
            & (self.data["Issue policy"].str.contains("Youth")
               | (self.data["Issue policy"] == "Safety & Civility"))
        ])

    def stats(self) -> pd.DataFrame:
        assert self.status == "quarter"
        total_count = self.total_videos_removed()

        shares = self.category_shares()
        category_share = (
            shares.data
            .loc[self.data["Issue policy"] == "Safety & Civility", "Result"]
            .iat[0]
        )
        subcategory_share = (
            shares.data
            .loc[self.data["Issue policy"] == "Youth Exploitation & Abuse", "Result"]
            .iat[0]
        )
        subcategory_count = int(total_count * category_share * subcategory_share)
        alt_subcategory_share = (
            shares.data
            .loc[self.data[
                "Issue policy"] == "Youth Safety & Well-Being - Youth Exploitation & Abuse",
                "Result"
            ]
            .iat[0]
        )

        return pd.DataFrame(
            [
                total_count,
                category_share,
                subcategory_share,
                subcategory_count,
                alt_subcategory_share,
                int(subcategory_count * alt_subcategory_share),
            ],
            columns=["Statistics"],
            index=[
                "Total videos removed",
                "Category share: Safety & civility",
                "Subcategory share: Youth exploitation & abuse",
                "Subcategory count: Youth exploitation & abuse",
                "Subcategory share: Youth safety & well-being - youth exploitation & abuse",
                "Speculative subcategory count: Previous two rows multiplied"
            ]
        )
