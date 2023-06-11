from typing import Protocol
import pandas as pd


class FrameLogger(Protocol):
    """
    A frame logger is a function that prints information about a given
    dataframed with an optional caption.
    """

    def __call__(self, frame: pd.DataFrame, *, caption: None | str = None) -> None:
        ...


def silent_logger(frame: pd.DataFrame, *, caption: None | str = None) -> None:
    pass
