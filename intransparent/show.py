from collections.abc import Iterator
import math
from typing import cast, NamedTuple, TypeAlias

from IPython.display import display, HTML
import numpy as np
import pandas as pd

from pandas.api.types import is_numeric_dtype
from pandas.io.formats.style import Styler

Dtype: TypeAlias = np.dtype | pd.api.extensions.ExtensionDtype

# --------------------------------------------------------------------------------------

def show(
    value: str | pd.DataFrame,
    *,
    show_schema: bool = False,
    caption: None | str = None,
    highlight_columns: None | str | list[str] = None,
    highlight_rows: None | int | list[int] = None,
    margin_top: float = 0,
    margin_bottom: float = 2.0,
) -> None:
    if isinstance(value, str):
        display(HTML(value))
        return

    if show_schema:
        caption = 'Table ' + '' if caption is None else f'<strong>{caption}</strong> '
        caption += f'with {value.shape[0]} rows'

        schema = to_schema(value)
        style = format_table(
            schema,
            caption=caption,
            show_column_header=False,
            show_row_header=False,
            margin_bottom=margin_bottom,
        )
        style = format_schema(style)
        display(style)
        return

    style = format_table(
        value,
        caption=caption,
        highlight_columns=highlight_columns,
        highlight_rows=highlight_rows,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
    )

    columns = value.columns
    if 'reports' in columns and 'Δ%' in columns and 'NCMEC' in columns:
        style = highlight_magnitude(
            value,
            style,
            column='Δ%',
            threshold=1,
            low=0.1,
            vmin=0,
            vmax=600,
        )

    display(style)

# --------------------------------------------------------------------------------------

def to_schema(frame: pd.DataFrame) -> pd.DataFrame:
    schema = []
    for vertical in all_verticals(frame):
        schema.append(
            [
                'index' if vertical.kind == 'index' else 'column',
                vertical.name or '',
                ':',
                vertical.dtype,
                vertical.data.isna().sum(),
            ]
        )
    return pd.DataFrame(schema, columns=['kind', 'name', 'dtype', '', 'nulls'])

# --------------------------------------------------------------------------------------

def format_table(
    frame: pd.DataFrame,
    *,
    caption: None | str = None,
    show_column_header: bool = True,
    show_row_header: bool = True,
    highlight_columns: None | str | list[str] = None,
    highlight_rows: None | int | list[int] = None,
    margin_top: float = 0,
    margin_bottom: float = 2,
) -> Styler:
    style = frame.style
    table_styles = []

    # Add caption
    if caption is not None:
        style.set_caption(caption)
        props = [
            ('caption-side', 'top'),
            ('font-size', '1.1em'),
            ('margin-bottom', '2ex'),
        ]
        if '<strong>' not in caption and '<em>' not in caption:
            props.append(('font-style', 'italic'))
        table_styles.append({'selector': 'caption', 'props': props})

    # Suppress row and/or column headers
    if not show_row_header:
        style.hide(subset=None, level=None, names=False, axis=0)

    if not show_column_header:
        style.hide(subset=None, level=None, names=False, axis=1)

    # Handle alignment
    select_verticals = all_verticals if show_row_header else all_columns
    align_left = ','.join(
        v.selector for v in select_verticals(frame) if not is_numeric_dtype(v.dtype))
    if len(align_left) > 0:
        table_styles.append(
            {
                'selector': align_left,
                'props': [('text-align', 'start')],
            }
        )

    # Format numbers and NA
    style.format(thousands=',', na_rep='⋯')
    table_styles.append(
        {
            'selector': '',
            'props': [
                ('font-variant-numeric', 'tabular-nums'),
                (
                    'margin-top',
                    '0' if margin_top == 0 else f'{margin_top}em',
                ),
                (
                    'margin-bottom',
                    '0' if margin_bottom == 0 else f'{margin_bottom}em',
                ),
            ],
        }
    )

    for v in all_columns(frame):
        if pd.api.types.is_float_dtype(v.dtype):
            minval = cast(pd.Series, v.data).abs().pipe(lambda c: c[c > 0].min())
            logmin = 2 if pd.isna(minval) else math.ceil(math.log10(minval))
            precision = max(1, 3 - logmin)
            style.format(
                thousands=',',
                na_rep='⋯',
                precision=precision,
                subset=[v.name or v.position],
            )

    # Apply collected CSS
    if table_styles:
        style.set_table_styles(table_styles, overwrite=False) # type: ignore[arg-type]

    # Apply highlights to rows and columns
    if highlight_rows is not None:
        if not isinstance(highlight_rows, list):
            highlight_rows = [highlight_rows]
        style.set_table_styles({
            row_label: [{
                'selector': '',
                'props': [('background-color', '#feddb0')],
            }]
            for row_label in highlight_rows
        }, overwrite=False, axis=1)

    if highlight_columns is not None:
        if isinstance(highlight_columns, str):
            highlight_columns = [highlight_columns]
        # Don't use style.set_table_styles() for columns
        # because that changes column headers, too.
        style.set_properties(
            **{'background-color': '#ffffb3'},
            subset=highlight_columns,
        )

    return style


