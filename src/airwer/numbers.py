"""Number reconciliation: fold every numeric expression to one canonical form.

``airwer`` scores numbers by *equivalence class* rather than by spelling
direction. Both spoken (``two five zero``, ``flight level two five zero``) and
written (``250``, ``FL250``) forms reduce to the SAME canonical token sequence,
so equivalent readouts never count as errors while genuine value differences
still do.

Canonical form: every number becomes its digit string read out digit-by-digit
in canonical digit words (``two five zero``). Digit *runs* keep their literal
digits, so leading zeros survive (``010`` -> ``zero one zero``); magnitude
composites are evaluated to an integer first (``ten thousand`` -> ``10000`` ->
``one zero zero zero zero``; ``flight level one hundred`` -> ``flight level one
zero zero``). Decimals split on a canonical ``decimal`` marker (``118.1`` and
``one one eight point one`` both -> ``one one eight decimal one``).

This deterministic, both-sides-symmetric mapping is what removes the
digit-spelling mismatch without the bugs of a one-directional expander
(``FL100`` vs spelled ``flight level one hundred``; ``10000`` vs ``ten
thousand``; the ``int("010")`` leading-zero collapse).

Deliberate limitation: a scale-less run that mixes digits with tens/teen words
("two fifty", "twenty five", "zero ten") is ambiguous between a value and a
digit readout, so it is left as words rather than evaluated. This keeps the
metric safe (no false equivalence, no dropped leading zero) at the cost of not
folding such colloquial composites; spelled forms with an explicit scale word
("two fifty" written as "two hundred fifty") do fold.
"""

from __future__ import annotations

import re

CANONICAL_DIGIT: dict[str, str] = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}  # fmt: skip

_DIGIT_WORD: dict[str, str] = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "niner": "9", "tree": "3", "fife": "5", "fower": "4",
}  # fmt: skip

# "oh"/"o" = zero, but only inside a number run (see _take_run)
_WEAK_DIGIT: dict[str, str] = {"oh": "0", "o": "0"}

_TEENS: dict[str, int] = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
_TENS: dict[str, int] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_SCALE: dict[str, int] = {"hundred": 100, "thousand": 1000, "million": 1_000_000}

_DECIMAL_WORDS: frozenset[str] = frozenset({"point", "decimal"})
_CARDINAL_WORDS: frozenset[str] = (
    frozenset(_TEENS) | frozenset(_TENS) | frozenset(_SCALE)
)
# a run needs at least one of these to count as a number
_STRONG_WORDS: frozenset[str] = frozenset(_DIGIT_WORD) | _CARDINAL_WORDS

_DIGITS_RE = re.compile(r"^\d+$")
_DECIMAL_RE = re.compile(r"^\d+\.\d+$")
# "FL250" / "FL 250" -> "flight level 250" so it folds like the spoken form.
_FL_RE = re.compile(r"\bfl\s*(\d{2,3})\b")

NUMERIC_TOKENS: frozenset[str] = frozenset(CANONICAL_DIGIT.values()) | {"decimal"}


def _is_number_token(tok: str, *, strong_only: bool = False) -> bool:
    if _DIGITS_RE.match(tok) or _DECIMAL_RE.match(tok):
        return True
    if tok in _STRONG_WORDS or tok in _DECIMAL_WORDS:
        return True
    return not strong_only and tok in _WEAK_DIGIT


def _take_run(tokens: list[str], start: int) -> tuple[list[str] | None, int]:
    """Collect a maximal number run beginning at ``start``.

    Returns ``(run, next_index)``, or ``(None, start)`` when ``tokens[start]``
    does not begin a number. ``and`` is consumed as a connector only between
    numeric tokens (``two thousand and five hundred``).
    """
    if not _is_number_token(tokens[start]):
        return None, start
    run: list[str] = []
    j = start
    n = len(tokens)
    while j < n:
        tok = tokens[j]
        if _is_number_token(tok):
            run.append(tok)
            j += 1
        elif (
            tok == "and"
            and run
            and j + 1 < n
            and _is_number_token(tokens[j + 1], strong_only=True)
        ):
            j += 1  # drop the connector
        else:
            break
    # drop a dangling decimal marker ("two point")
    while run and run[-1] in _DECIMAL_WORDS:
        run.pop()
    # reject a weak-only run (a lone "oh") that the weak start admitted
    if not any(_is_number_token(t, strong_only=True) for t in run):
        return None, start
    return run, j


