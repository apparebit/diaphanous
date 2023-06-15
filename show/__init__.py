from collections.abc import Iterator, Sequence
from contextlib import contextmanager
import sys
from typing import cast, overload, TypeAlias

import pandas as pd

from .formatter import Formatter, HtmlFormatter, TerminalFormatter
from .markup import (
    Markup,
    BlockContent,
    only_block_content,
)


__all__ = ('Markup' 'show', 'SUPPORTS_HTML', 'use_color')


def _supports_html() -> bool:
    """Determine whether the current runtime environment displays HTML content."""
    if 'IPython' not in sys.modules or 'IPython.display' not in sys.modules:
        return False

    class Inspector:
        def __init__(self) -> None:
            self.status: None | str = None

        def _repr_html_(self) -> str:
            self.status = 'HTML'
            return '<p>Checking HTML support: ✅</p>'

        def __repr__(self) -> str:
            self.status = 'Plain'
            return 'Checking HTML support: ❌'

    from IPython.display import display

    inspector = Inspector()
    display(inspector)
    return inspector.status == 'HTML'


SUPPORTS_HTML = _supports_html()


# ======================================================================================


_current_formatter: Formatter
if SUPPORTS_HTML:
    _current_formatter = HtmlFormatter()
else:
    _current_formatter = TerminalFormatter(sys.stdout)


def use_color(colorful: bool) -> None:
    """Force colors or no colors in formatter output."""
    _current_formatter.use_color = colorful


@contextmanager
def formatter(formatter: None | Formatter) -> Iterator[Formatter]:
    """Show data with a user-controlled formatter."""
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
    None
    | str  # Implicit block content headings specified through keyword arguments
    | BlockContent
    | Sequence[BlockContent] # May be paragraph, several blocks, or ordered list
    | pd.Series  # Block content
    | pd.DataFrame  # Dataframes
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
def show(data: str | BlockContent | Sequence[BlockContent]) -> None:
    """
    Show the given data as (rich) text. This function converts the data to
    markup and then displays the markup.
    """

def show(
    data: _Showable,
    *,
    schema: bool = False,
    caption: None | str = None,
    highlight_columns: None | str | Sequence[str] = None,
    margin_bottom: float = 1.0,
) -> None:
    # Nothing to show:
    if data is None:
        return

    # Handle all block content:
    blocks: None | Sequence[BlockContent] = None
    if isinstance(data, str):
        blocks = Markup.parse(data)
    elif isinstance(data, Markup):
        blocks = [data]
    elif isinstance(data, Sequence):
        if only_block_content(data):
            blocks = data
        else:
            blocks = [cast(BlockContent,
                Markup.tx.ol(*(Markup.tx.li(str(el)) for el in data)))]

    if blocks:
        _current_formatter.display_all(blocks)
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
