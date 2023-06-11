from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast, TypeAlias

import numpy as np
import pandas as pd


Dtype: TypeAlias = np.dtype | pd.api.extensions.ExtensionDtype


@dataclass(frozen=True, slots=True)
class Vertical(ABC):
    number: int
    name: None | str
    dtype: Dtype

    @property
    @abstractmethod
    def is_level(self) -> bool:
        ...

    @property
    def level(self) -> pd.Index:
        raise TypeError('Not an index level')

    @property
    def column(self) -> pd.Series:
        raise TypeError('Not a column')

    @property
    @abstractmethod
    def selector(self) -> str:
        ...


@dataclass(frozen=True, slots=True)
class IndexLevel(Vertical):
    data: pd.Index

    @property
    def is_level(self) -> bool:
        return True

    @property
    def level(self) -> pd.Index:
        return self.data

    @property
    def selector(self) -> str:
        return f'.level{self.number}'


@dataclass(frozen=True, slots=True)
class Column(Vertical):
    data: pd.Series

    @property
    def is_level(self) -> bool:
        return False

    @property
    def column(self) -> pd.Series:
        return self.data

    @property
    def selector(self) -> str:
        return f'.col{self.number}'


def verticals(frame: pd.DataFrame) -> Iterator[Vertical]:
    if frame.index.nlevels == 1:
        yield IndexLevel(
            0,
            frame.index.name,
            frame.index.dtype,
            frame.index,
        )
    else:
        multi_index = cast(pd.MultiIndex, frame.index)
        for level, dtype in enumerate(multi_index.dtypes):
            yield IndexLevel(
                level,
                multi_index.names[level],
                cast(Dtype, dtype),
                multi_index.levels[level],
            )
    for column_number, dtype in enumerate(frame.dtypes):
        column_name = frame.columns[column_number]
        yield Column(
            column_number,
            None if column_name is None else str(column_name),
            cast(Dtype, dtype),
            frame.iloc[:, column_number],
        )
