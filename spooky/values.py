"""Null handling shared by the data layer and the components.

A JSON `null` does not survive pandas as `None`. Depending on the column dtype
it arrives as `float('nan')` (object/float columns) or `pd.NA` (nullable
integer columns), and neither satisfies `value is None`. Every `is None` guard
against record data is therefore wrong, which is how "nan" reached the UI and
how films crashed the link builder.

These are the three shapes a null actually takes. Check them explicitly.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


def is_missing(value: Any) -> bool:
    """True for `None`, `float('nan')`, `pd.NA`, and `pd.NaT`."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    return isinstance(value, float) and math.isnan(value)


def as_int(value: Any) -> int | None:
    """Coerce to `int`, or `None` when the value is missing.

    Guards `int(pd.NA)`, which raises `TypeError`.
    """
    if is_missing(value):
        return None
    return int(value)
