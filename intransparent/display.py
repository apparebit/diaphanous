from functools import partial
import itertools as it
import linecache
import math
import re
import sys
import textwrap
from typing import Any, Callable, cast

from IPython.display import display, HTML
import pandas as pd


# ======================================================================================


def _sgr(code: str) -> str:
    return f"\x1b[{code}m"


def _format_title(title: str, *, delta_percent: str) -> str:
    if title == 'Δ%':
        return delta_percent
    if 'a' <= title[0] <= 'z':
        return title.title()
    return title


def _is_period(value: object) -> bool:
    if not isinstance(value, pd.Period):
        return False
    return value.freqstr in ('Q-DEC', '6M', 'Y')


def _format_period(value: object) -> str:
    period = cast(pd.Period, value)
    freq = period.freqstr
    if freq == 'Q-DEC':
        return f'{period.year:04d} Q{period.month // 3:1d}'
    elif freq == '6M':
        return f'{period.year:04d} H{period.month // 6:1d}'
    else:
        return str(period.year)


def _formatter_for(column: pd.Series, not_available: str) -> Callable[[Any], str]:
    if pd.api.types.is_bool_dtype(column.dtype):
        fmt_value = lambda v: 'true' if v else 'false'
    elif pd.api.types.is_period_dtype(column.dtype):
        fmt_value = _format_period
    elif pd.api.types.is_integer_dtype(column.dtype):
        fmt_value = lambda v: f'{v:,d}'
    else:
        fmt_value = lambda v: f'{v:.2f}'

    return lambda v: not_available if pd.isna(v) else fmt_value(v)


def _pad_columns(data: pd.DataFrame, widths: pd.Series) -> pd.DataFrame:
    return data.apply(lambda column: column.str.rjust(widths[column.name]))


def _join_cells(data: pd.DataFrame, column_separator: str, row_terminator: str) -> str:
    return row_terminator.join(
        data.apply(lambda row: column_separator.join(row), axis=1)
    )


# ======================================================================================


_OUTLIER_BINS = (-0.1, 5.0, 30.0, 100.0, math.inf)

_OUTLIER_SGR = (
    None,
    ('1;38;5;202', '39;0'),
    ('1;38;5;160', '39;0'),
    ('1;38;5;126', '39;0'),
)

_OUTLIER_CSS = (
    '',
    'color: #d95100; background-color: #ffeada;',
    'color: #f4002a; background-color: #ffe8e7;',
    'color: #d900c7; background-color: #ffe5fa;',
)


def _maybe_has_outliers(data: pd.DataFrame) -> bool:
    columns = data.columns
    return 'reports' in columns and 'Δ%' in columns and 'NCMEC' in columns


def _bin_outliers(percentages: pd.Series) -> pd.Series:
    # labels=False causes bin numbers to be returned.
    return pd.cut(percentages.abs(), bins=_OUTLIER_BINS, labels=False)


def _highlight_outliers_sgr(percentages: pd.Series, data: pd.DataFrame) -> pd.DataFrame:
    """
    Inject ANSI SGR codes that highlight Δ% outliers amongst the cells of the
    given dataframe. This function assumes that the dataframe contains the
    requisite reports, Δ%, and NCMEC columns, right next to each other, in that
    same order, and with their contents fully formatted including column
    padding. Due to the last assumption, the dataframe contains only strings and
    the percentage differences are passed through a separate argument.
    """
    bins = _bin_outliers(percentages)

    data = data.copy()
    for row, bin in enumerate(bins):
        if pd.isna(bin) or math.isclose(bin, 0.0):
            continue

        codes = _OUTLIER_SGR[int(bin)]
        if codes is None:
            continue

        data.at[row, 'reports'] = _sgr(codes[0]) + data.at[row, 'reports']
        data.at[row, 'NCMEC'] = data.at[row, 'NCMEC'] + _sgr(codes[1])

    return data


