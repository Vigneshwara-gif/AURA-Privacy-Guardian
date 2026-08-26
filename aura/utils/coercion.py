"""
Defensive type coercion for untrusted and semi-trusted values.

AURA reads values from three sources that can all produce surprises:

  * the operating system — ``psutil`` can return ``None`` for a counter that
    is unavailable, and process names are attacker-influencable strings
  * pandas — a missing CSV cell arrives as ``float('nan')`` or ``pd.NA``,
    neither of which behaves like a normal absent value
  * scikit-learn — decision scores can be ``inf`` when a model is degenerate

The existing code has three independent implementations of this logic
(``app.py``, ``aura_core.py``, ``logger.py``) which disagree in one important
respect: ``logger._safe_int`` has no NaN guard, so ``int(float('nan'))``
raises ``ValueError`` there while the other two return the fallback. This
module implements the union of the safe behaviours.

Deliberately no pandas import. These helpers are used by the logging layer
and by the future FastAPI process, neither of which should pay pandas' import
cost or depend on it being installed. Missing-value detection is done
structurally instead: NaN is the only value that is not equal to itself, and
``pd.NA`` is handled by catching the ``TypeError`` its ambiguous truth value
raises.
"""

from __future__ import annotations

import math
import unicodedata
from typing import Any, TypeVar

__all__ = [
    "clamp",
    "is_missing",
    "safe_bool",
    "safe_float",
    "safe_int",
    "safe_text",
    "strip_control_characters",
]

_NumberT = TypeVar("_NumberT", int, float)

# Strings that pandas, CSV exports and human editors all use for "no value".
_MISSING_TOKENS = frozenset(
    {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "nan",
        "none",
        "null",
        "nil",
        "unknown",
        "<na>",
    }
)

_TRUE_TOKENS = frozenset({"1", "true", "t", "yes", "y", "on", "enabled"})
_FALSE_TOKENS = frozenset({"0", "false", "f", "no", "n", "off", "disabled"})


def is_missing(value: Any) -> bool:
    """
    Return True for values that represent absence rather than data.

    Covers ``None``, NaN, ``pd.NA``, and the textual placeholders that appear
    in CSV exports. Written without pandas so this module stays importable in
    a process that has not loaded it.
    """
    if value is None:
        return True

    # NaN is the only value not equal to itself. pd.NA returns pd.NA from the
    # comparison, and bool(pd.NA) raises TypeError — which is itself a
    # reliable signal that the value is a missing-value sentinel.
    #
    # The self-comparison below is deliberate, not a typo. It is the only NaN
    # test that also works for numpy.float32, Decimal("NaN") and pandas
    # sentinels, none of which math.isnan accepts. If the Pylint ruleset is ever
    # enabled, this line needs `# noqa: PLR0124` — it is omitted now because an
    # unused noqa is itself a lint error under RUF100.
    try:
        if value != value:
            return True
    except TypeError:
        return True

    if isinstance(value, str) and value.strip().lower() in _MISSING_TOKENS:
        return True

    return False


def safe_float(
    value: Any,
    default: float = 0.0,
    *,
    allow_infinite: bool = False,
) -> float:
    """
    Coerce ``value`` to a finite float, returning ``default`` on failure.

    Infinity is rejected by default. This matters for real inputs: a
    scikit-learn decision score of ``-inf`` would otherwise propagate into a
    risk score and then into JSON, where ``Infinity`` is not valid and would
    break the API contract.

    >>> safe_float("42.5")
    42.5
    >>> safe_float(None)
    0.0
    >>> safe_float(float("nan"), default=-1.0)
    -1.0
    >>> safe_float(float("inf"))
    0.0
    """
    if is_missing(value):
        return default

    if isinstance(value, bool):
        # bool is a subclass of int; coercing it silently is almost always a
        # bug, so it is handled explicitly rather than by accident.
        return 1.0 if value else 0.0

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default

    if math.isnan(result):
        return default

    if math.isinf(result) and not allow_infinite:
        return default

    return result


