from abc import ABC, abstractmethod
from collections.abc import Sequence
import math
from typing import Any, Callable, cast, Generic, TypeVar

import pandas as pd
from pandas.api.types import is_numeric_dtype
from pandas.io.formats.style import Styler

from .markup import (
    BlockContent,
    HtmlRenderer,
    InlineContent,
    Markup,
    MarkupRenderer,
    Paragraph,
)

from .util import verticals

# def down_sample(color: tuple[int, int, int]) -> int:
#     r, g, b = color
#     r = r * 6 // 256
#     g = g * 6 // 256
#     b = b * 6 // 256
#     if r == g == b:
#         pass
#     return 16 + r * 36 + g * 6+ b
# CSI = re.compile(r'(?:\x9b|\x1b\[)[0-?]*[@-~]')


FormatT = TypeVar('FormatT')

class Formatter(ABC, Generic[FormatT]):
    """
    The base of formatters. A formatter knows how to convert a dataframe into a
    human-readable representation.
    """

    def __init__(
        self,
        *,
        not_available: str,
        significant_digits: int,
        decimal: str,
        thousands: str,
    ) -> None:
        self._not_available = not_available
        self._significant_digits = significant_digits
        self._decimal = decimal
        self._thousands = thousands


    # ----------------------------------------------------------------------------------
    # Configuration and Context-Dependent Utilities


    @property
    def not_available(self) -> str:
        """The representation of “not available” as well as “not a number”."""
        return self._not_available


    @property
    def significant_digits(self) -> int:
        """The minimum number of significant digits per column."""
        return self._significant_digits


    @property
    def decimal(self) -> str:
        """The decimal indicator."""
        return self._decimal


    @property
    def thousands(self) -> str:
        """The thousands separator."""
        return self._thousands


    @property
    @abstractmethod
    def markup_renderer(self) -> MarkupRenderer:
        """The renderer for markup objects."""


    # ----------------------------------------------------------------------------------
    # Formatting Data Frames and Their Schemas


    def format_schema(
        self,
        frame: pd.DataFrame,
        *,
        name: None | str = None,
        margin_bottom: float = 1.0,
    ) -> FormatT:
        """
        Format the schema for the given frame. This method (1) creates a summary
        for the frame, (2) determines the schema, (3) inserts a column with
        colons before the dtypes, (4) formats the table with the summary as
        caption but without any headers, and (5) styles the format.
        """

        summary = self.summarize_frame(frame, name=name)
        schema = self.to_schema(frame)
        schema.insert(2, 'colon', ':')
        format = self.format_table(
            schema,
            caption=summary,
            show_column_header=False,
            show_row_header=False,
            margin_bottom=margin_bottom,
        )
        return self.style_schema(schema, format)


    def to_schema(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Convert the dataframe into its schema, also represented as a dataframe."""

        schema = []
        for vertical in verticals(frame):
            schema.append([
                'index' if vertical.is_level else 'column',
                vertical.name,
                vertical.dtype,
                vertical.data.isna().sum()
            ])
        return pd.DataFrame(schema, columns=['kind', 'name', 'dtype', 'nulls'])


    @abstractmethod
    def style_schema(self, frame: pd.DataFrame, format: FormatT) -> FormatT:
        """Refine a schema's presentation, e.g., by adding styles."""


    def summarize_frame(
        self,
        frame: pd.DataFrame,
        *,
        name: None | str = None,
    ) -> Paragraph:
        """
        Generate a very short paragraph describing the frame. That paragraph, or
        summary, incorporates the frame's name (if available) and its number of
        rows. It is suitable as the table's caption, with the name highlighted.
        """

        fragments = cast(tuple[str | InlineContent], (
            'Table ',
            *(() if name is None else (Markup.strong(name), ' ')),
            f'with {frame.shape[0]} rows',
        ))
        return Paragraph(fragments)


    @abstractmethod
    def format_table(
        self,
        frame: pd.DataFrame,
        *,
        caption: None | str | Paragraph = None,
        highlight_columns: None | str | Sequence[str] = None,
        show_column_header: bool = True,
        show_row_header: bool = True,
        margin_bottom: float = 1.5,
    ) -> FormatT:
        """Format the given frame as a table."""


    @abstractmethod
    def highlight_magnitude(
        self,
        frame: pd.DataFrame,
        format: FormatT,
        column: str,
        threshold: float,
        colormap: str = 'plasma_r',
        low: float = 0,
        high: float = 0,
        vmin: None | float = None,
        vmax: None | float = None,
    ) -> FormatT:
        """
        Highlight rows for which the named column's absolute magnitude is above
        the given threshold using the given color map.
        """

    def precision_of(self, column: pd.Series) -> int:
        """
        Determine the column's precision. This method determines the number of
        digits needed after the decimal, so that even the smallest non-zero cell
        includes this format's number of significant digits. Note that the
        result may be zero if the column's values are large enough.
        """

        minval = column.abs().pipe(lambda c: c[c > 0].min())
        if pd.isna(minval):
            logmin = self.significant_digits - 1
        else:
            logmin = math.floor(math.log10(minval))

        # For 0 < minval < 1: -logmin == zeros past decimal + 1
        return max(0, self.significant_digits - logmin - 1)


    # ----------------------------------------------------------------------------------


    def render_markup(self, markup: Markup) -> str:
        """Render the given markup to a string."""
        return markup.render_with(self.markup_renderer)


    @abstractmethod
    def render_format(self, format: FormatT) -> str:
        """Render the given format to a string."""


    def render(self, block: BlockContent | FormatT) -> str:
        """Render the given block content or format."""
        if isinstance(block, BlockContent):
            return self.render_markup(block)
        else:
            return self.render_format(block)


    def render_all(self, blocks: Sequence[BlockContent | FormatT]) -> str:
        """Render all the given blocks to a string."""
        return ''.join(self.render(block) for block in blocks)


    @abstractmethod
    def display(self, block: BlockContent | FormatT) -> None:
        """Render the given block to screen."""


    @abstractmethod
    def display_all(self, blocks: Sequence[BlockContent | FormatT]) -> None:
        """Render the given blocks to the screen."""


# ======================================================================================


class HtmlFormatter(Formatter[Styler]):

    def __init__(
        self,
        *,
        not_available: str = '⋯',
        significant_digits: int = 3,
        decimal: str = '.',
        thousands: str = ',',
    ) -> None:
        super().__init__(
            not_available=not_available,
            significant_digits=significant_digits,
            decimal=decimal,
            thousands=thousands,
        )
        self._display: None | Callable[[object], None] = None
        self._html: None | Callable[[str], object] = None
        self._markup_renderer = HtmlRenderer()


    @property
    def markup_renderer(self) -> MarkupRenderer:
        return self._markup_renderer


    def style_schema(self, frame: pd.DataFrame, format: Styler) -> Styler:
        def format_nulls(nulls: object) -> str:
            if not isinstance(nulls, int):
                raise ValueError(f'{nulls} is not an integer')
            quantity = 'no' if nulls == 0 else f'{nulls}'
            return f'({quantity} null{"" if nulls == 1 else "s"})'

        format.format({'nulls': format_nulls})
        format.set_table_styles([
            {
                'selector': 'td',
                'props': [('padding', '0.1em 1ex 0.1em 0')]
            },
            {
                'selector': 'td:nth-child(5)',
                'props': [('padding-left', '0.4em'), ('text-align', 'start')]
            }
        ], overwrite=False)
        return format


    def format_table(
        self,
        frame: pd.DataFrame,
        *,
        caption: None | str | Paragraph = None,
        highlight_columns: None | str | Sequence[str] = None,
        show_column_header: bool = True,
        show_row_header: bool = True,
        margin_bottom: float = 1.5,
    ) -> Styler:
        styler = frame.style
        table_styles = []

        # The caption
        if caption is not None:
            is_paragraph = isinstance(caption, Paragraph)

            # Set caption markup
            if is_paragraph:
                caption = (
                    self.markup_renderer
                    .reduce(caption.fragments) # type: ignore[union-attr]
                )
            assert isinstance(caption, str)
            styler.set_caption(caption)

            # Set caption style
            props = [
                    ('caption-side', 'top'),
                    ('font-size', '1.1em'),
                    ('margin-bottom', '2ex'),
            ]
            if not is_paragraph:
                props.append(('font-style', 'italic'))
            table_styles.append({'selector': 'caption', 'props': props})

        # Row header
        if not show_row_header:
            styler.hide(subset=None, level=None, names=False, axis=0)

        # Column header
        if not show_column_header:
            styler.hide(subset=None, level=None, names=False, axis=1)
        else:
            styler.relabel_index(
                [column.replace('_', ' ') for column in frame.columns], axis=1)

        # Column alignment
        align_start = ','.join(
            v.selector for v in verticals(frame) if not is_numeric_dtype(v.dtype)
        )
        if len(align_start) > 0:
            table_styles.append({
                'selector': align_start,
                'props': [('text-align', 'start')],
            })

        # The data
        styler.format(
            decimal=self.decimal,
            thousands=self.thousands,
            na_rep=self.not_available
        )
        table_styles.append({
            'selector': '',
            'props': [
                ('font-variant-numeric', 'tabular-nums'),
                ('margin-bottom', '0' if margin_bottom == 0 else f'{margin_bottom}em')
            ],
        })

        # Actually apply table styles
        if table_styles:
            styler.set_table_styles(table_styles) # type: ignore[arg-type]

        # Highlights
        if highlight_columns is not None:
            if isinstance(highlight_columns, str):
                highlight_columns = [highlight_columns]
            styler.set_properties(
                **{'background-color': '#ffffb3'},
                subset=list(highlight_columns),
            )

        return styler


    def highlight_magnitude(
        self,
        frame: pd.DataFrame,
        format: Styler,
        column: str,
        threshold: float,
        colormap: str = 'plasma_r',
        low: float = 0,
        high: float = 0,
        vmin: None | float = None,
        vmax: None | float = None,
    ) -> Styler:
        magnitude = frame[column].fillna(0).abs()
        above_threshold = (~magnitude.isna()) & (magnitude > threshold)
        return format.background_gradient(
            cmap=colormap,
            low=low,
            high=high,
            vmin=vmin,
            vmax=vmax,
            gmap=magnitude,
            subset=(above_threshold, frame.columns), # type: ignore[arg-type]
        )


    # ----------------------------------------------------------------------------------


    def render_format(self, format: Styler) -> str:
        return format.to_html()


    def _display_html(self, html: str) -> None:
        if self._display is None:
            import IPython.display
            object.__setattr__(self, '_display', IPython.display.display)
            object.__setattr__(self, '_html', IPython.display.HTML)

        assert self._display is not None
        assert self._html is not None
        self._display(self._html(html))


    def display(self, block: BlockContent | Styler) -> None:
        self._display_html(self.render(block))


    def display_all(self, blocks: Sequence[BlockContent | Styler]) -> None:
        self._display_html(self.render_all(blocks))


# ======================================================================================