def _highlight_outliers_css(data: pd.DataFrame) -> pd.DataFrame:
    """
    Create a new dataframe with CSS styles that highlight Δ% outliers amongst
    the cells of the given dataframe. This function assumes that the dataframe
    contains the requisite reports, Δ%, and NCMEC columns, right next to each
    other and in that same order.
    """
    bins = _bin_outliers(data['Δ%'])
    row_styles = bins.apply(lambda bin: '' if pd.isna(bin) else _OUTLIER_CSS[int(bin)])
    return pd.DataFrame({
        'reports': row_styles,
        'Δ%': row_styles,
        'NCMEC': row_styles,
    }, index=data.index)


# ======================================================================================


def format_text(
    platform: str,
    df: pd.DataFrame,
    *,
    not_available: str = '⋯⋯',
    column_separator: str = '   ',
    row_terminator: str = '',
    delta_percent: str = 'Δ%',
    header_terminator: str = '',
    use_sgr: bool = False,
) -> str:
    # Make index part of table.
    df = df.sort_index().reset_index(names='Year')

    # Determine titles and their minimum widths, i.e., longest words.
    titles = df.columns.to_series().apply(
        partial(_format_title, delta_percent=delta_percent))
    widths = titles.str.split().apply(lambda words: max(len(w) for w in words))

    # Format columns, determine theirs widths, and combine with title widths.
    body = df.apply(lambda column: column.apply(_formatter_for(column, not_available)))
    widths = body.apply(lambda column: column.str.len().max()).combine(widths, max)

    # Text-wrap titles to their widths, normalize number of lines by prepending
    # empty lines, and convert to a dataframe with the same columns as body.
    titles = pd.Series(
        (textwrap.wrap(title, width) for title, width in zip(titles, widths)),
        index=titles.index)
    line_count = titles.apply(lambda lines: len(lines)).max()
    header = pd.DataFrame(
        [[*it.repeat('', line_count - len(lines)), *lines] for lines in titles],
        index=titles.index,
    ).transpose()

    # Normalize the cell width for each column.
    header = _pad_columns(header, widths)
    body = _pad_columns(body, widths)

    # Maybe highlight outliers.
    if use_sgr and _maybe_has_outliers(df):
        body = _highlight_outliers_sgr(df['Δ%'], body)

    # Render down to string.
    bold = _sgr('1') if use_sgr else ''
    plain = _sgr('0') if use_sgr else ''

    return (
        bold
        + _join_cells(header, column_separator, row_terminator + '\n')
        + plain + header_terminator + '\n'
        + _join_cells(body, column_separator, row_terminator + '\n')
        + row_terminator  # No trailing newline
    )


def format_latex(platform: str, df: pd.DataFrame) -> str:
    alignment = "r" * (len(df.columns) + 1)
    body = format_text(
        platform,
        df,
        not_available='$\cdots$',
        column_separator='  &  ',
        row_terminator='  \\\\',
        delta_percent='\\Delta\\%',
        header_terminator='  \\\\ \\hline',
        use_sgr=False,
    )
    return f'\\begin{{tabular}}{{{alignment}}}\n{body}\n\\end{{tabular}}'


# ======================================================================================


def show_html(text: None | str = None, **kwargs: str) -> None:
    if len(kwargs) > 0:
        assert text is None
        s = ''.join(f'<{tag}>{content}</{tag}>' for tag, content in kwargs.items())
    elif text is not None:
        s = f'<p>{text}</p>'
    else:
        s = ''

    display(HTML(s))


# --------------------------------------------------------------------------------------


def _do_not_log(**kwargs: object) -> None:
    pass

def _do_log(**kwargs: object) -> None:
    for key, value in kwargs.items():
        print(f'>>> {key}:', value)

# When I needed instrumentation in _get_table_name() for 2nd time, I made it permanent.
_logger = _do_not_log


