"""Canonical Air Traffic Control vocabulary and equivalence data.

Single source of truth for the spoken-form vocabulary that ``airwer`` folds to
canonical representatives during scoring: the NATO/ICAO phonetic alphabet (and
its common spelling variants), radiotelephony fillers, procedure-word synonyms,
British/American spelling pairs, and the ICAO operator -> telephony map used for
optional callsign expansion.

Numeric vocabulary (digit words, ATC variants such as ``niner``/``tree``/
``fife``, magnitude words) lives in :mod:`airwer.numbers`.
"""

from __future__ import annotations

import re

# hyphenless ("xray") so they survive punctuation stripping
NATO: dict[str, str] = {
    "a": "alfa", "b": "bravo", "c": "charlie", "d": "delta", "e": "echo",
    "f": "foxtrot", "g": "golf", "h": "hotel", "i": "india", "j": "juliett",
    "k": "kilo", "l": "lima", "m": "mike", "n": "november", "o": "oscar",
    "p": "papa", "q": "quebec", "r": "romeo", "s": "sierra", "t": "tango",
    "u": "uniform", "v": "victor", "w": "whiskey", "x": "xray",
    "y": "yankee", "z": "zulu",
}  # fmt: skip

# folded so alfa/alpha, juliett/juliet, whiskey/whisky are not scored as errors
NATO_VARIANTS: dict[str, str] = {
    "alpha": "alfa",
    "juliet": "juliett",
    "whisky": "whiskey",
}

FILLERS: frozenset[str] = frozenset({
    "uh", "uhh", "uhm", "um", "umm", "er", "err", "erm",
    "ah", "ahh", "eh", "hmm", "hm", "mm", "mmm", "mhm",
})  # fmt: skip

# letter-acronyms voiced (and transcribed) letter-by-letter; spelled on both
# sides so a solid "ils" matches a spelled "i l s"
ACRONYMS: frozenset[str] = frozenset({
    "ils", "qnh", "qfe", "dme", "vor", "ndb", "ifr", "vfr",
    "atis", "rvr", "adf", "rnav", "klm", "ups",
})  # fmt: skip

PROCEDURE_SYNONYMS: dict[str, str] = {
    "affirmative": "affirm",
}

SPELLING: dict[str, str] = {
    "centre": "center",
    "metre": "meter",
    "metres": "meters",
    "manoeuvre": "maneuver",
    "manoeuvring": "maneuvering",
    "kilometre": "kilometer",
    "kilometres": "kilometers",
}

FUNCTION_WORDS: frozenset[str] = frozenset({"the", "a", "an", "and", "to", "of"})

# only high-confidence codes; an unknown prefix falls back to phonetic spelling
ICAO_TELEPHONY: dict[str, str] = {
    "ewg": "eurowings", "ryr": "ryanair", "dlh": "lufthansa", "qtr": "qatari",
    "wzz": "wizz air", "csa": "csa", "tap": "air portugal", "uae": "emirates",
    "afr": "airfrans", "baw": "speedbird", "ezs": "topswiss", "ezy": "easy",
    "pgt": "sunturk", "vlg": "vueling", "swr": "swiss", "aua": "austrian",
    "tra": "transavia", "lot": "lot", "sdr": "sundair", "tvs": "sky travel",
    "bla": "dark blue", "ira": "iranair", "rot": "tarom", "voe": "volotea",
    "ely": "elal", "klm": "klm", "thy": "turkish", "aza": "alitalia",
    "aca": "air canada", "ual": "united", "fin": "finnair", "aal": "american",
    "bti": "air baltic", "sas": "scandinavian", "aee": "aegean", "tui": "tuifly",
    "sxs": "sunexpress", "eju": "alpine", "ram": "royalair maroc",
    "aho": "air hamburg", "etd": "etihad",
}  # fmt: skip

_DIGIT_SPOKEN: dict[str, str] = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}  # fmt: skip
_CODE_RE = re.compile(r"^[a-z0-9]+$")


def _spell(chars: str) -> str | None:
    """Spell a run of letters/digits phonetically; None on any other char."""
    out: list[str] = []
    for ch in chars:
        if ch in NATO:
            out.append(NATO[ch])
        elif ch in _DIGIT_SPOKEN:
            out.append(_DIGIT_SPOKEN[ch])
        else:
            return None
    return " ".join(out) if out else None


def expand_callsign(code: str) -> str | None:
    """Expand a single callsign/registration code to its spoken form.

    Returns a lowercased spoken phrase, or ``None`` if the code is empty or
    contains characters that cannot be voiced.

    >>> expand_callsign("EWG7AB")
    'eurowings seven alfa bravo'
    >>> expand_callsign("OKLBA")
    'oscar kilo lima bravo alfa'
    """
    if not code:
        return None
    code = code.strip().lower()
    if not _CODE_RE.match(code):
        return None
    m = re.match(r"^([a-z]{1,3})(.*)$", code)
    if m:
        prefix, rest = m.group(1), m.group(2)
        if prefix in ICAO_TELEPHONY and rest:
            spoken_rest = _spell(rest)
            if spoken_rest is not None:
                return f"{ICAO_TELEPHONY[prefix]} {spoken_rest}"
    return _spell(code)
