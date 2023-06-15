from abc import ABC, abstractmethod
from collections.abc import Sequence
import math
import os
from typing import Callable, cast, Generic, TextIO, TypeVar

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
    TerminalRenderer,
)

from .vertical import all_columns, all_verticals
from .texting import format_label, visible_length


FormatT = TypeVar('FormatT')


class Formatter(ABC, Generic[FormatT]):
    """
    The base of formatters. A formatter knows how to convert a dataframe into a
    human-readable representation. The constructor arguments are required
    configuration state.
    """

    def __init__(
        self,
        *,
        use_color: bool,
        not_available: str,
        significant_digits: int,
        decimal: str,
        thousands: str,
    ) -> None:
        self._use_color = use_color
        self._not_available = not_available
        self._significant_digits = significant_digits
        self._decimal = decimal
        self._thousands = thousands

    # ----------------------------------------------------------------------------------
    # Configuration and Context-Dependent Utilities

    @property
    def use_color(self) -> bool:
        return self._use_color

    @use_color.setter
    def use_color(self, use_color: bool) -> None:
        self._use_color = bool(use_color)

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
        for vertical in all_verticals(frame):
            schema.append(
                [
                    'index' if vertical.is_level else 'column',
                    vertical.name,
                    vertical.dtype,
                    vertical.data.isna().sum(),
                ]
            )
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

        fragments = cast(
            tuple[str | InlineContent],
            (
                'Table ',
                *(() if name is None else (Markup.tx.strong(name), ' ')),
                f'with {frame.shape[0]} rows',
            ),
        )
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

    # ----------------------------------------------------------------------------------

    def format_label(self, label: object) -> str:
        """Format the label for an index level or column."""
        return format_label(label)

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

    def render_block(self, block: BlockContent) -> str:
        """Render the given markup to a string."""
        return block.render(self.markup_renderer)

    @abstractmethod
    def render_format(self, format: FormatT) -> str:
        """Render the given format to a string."""

    def render(self, block: BlockContent | FormatT) -> str:
        """Render the given block content or format."""
        if isinstance(block, BlockContent):
            return self.render_block(block)
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
        use_color: bool = True,
        not_available: str = '⋯',
        significant_digits: int = 3,
        decimal: str = '.',
        thousands: str = ',',
    ) -> None:
        super().__init__(
            use_color=use_color,
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
        format.set_table_styles(
            [
                {'selector': 'td', 'props': [('padding', '0.1em 1ex 0.1em 0')]},
                {
                    'selector': 'td:nth-child(5)',
                    'props': [('padding-left', '0.4em'), ('text-align', 'start')],
                },
            ],
            overwrite=False,
        )
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
                assert isinstance(caption, Paragraph)
                caption = self.markup_renderer.reduce(
                    caption.fragments
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
                [self.format_label(column) for column in frame.columns], axis=1
            )

        # Column alignment
        align_start = ','.join(
            v.selector for v in all_verticals(frame) if not is_numeric_dtype(v.dtype)
        )
        if len(align_start) > 0:
            table_styles.append(
                {
                    'selector': align_start,
                    'props': [('text-align', 'start')],
                }
            )

        # The data
        styler.format(
            decimal=self.decimal, thousands=self.thousands, na_rep=self.not_available
        )
        table_styles.append(
            {
                'selector': '',
                'props': [
                    ('font-variant-numeric', 'tabular-nums'),
                    (
                        'margin-bottom',
                        '0' if margin_bottom == 0 else f'{margin_bottom}em',
                    ),
                ],
            }
        )

        # Actually apply table styles
        if table_styles:
            styler.set_table_styles(table_styles)  # type: ignore[arg-type]

        # Highlights
        if self.use_color and highlight_columns is not None:
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
        if not self.use_color:
            return format

        magnitude = frame[column].fillna(0).abs()
        above_threshold = (~magnitude.isna()) & (magnitude > threshold)
        return format.background_gradient(
            cmap=colormap,
            low=low,
            high=high,
            vmin=vmin,
            vmax=vmax,
            gmap=magnitude,
            subset=(above_threshold, frame.columns),  # type: ignore[arg-type]
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


class TerminalOutput:
    def __init__(
        self,
        frame: pd.DataFrame,
        caption: None | str | Paragraph = None,
        highlight_columns: None | str | Sequence[str] = None,
        show_column_header: bool = True,
        show_row_header: bool = True,
        format_label_fn: Callable[[object], str] = format_label,
    ) -> None:
        self.frame = frame
        self.caption = caption
        self.highlight_columns = highlight_columns
        self.show_column_header = show_column_header
        self.show_row_header = show_row_header

        self.format: None | pd.DataFrame = None
        self.format_label = format_label_fn

    def format_frame(self) -> None:
        # Determine function used for iterating over verticals:
        pick_verticals = all_verticals if self.show_row_header else all_columns

        # Determine titles and their minimum widths, i.e., longest words.
        if self.show_column_header:
            titles = (self.format_label(v.name) for v in pick_verticals(self.frame))
            widths = (max(len(w) for w in ws) for t in titles for ws in t.split())

        # Format columns, determine theirs widths, and combine with title widths.
        #columns = []


        # ( format_column(v.data) for v in pick_verticals(self.frame))

        # column_formats = {}

        # def do_format_column(column: pd.Series) -> pd.Series:
        #     format, formatted = _format_column(column, not_available)
        #     column_formats[column.name] = format
        #     return formatted

        # body = df.apply(do_format_column)
        # widths = body.apply(lambda column: column.str.len().max()).combine(widths, max)

        # # Text-wrap each title to its column width.
        # titles = pd.Series(
        #     (textwrap.wrap(title, width) for title, width in zip(titles, widths)),
        #     index=titles.index,
        # )
        # # Normalize number of lines for each title by prepending empty lines.
        # line_count = titles.apply(lambda lines: len(lines)).max()
        # header = pd.DataFrame(
        #     [[*it.repeat('', line_count - len(lines)), *lines] for lines in titles],
        #     index=titles.index,
        # )
        # # Transpose the dataframe so that each title forms a column.
        # header = header.transpose()

        # # Normalize the cell width for each column
        # header = header.apply(lambda column: column.str.ljust(widths[column.name]))

        # def pad_column(column: pd.Series) -> pd.Series:
        #     name: str = cast(str, column.name)
        #     if _ColumnFormat.STRING == column_formats[name]:
        #         return column.str.ljust(widths[name])
        #     else:
        #         return column.str.rjust(widths[name])

        # body = body.apply(pad_column)

    def style_frame(
        self,
        *,
        column: int,
        row: int,
        color: None | str,
        background_color: None | str,
    ) -> None:
        pass

    def render_frame(self, renderer: TerminalRenderer) -> str:
        frame = str(self.frame)
        frame_width: int = max(len(line) for line in frame.split('\n'))

        if self.caption is not None:
            if isinstance(self.caption, str):
                markup = Markup.tx.p(Markup.tx.strong(self.caption))
            else:
                markup = self.caption
            with renderer.new_line_width(frame_width) as r:
                caption_lines = markup.render(r).rstrip().split('\n')
            caption_width = max(visible_length(line) for line in caption_lines)
            indent_width = (frame_width - caption_width) // 2
            indent = ' ' * indent_width
            caption = indent + ('\n' + indent).join(caption_lines) + '\n\n'
        else:
            caption = ''

        return caption + frame + '\n\n'


class TerminalFormatter(Formatter[TerminalOutput]):

    def __init__(
        self,
        out: TextIO,
        *,
        use_sgr: None | bool = None,
        not_available: str = '⋯',
        significant_digits: int = 3,
        decimal: str = '.',
        thousands: str = ',',
    ) -> None:
        if use_sgr is None:
            use_sgr = out.isatty()

        super().__init__(
            use_color=use_sgr,
            not_available=not_available,
            significant_digits=significant_digits,
            decimal=decimal,
            thousands=thousands,
        )

        if use_sgr and out.isatty():
            width, _ = os.get_terminal_size(out.fileno())
        else:
            width = 70

        self._out = out
        self._line_width = width
        self._markup_renderer = TerminalRenderer(
            line_width=width,
            use_sgr=use_sgr,
        )

    @property
    def markup_renderer(self) -> TerminalRenderer:
        return self._markup_renderer

    def style_schema(
        self,
        frame: pd.DataFrame,
        format: TerminalOutput
    ) -> TerminalOutput:
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
    ) -> TerminalOutput:
        return TerminalOutput(frame, caption)

    def highlight_magnitude(
        self,
        frame: pd.DataFrame,
        format: TerminalOutput,
        column: str,
        threshold: float,
        colormap: str = 'plasma_r',
        low: float = 0,
        high: float = 0,
        vmin: None | float = None,
        vmax: None | float = None,
    ) -> TerminalOutput:
        return format

    def render_format(self, format: TerminalOutput) -> str:
        return format.render_frame(self.markup_renderer)

    def display(self, block: BlockContent | TerminalOutput) -> None:
        print(self.render(block), file=self._out)

    def display_all(self, blocks: Sequence[BlockContent | TerminalOutput]) -> None:
        print(self.render_all(blocks), file=self._out)



# def _background_gradient(
#     data,
#     cmap: str | Colormap = "PuBu",
#     low: float = 0,
#     high: float = 0,
#     text_color_threshold: float = 0.408,
#     vmin: float | None = None,
#     vmax: float | None = None,
#     gmap: Sequence | np.ndarray | DataFrame | Series | None = None,
#     text_only: bool = False,
# ):
#     """
#     Color background in a range according to the data or a gradient map
#     """
#     if gmap is None:  # the data is used the gmap
#         gmap = data.to_numpy(dtype=float, na_value=np.nan)
#     else:  # else validate gmap against the underlying data
#         gmap = _validate_apply_axis_arg(gmap, "gmap", float, data)

#     with _mpl(Styler.background_gradient) as (_, _matplotlib):
#         smin = np.nanmin(gmap) if vmin is None else vmin
#         smax = np.nanmax(gmap) if vmax is None else vmax
#         rng = smax - smin
#         # extend lower / upper bounds, compresses color range
#         norm = _matplotlib.colors.Normalize(smin - (rng * low), smax + (rng * high))

#         if cmap is None:
#             rgbas = _matplotlib.colormaps[_matplotlib.rcParams["image.cmap"]](
#                 norm(gmap)
#             )
#         else:
#             rgbas = _matplotlib.colormaps.get_cmap(cmap)(norm(gmap))

#         def relative_luminance(rgba) -> float:
#             """
#             Calculate relative luminance of a color.

#             The calculation adheres to the W3C standards
#             (https://www.w3.org/WAI/GL/wiki/Relative_luminance)

#             Parameters
#             ----------
#             color : rgb or rgba tuple

#             Returns
#             -------
#             float
#                 The relative luminance as a value from 0 to 1
#             """
#             r, g, b = (
#                 x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
#                 for x in rgba[:3]
#             )
#             return 0.2126 * r + 0.7152 * g + 0.0722 * b

#         def css(rgba, text_only) -> str:
#             if not text_only:
#                 dark = relative_luminance(rgba) < text_color_threshold
#                 text_color = "#f1f1f1" if dark else "#000000"
#                 return (
#                     f"background-color: {_matplotlib.colors.rgb2hex(rgba)};"
#                     + f"color: {text_color};"
#                 )
#             else:
#                 return f"color: {_matplotlib.colors.rgb2hex(rgba)};"

#         if data.ndim == 1:
#             return [css(rgba, text_only) for rgba in rgbas]
#         else:
#             return DataFrame(
#                 [[css(rgba, text_only) for rgba in row] for row in rgbas],
#                 index=data.index,
#                 columns=data.columns,
#             )

# def down_sample(color: tuple[int, int, int]) -> int:
#     r, g, b = color
#     r = r * 6 // 256
#     g = g * 6 // 256
#     b = b * 6 // 256
#     if r == g == b:
#         pass
#     return 16 + r * 36 + g * 6+ b
# CSI = re.compile(r'(?:\x9b|\x1b\[)[0-?]*[@-~]')