def _get_table_name(invocation: str) -> None | str:
    # Try locating source code through stack frame
    frame = sys._getframe(2)
    _logger(frame=frame)

    lines = linecache.getlines(frame.f_code.co_filename, frame.f_globals)
    lineno = frame.f_lineno - 1
    _logger(len_lines=len(lines), lineno=lineno)
    if len(lines) <= lineno:
        return None

    # Find start of invocation in source code.
    text = ''.join(lines[lineno:])
    start = text.find(invocation)
    _logger(invocation=invocation, start=start)
    if start == -1:
        return None

    # Find end of first argument, stopping at next comma or closing parenthesis.
    start = start + len(invocation)
    stop1 = text.find(',', start)
    stop2 = text.find(')', start)
    stop = stop1 if start <= stop1 < stop2 else stop2
    _logger(stop=stop)
    if stop == -1:
        return None

    # Given the above, very simplistic scan, make sure that the result is usable.
    name = text[start : stop].strip()
    _logger(raw_name=name)
    if not name.isidentifier():
        return None

    # Drop tech appearance when rendering name.
    name = name.replace('_', ' ')
    _logger(name=name)
    return name


def show_info(
    table: pd.DataFrame,
    *,
    table_name: None | str = None,
    extra: None | str = None,
    invocation: None | str = None,
) -> None:
    fragments = ['<p>Table']

    if table_name is None:
        if invocation is None:
            invocation = 'show_info('
        table_name = _get_table_name(invocation)
    if table_name is not None:
        fragments.append(f' <strong>{table_name}</strong>')

    rows = len(table)
    fragments.append(f' with {rows:,d} rows')
    fragments.append('' if extra is None else extra)
    fragments.append(':</p><ul>')

    if table.index.nlevels == 1:
        label = table.index.name
        fragments.append('<li>index')
        fragments.append('' if label is None else f' {label}')
        fragments.append(f': {table.index.dtype}</li>')
    else:
        index = cast(pd.MultiIndex, table.index)
        for level, (name, typ) in enumerate(zip(index.names, index.dtypes)):
            fragments.append('<li>index ')
            fragments.append(f'#{level}' if name is None else name)
            fragments.append(f': {typ}</li>')

    for col, typ in zip(table.columns, table.dtypes):
        nonnull = rows - table[col].isna().sum()
        fragments.append(f'<li>column {col}: {typ}, ')
        fragments.append('all' if nonnull == rows else f'{nonnull:,d}')
        fragments.append(' values non-null</li>')

    fragments.append('</ul>')
    display(HTML(''.join(fragments)))


def show_table(
    table: pd.Series | pd.DataFrame,
    *,
    table_name: None | str = None,
    highlight: None | str | list[str] = None,
) -> None:
    if isinstance(table, pd.Series):
        table = table.to_frame()
    assert isinstance(table, pd.DataFrame)
    style = table.style

    # Add table name as caption
    if table_name is None:
        table_name = _get_table_name('show_table(')
    if table_name is not None:
        style.set_caption(table_name)
        style.set_table_styles([
            {
                'selector': 'caption',
                'props': 'caption-side: bottom; font-style: italic; margin-top: 1ex;'
            }
        ])

    # Improve readability of large numbers.
    style.format(thousands=',')

    if table.index.nlevels == 1:
        # Improve presentation of periods.
        if all(_is_period(value) for value in table.index.values):
            style.format_index(_format_period, axis=0)
    else:
        # Improve presentation of tables with multi-indices.
        level_name = table.index.names[0]
        if level_name is not None:
            for _, group in table.groupby(level_name):
                # If the table is the result of a query, its multi-index is that
                # of the original table and some groups may be empty.
                if group.size > 0:
                    style.set_table_styles(
                        {
                            group.index[0]: [{
                                'selector': '',
                                'props': 'border-top: 2px solid #000000 !important;',
                            }]
                        },
                        overwrite=False,
                        axis=1)

    # Highlight outliers when comparing CSAM report counts.
    if _maybe_has_outliers(table):
        style.apply(_highlight_outliers_css, axis=None)

    # Highlight column(s) as requested.
    if highlight is not None:
        if isinstance(highlight, str):
            highlight = [highlight]
        style.set_properties(**{'background-color': '#ffffb3'}, subset=highlight)

    # Ready to render...
    display(HTML(style.to_html()))
