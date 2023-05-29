from functools import partial
import itertools as it
import math
import textwrap
from typing import cast

from IPython.display import display, HTML
import pandas as pd


# ======================================================================================


def _sgr(code: str) -> str:
    return f"\x1b[{code}m"


def _format_title(title: str, *, delta_percent: str) -> str:
    title = title.replace('_pct', ' percent')
    title = title.replace('_', ' ')
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


def _format_column(column: pd.Series, not_available: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(column.dtype):
        return column.apply(lambda v: 'true' if v else 'false')
    elif pd.api.types.is_period_dtype(column.dtype):
        return column.apply(_format_period)
    elif pd.api.types.is_integer_dtype(column.dtype):
        return column.apply(lambda v: not_available if pd.isna(v) else f'{v:,d}')
    elif pd.api.types.is_float_dtype(column.dtype):
        # Pick a precision so that at least three significant digits are displayed
        minval = column.abs().pipe(lambda c: c[c > 0].min())
        logmin = 2 if pd.isna(minval) else math.ceil(math.log10(minval))
        precision = max(1, 3 - logmin)
        return column.apply(
            lambda v: not_available if pd.isna(v) else f'{v:.{precision}f}')
    else:
        c = column.astype(str)
        # d = c.copy()
        # d.loc[c.str.len() > 15] = c.str.slice(stop=12)
        # d.loc[c.str.len() > 15] = (
        #     d + pd.Series(['...']).repeat(c.shape[0]).reset_index(drop=True))
        return c


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
    df: pd.DataFrame,
    *,
    not_available: str = '⋯⋯',
    column_separator: str = '   ',
    row_terminator: str = '',
    delta_percent: str = 'Δ%',
    header_terminator: str = '',
    use_sgr: bool = False,
    highlights: None | str | list[str] = None,
) -> str:
    # Make index part of frame.
    df = df.reset_index()

    # Determine titles and their minimum widths, i.e., longest words.
    titles = df.columns.to_series().apply(
        partial(_format_title, delta_percent=delta_percent))
    widths = titles.str.split().apply(lambda words: max(len(w) for w in words))

    # Format columns, determine theirs widths, and combine with title widths.
    body = df.apply(lambda column: _format_column(column, not_available))
    widths = body.apply(lambda column: column.str.len().max()).combine(widths, max)

    # Text-wrap each title to its column width.
    titles = pd.Series(
        (textwrap.wrap(title, width) for title, width in zip(titles, widths)),
        index=titles.index)
    # Normalize number of lines for each title and combine into dataframe.
    line_count = titles.apply(lambda lines: len(lines)).max()
    header = pd.DataFrame(
        [[*it.repeat('', line_count - len(lines)), *lines] for lines in titles],
        index=titles.index,
    ).transpose()

    # Normalize the cell width for each column
    header = _pad_columns(header, widths)
    body = _pad_columns(body, widths)

    # Maybe highlight columns.
    if use_sgr and highlights is not None:
        if isinstance(highlights, str):
            highlights = [highlights]
        for column in highlights:
            body[column] = _sgr('48;5;230') + body[column] + _sgr('49')

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


def format_latex(df: pd.DataFrame) -> str:
    alignment = "r" * (len(df.columns) + 1)
    body = format_text(
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
    s = ''
    if text is not None:
        s += f'<p>{text}</p>'
    if len(kwargs) > 0:
        s += ''.join(f'<{tag}>{content}</{tag}>' for tag, content in kwargs.items())
    display(HTML(s))


def show_info(
    table: pd.DataFrame,
    *,
    title: None | str = None,
    description: None | str = None,
    highlights: None | str | list[str] = None,  # unused
) -> None:
    fragments = ['<p>Table']

    if title is not None:
        fragments.append(f' <strong>{title}</strong>')

    rows = len(table)
    fragments.append(f' with {rows:,d} rows')
    fragments.append('' if description is None else f' {description}')
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
    title: None | str = None,
    description: None | str = None,  # unused
    highlights: None | str | list[str] = None,
    first_index_rules: bool = False
) -> None:
    if isinstance(table, pd.Series):
        table = table.to_frame()
    assert isinstance(table, pd.DataFrame)
    style = table.style

    # Add table name as caption
    if title is not None:
        style.set_caption(title)
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
    elif first_index_rules:
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

    # Highlight column(s) as requested.
    if highlights is not None:
        if isinstance(highlights, str):
            highlights = [highlights]
        style.set_properties(
            **{'background-color': '#ffffb3'},
            subset=highlights,
        )

    # Highlight outliers when comparing CSAM report counts.
    if _maybe_has_outliers(table):
        style.apply(_highlight_outliers_css, axis=None)

    # Ready to render...
    display(HTML(style.to_html()))
