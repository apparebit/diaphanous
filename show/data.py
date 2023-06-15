from enum import auto, StrEnum
import math
from typing import Any, Callable, cast, TypeAlias

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_categorical_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_period_dtype,
)


_TMP_DECIMAL = 'ᴟ'


Dtype: TypeAlias = np.dtype | pd.api.extensions.ExtensionDtype
FormatterT: TypeAlias = Callable[[object], str]


class Alignment(StrEnum):
    START = auto()
    END = auto()


def to_alignment(data: pd.Series) -> Alignment:
    dtype = base_dtype(data.dtype)

    if is_bool_dtype(dtype) or is_integer_dtype(dtype) or is_float_dtype(dtype):
        return Alignment.END
    else:
        return Alignment.START


def to_formatter(
    data: pd.Series | pd.Index,
    *,
    significant_digits: int,
    decimal: str = '.',
    thousands: str = ',',
) -> Callable[[Any], str]:
    """
    Determine an appropriate formatter for the given vertical. The resulting
    function does not handle N/A or NaN values.
    """
    dtype = base_dtype(data.dtype)

    fn = None
    if is_bool_dtype(dtype):
        return lambda v: 'true' if v else 'false'
    elif is_integer_dtype(dtype):
        if thousands == ',':
            return lambda v: f'{v:,d}'
        else:
            return lambda v: f'{v:,d}'.replace(',', thousands)
    elif is_float_dtype(dtype):
        prec = calc_precision(data, significant_digits)
        if decimal == '.' and thousands == ',':
            return lambda v: f'{v:,.{prec}f}'
        elif '.' not in thousands:
            return lambda v: (
                f'{v:,.{prec}f}'
                .replace(',', thousands)
                .replace('.', decimal))
        else:
            return lambda v: (
                f'{v:,.{prec}f}'
                .replace('.', _TMP_DECIMAL)
                .replace(',', thousands)
                .replace(_TMP_DECIMAL, decimal)
            )
    elif is_period_dtype(dtype) and all(is_simple_period(p) for p in data):
        fn = format_simple_period
    else:
        fn = lambda v: f'{v}'

    return fn


def is_valid_thousands(thousands: str) -> bool:
    return _TMP_DECIMAL not in thousands


def base_dtype(dtype: Dtype) -> Dtype:
    if is_categorical_dtype(dtype):
        return cast(pd.api.types.CategoricalDtype, dtype).categories.dtype
    return dtype


def calc_precision(data: pd.Series | pd.Index, significant_digits: int = 3) -> int:
    if isinstance(data, pd.Series):
        min_nonzero_magnitude = data.abs().pipe(lambda c: c[c > 0].min())
    else:
        min_nonzero_magnitude = calc_min_nonzero_magnitude(cast(pd.Index, data))

    if pd.isna(min_nonzero_magnitude):
        return 0

    # For 0 < minval < 1: -logmin == zeros past decimal + 1
    logmin = math.floor(math.log10(min_nonzero_magnitude))
    return max(0, significant_digits - logmin - 1)


def calc_time_precision(data: pd.Series, significant_digits: int = 3) -> int:
    fractional = data.dt.microsecond * 1_000 + data.dt.nanosecond
    min_nonzero_fractional = fractional[fractional > 0].min()
    if pd.isna(min_nonzero_fractional):
        return 0
    logmin = math.floor(math.log10(min_nonzero_fractional))
    return max(9, 9 - logmin - 1 + significant_digits)


def calc_min_nonzero_magnitude(data: pd.Index) -> float:
    try:
        return min(m for m in (math.fabs(n) for n in data) if m > 0)
    except ValueError:
        return math.nan


def is_simple_period(period: Any) -> bool:
    # FIXME: When Pandas starts exporting NAType and NaTType, use them above
    if pd.isna(period):
        return True

    assert isinstance(period, pd.Period)
    freq = period.freqstr
    if freq not in ('A-DEC', 'Q-DEC'):
        return True
    if freq != '6M':
        return False
    return period.month in (1, 7)


def format_simple_period(period: pd.Period) -> str:
    match period.freqstr:
        case 'A-DEC':
            return f'{period.year:04d}'
        case 'Q-DEC':
            return f'{period.year:04d} Q{period.month // 3:1d}'
        case '6M':
            return f'{period.year:04d} H{1 + period.month // 6:1d}'
        case _:
            raise ValueError(f'{period} is not a simple period')
