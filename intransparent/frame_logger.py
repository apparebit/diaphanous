from collections.abc import Sequence
from typing import Protocol

import pandas as pd


class FrameLogger(Protocol):
    """
    A frame logger is a function that prints information about a dataframe,
    which is passed as its only positional argument. Optional named arguments
    provide a title and/or description.
    """

    def __call__(
        self,
        frame: pd.DataFrame,
        *,
        title: None | str = None,
        description: None | str = None,
    ) -> None:
        ...


def silent_logger(
    frame: pd.DataFrame,
    *,
    title: None | str = None,
    description: None | str = None,
    highlights: None | str | Sequence[str] = None,
) -> None:
    pass
