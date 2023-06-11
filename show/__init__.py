from collections.abc import Iterator, Sequence
from contextlib import contextmanager
import sys
from typing import overload, TypeAlias

import pandas as pd

from .formatter import Formatter, HtmlFormatter
from .markup import Markup, BlockContent, Heading, InlineContent, Paragraph


# A convenient alias
mx = Markup

__all__ = (
    'BlockContent',
    'Markup',
    'mx',
    'show'
)


class _DisplayInspector:
    def __init__(self) -> None:
        self.status: None | str = None

    def _repr_html_(self) -> str:
        self.status = 'HTML'
        return ''  #'<p>Checking HTML support: ✅</p>'

    def __repr__(self) -> str:
        self.status = 'Plain'
        return ''#'Checking HTML support: ❌'


def supports_html() -> bool:
    """Determine whether the current runtime environment displays HTML content."""
    if 'IPython' not in sys.modules or 'IPython.display' not in sys.modules:
        return False

    from IPython.display import display
    inspector = _DisplayInspector()
    display(inspector)
    return inspector.status == 'HTML'


# ======================================================================================


_current_formatter: Formatter = HtmlFormatter()


@contextmanager
def formatter(formatter: None | Formatter) -> Iterator[Formatter]:
    global _current_formatter
    saved_formatter = _current_formatter
    _current_formatter = _current_formatter if formatter is None else formatter
    try:
        yield _current_formatter
    finally:
        _current_formatter = saved_formatter


# --------------------------------------------------------------------------------------


# Data that can be shown:
_Showable: TypeAlias = (
    None | # Implicit block content headings specified through keyword arguments
    str | Sequence[str | InlineContent] | BlockContent | # Block content
    pd.Series | pd.DataFrame # Dataframes
)


@overload
def show(
    data: pd.Series | pd.DataFrame,
    *,
    schema: bool = False,
    caption: None | str = None,
    highlight_columns: None | str | Sequence[str] = None,
    margin_bottom: float = 1.0,
) -> None:
    """Show the given series or dataframe or its schema."""


@overload
def show(
    data: str | Sequence[str | InlineContent] | BlockContent,
    *,
    h1: None | str = None,
    h2: None | str = None,
) -> None:
    """Show the given block content, with strings or sequences of strings and
    inline content treated as paragraphs."""


@overload
def show(
    data: None = None,
    *,
    h1: None | str = None,
    h2: None | str = None,
) -> None:
    """Show the given headlines."""


def show(
    data: _Showable = None,
    *,
    h1: None | str = None,
    h2: None | str = None,
    schema: bool = False,
    caption: None | str = None,
    highlight_columns: None | str | Sequence[str] = None,
    margin_bottom: float = 1.0,
) -> None:
    # Nothing to show:
    if data is None and h1 is None and h2 is None:
        return

    # Handle all block content:
    blocks: list[BlockContent] = []
    data_is_block = False

    if h1 is not None:
        blocks.append(Heading(1, h1))
    if h2 is not None:
        blocks.append(Heading(2, h2))

    if isinstance(data, str):
        blocks.append(Paragraph((data,)))
        data_is_block = True
    elif isinstance(data, Sequence):
        blocks.append(Paragraph(tuple(data)))
        data_is_block = True
    elif isinstance(data, BlockContent):
        blocks.append(data)
        data_is_block = True

    if blocks:
        _current_formatter.display_all(blocks)
    if data is None or data_is_block:
        return

    # Normalize to dataframe:
    if isinstance(data, pd.Series):
        data = data.to_frame()
    assert isinstance(data, pd.DataFrame)

    # Handle dataframe schemas:
    if schema:
        format = _current_formatter.format_schema(
            frame=data,
            name=caption,
            margin_bottom=margin_bottom,
        )
        _current_formatter.display(format)
        return

    # Handle dataframe:
    format = _current_formatter.format_table(
        data,
        caption=caption,
        highlight_columns=highlight_columns,
        margin_bottom=margin_bottom,
    )

    columns = data.columns
    if 'reports' in columns and 'Δ%' in columns and 'NCMEC' in columns:
        format = _current_formatter.highlight_magnitude(
            data,
            format,
            column='Δ%',
            colormap='Reds',
            low=0.1,
            vmin=0,
            vmax=600,
            threshold=1,
        )

    _current_formatter.display(format)