def safe_int(value: Any, default: int = 0) -> int:
    """
    Coerce ``value`` to an int, returning ``default`` on failure.

    Routed through :func:`safe_float` so that NaN, infinity and numeric
    strings such as ``"12.0"`` are all handled — ``int("12.0")`` raises
    ``ValueError``, which is the defect present in ``logger._safe_int``.

    Truncates toward zero, matching the existing behaviour.

    >>> safe_int("12.7")
    12
    >>> safe_int("not a number", default=-1)
    -1
    >>> safe_int(float("nan"))
    0
    """
    if is_missing(value):
        return default

    if isinstance(value, bool):
        return 1 if value else 0

    if isinstance(value, int):
        return value

    numeric = safe_float(value, default=float("nan"))
    if math.isnan(numeric):
        return default

    try:
        return int(numeric)
    except (TypeError, ValueError, OverflowError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Coerce ``value`` to a bool, returning ``default`` on failure.

    Text is interpreted by token rather than by Python truthiness, because
    ``bool("False")`` is ``True`` — a trap when reading booleans back from a
    CSV or an environment variable.

    >>> safe_bool("false")
    False
    >>> safe_bool("yes")
    True
    >>> safe_bool("maybe", default=True)
    True
    """
    if is_missing(value):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        numeric = safe_float(value, default=float("nan"))
        if math.isnan(numeric):
            return default
        return numeric != 0.0

    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
        return default

    return default


def strip_control_characters(text: str, replacement: str = "") -> str:
    """
    Remove C0 and C1 control characters, preserving ordinary whitespace.

    This is a real defence, not hygiene theatre. AURA writes OS-supplied
    process names into log files, and a process named with an embedded CRLF
    could forge additional log lines — log injection that could be used to
    hide activity from an analyst reading the log. Tab, newline and carriage
    return are stripped here too; callers that legitimately need multi-line
    text should not route it through this function.

    Unicode category ``Cc`` covers C0 and C1 controls. ``Cf`` (format
    characters) is also removed because it includes the bidirectional
    override characters used to make text render in an order different from
    its byte order — the basis of filename-spoofing attacks.
    """
    if not text:
        return text
    return "".join(
        replacement if unicodedata.category(char) in {"Cc", "Cf"} else char
        for char in text
    )


def safe_text(
    value: Any,
    default: str = "",
    *,
    max_length: int | None = 512,
    allow_control_characters: bool = False,
) -> str:
    """
    Coerce ``value`` to a clean, bounded string.

    Control characters are stripped and the result is truncated, because the
    input may be an OS-supplied process name or file path of unbounded length
    and uncontrolled content.

    >>> safe_text(None, default="UNKNOWN")
    'UNKNOWN'
    >>> safe_text("chrome.exe\\r\\nFAKE LOG LINE")
    'chrome.exeFAKE LOG LINE'
    >>> safe_text("x" * 20, max_length=10)
    'xxxxxxx...'
    """
    if is_missing(value):
        return default

    if isinstance(value, str):
        text = value
    else:
        try:
            text = str(value)
        except Exception:  # noqa: BLE001 - __str__ on foreign objects can raise anything
            return default

    if not allow_control_characters:
        text = strip_control_characters(text)

    text = text.strip()
    if not text:
        return default

    if max_length is not None and len(text) > max_length:
        if max_length <= 3:
            return text[:max_length]
        return text[: max_length - 3] + "..."

    return text


def clamp(value: _NumberT, minimum: _NumberT, maximum: _NumberT) -> _NumberT:
    """
    Constrain ``value`` to the inclusive range ``[minimum, maximum]``.

    Used wherever a computed score must stay inside its declared domain. Note
    that clamping hides magnitude: the stored log contains
    ``LOF_Score=-114.4696`` clamped to an intensity of ``100.0``, which is why
    the audit flags the LOF normalisation itself as unsound. Clamping is the
    correct final guard, not a substitute for a bounded transform.

    >>> clamp(150, 0, 100)
    100
    >>> clamp(-5.0, 0.0, 100.0)
    0.0
    """
    if minimum > maximum:
        raise ValueError(f"clamp minimum {minimum!r} exceeds maximum {maximum!r}")
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value