def highlight_magnitude(
    frame: pd.DataFrame,
    style: Styler,
    *,
    column: str,
    threshold: float = 0,
    colormap: str = 'Reds',
    low: float = 0,
    high: float = 0,
    vmin: None | float = None,
    vmax: None | float = None,
) -> Styler:
    magnitude = frame[column].fillna(0).abs()
    above_threshold = magnitude > threshold
    return style.background_gradient(
        cmap=colormap,
        low=low,
        high=high,
        vmin=vmin,
        vmax=vmax,
        gmap=magnitude,
        subset=(above_threshold, frame.columns), # type: ignore[arg-type]
    )


def format_schema(style: Styler) -> Styler:
    style.format({'nulls': format_nulls})
    style.set_table_styles(
        [
            {'selector': 'td', 'props': [('padding', '0.1em 1ex 0.1em 0')]},
            {
                'selector': 'td:nth-child(5)',
                'props': [('padding-left', '0.4em'), ('text-align', 'start')],
            },
        ],
        overwrite=False,
    )
    return style


def format_nulls(nulls: object) -> str:
    count = cast(int, nulls)
    quantity = 'no' if count == 0 else f'{count}'
    return f'({quantity} null{"" if count == 1 else "s"})'

# --------------------------------------------------------------------------------------

class Vertical(NamedTuple):
    kind: str
    position: int
    total: int
    name: None | str
    dtype: Dtype
    data: pd.Index | pd.Series

    @property
    def selector(self) -> str:
        if self.kind == 'index':
            return f'.level{self.position}'
        else:
            return f'.col{self.position}'


def all_verticals(frame: pd.DataFrame) -> Iterator[Vertical]:
    yield from all_levels(frame)
    yield from all_columns(frame)

def all_levels(frame: pd.DataFrame) -> Iterator[Vertical]:
    nlevels = frame.index.nlevels
    if nlevels == 1:
        yield Vertical(
            'index',
            0,
            1,
            frame.index.name,
            frame.index.dtype,
            frame.index,
        )
    else:
        multi_index = cast(pd.MultiIndex, frame.index)
        for level_index, dtype in enumerate(multi_index.dtypes):
            yield Vertical(
                'index',
                level_index,
                nlevels,
                multi_index.names[level_index],
                cast(Dtype, dtype),
                multi_index.levels[level_index],
            )

def all_columns(frame: pd.DataFrame) -> Iterator[Vertical]:
    ncolumns = frame.shape[0]
    for column_index, dtype in enumerate(frame.dtypes):
        name = frame.columns[column_index]
        yield Vertical(
            'column',
            column_index,
            ncolumns,
            None if name is None else str(name),
            cast(Dtype, dtype),
            frame.iloc[:, column_index],
        )