def _parse_cardinal(seg: list[str]) -> int:
    """Evaluate a token segment containing magnitude/teen/tens words to an int."""
    total = 0
    current = 0
    for tok in seg:
        if tok in _DIGIT_WORD:
            current += int(_DIGIT_WORD[tok])
        elif tok in _WEAK_DIGIT:
            current += int(_WEAK_DIGIT[tok])
        elif _DIGITS_RE.match(tok):
            current += int(tok)
        elif tok in _TEENS:
            current += _TEENS[tok]
        elif tok in _TENS:
            current += _TENS[tok]
        elif tok in _SCALE:
            scale = _SCALE[tok]
            if current == 0:
                current = 1
            if scale == 100:
                current *= 100
            else:
                total += current * scale
                current = 0
    return total + current


def _has_scale(seg: list[str]) -> bool:
    return any(tok in _SCALE for tok in seg)


def _all_digit_tokens(seg: list[str]) -> bool:
    return all(
        _DIGITS_RE.match(tok) or tok in _DIGIT_WORD or tok in _WEAK_DIGIT for tok in seg
    )


def _digit_chars(seg: list[str]) -> str:
    chars: list[str] = []
    for tok in seg:
        if _DIGITS_RE.match(tok):
            chars.append(tok)  # literal digits, leading zeros preserved
        elif tok in _DIGIT_WORD:
            chars.append(_DIGIT_WORD[tok])
        else:
            chars.append(_WEAK_DIGIT[tok])
    return "".join(chars)


def _segment_to_tokens(seg: list[str]) -> list[str]:
    """Canonical tokens for one decimal-free segment.

    * scale composite ("ten thousand", "two hundred fifty") -> evaluate to an
      int, then render digit-by-digit;
    * pure digit sequence ("two one zero", "010") -> digit-by-digit, literal
      digits preserved;
    * ambiguous scale-less tens/teens run ("two fifty", "twenty five") -> NOT
      evaluated (that would risk both false matches and dropped leading zeros);
      single-digit parts are folded, tens/teen words kept verbatim.
    """
    if not seg:
        return []
    if _has_scale(seg):
        return _spoken(str(_parse_cardinal(seg))).split()
    if _all_digit_tokens(seg):
        return _spoken(_digit_chars(seg)).split()
    out: list[str] = []
    for tok in seg:
        if _DIGITS_RE.match(tok):
            out.extend(_spoken(tok).split())
        elif tok in _DIGIT_WORD:
            out.append(CANONICAL_DIGIT[_DIGIT_WORD[tok]])
        else:
            out.append(tok)
    return out


def _spoken(digit_str: str) -> str:
    return " ".join(CANONICAL_DIGIT[c] for c in digit_str)


def _canonicalize(run: list[str]) -> list[str]:
    """Map one number run to its canonical spoken-digit tokens."""
    segments: list[list[str]] = [[]]
    for tok in run:
        if tok in _DECIMAL_WORDS:
            segments.append([])
        elif _DECIMAL_RE.match(tok):
            int_part, frac = tok.split(".")
            segments[-1].append(int_part)
            segments.append([frac])
        else:
            segments[-1].append(tok)
    rendered = [_segment_to_tokens(seg) for seg in segments]
    nonempty = [r for r in rendered if r]
    if not nonempty:
        return []
    if len(segments) == 1:
        return rendered[0]
    out: list[str] = []
    for i, part in enumerate(nonempty):
        if i:
            out.append("decimal")
        out.extend(part)
    return out


def reconcile(text: str) -> str:
    """Fold every number in ``text`` to its canonical spoken-digit form."""
    text = _FL_RE.sub(lambda m: "flight level " + m.group(1), text)
    tokens = text.split()
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        run, j = _take_run(tokens, i)
        if run is None:
            out.append(tokens[i])
            i += 1
        else:
            out.extend(_canonicalize(run))
            i = j
    return " ".join(out)
