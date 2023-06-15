from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import cast, TypeAlias

import numpy as np
import pandas as pd


Dtype: TypeAlias = np.dtype | pd.api.extensions.ExtensionDtype


@dataclass(frozen=True, slots=True)
class Vertical(ABC):
    """
    The base class for records representing verticals. This class only allows
    two concrete subtypes; it prevents other subtypes from being instantiated.
    Both subtypes implement the abstract `data` property declared by this class,
    albeit with different types, i.e., `pd.Index` vs `pd.Series`. For many use
    cases, accessing the vertical through the `data` property works well enough
    because Pandas indices and series share many operations. When the difference
    between the two types is meaningful, the `is_level`, `level`, and `column`
    properties help access the right instance in a typesafe manner.
    """
    index: int
    length: int
    name: None | str
    dtype: Dtype

    @classmethod
    def __init_subclass__(cls) -> None:
        full_name = f'{cls.__module__}.{cls.__qualname__}'
        if full_name not in ('show.vertical.IndexLevel', 'show.vertical.Column'):
            raise TypeError(f'{full_name} is not a valid vertical')

    @property
    @abstractmethod
    def data(self) -> pd.Index | pd.Series:
        ...

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
    def kind(self) -> str:
        ...

    @property
    @abstractmethod
    def selector(self) -> str:
        ...


@dataclass(frozen=True, slots=True)
class IndexLevel(Vertical):
    """An index level as vertical."""
    data: pd.Index

    @property
    def is_level(self) -> bool:
        return True

    @property
    def level(self) -> pd.Index:
        return self.data

    @property
    def kind(self) -> str:
        return 'level'

    @property
    def selector(self) -> str:
        return f'.level{self.index}'


@dataclass(frozen=True, slots=True)
class Column(Vertical):
    """A column as vertical."""
    data: pd.Series

    @property
    def is_level(self) -> bool:
        return False

    @property
    def column(self) -> pd.Series:
        return self.data

    @property
    def kind(self) -> str:
        return 'column'

    @property
    def selector(self) -> str:
        return f'.col{self.index}'


def all_verticals(frame: pd.DataFrame) -> Iterator[Vertical]:
    """
    Iterate over the data frame's verticals, that is, index levels and columns,
    returning an immutable object with critical metadata and the data.
    """
    yield from all_levels(frame)
    yield from all_columns(frame)


def all_levels(frame: pd.DataFrame) -> Iterator[IndexLevel]:
    """Iterate over the data frame's index levels."""
    nlevels = frame.index.nlevels
    if nlevels == 1:
        yield IndexLevel(
            0,
            1,
            frame.index.name,
            frame.index.dtype,
            frame.index,
        )
    else:
        multi_index = cast(pd.MultiIndex, frame.index)
        for level_index, dtype in enumerate(multi_index.dtypes):
            yield IndexLevel(
                level_index,
                nlevels,
                multi_index.names[level_index],
                cast(Dtype, dtype),
                multi_index.levels[level_index],
            )

def all_columns(frame: pd.DataFrame) -> Iterator[Column]:
    """Iterate over the data frame's columns."""
    ncolumns = frame.shape[0]
    for column_index, dtype in enumerate(frame.dtypes):
        column_name = frame.columns[column_index]
        yield Column(
            column_index,
            ncolumns,
            None if column_name is None else str(column_name),
            cast(Dtype, dtype),
            frame.iloc[:, column_index],
        )
