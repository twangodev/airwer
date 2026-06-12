"""The normalization pipeline: text -> canonical scored form.

A single ordered pipeline, applied symmetrically to references and hypotheses,
turns raw transcripts into the canonical token string that WER is computed over.
Step order is load-bearing: bracketed annotations and contractions are handled
*before* punctuation is stripped (so ``[unintelligible]`` and ``don't`` resolve
correctly), callsigns are expanded *before* glued letter+digit tokens are split
(so ``DLH123`` reaches the expander intact), and numbers are reconciled
*before* the decimal point is removed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from airwer import vocab
from airwer.config import CANONICAL
from airwer.numbers import reconcile

if TYPE_CHECKING:
    from airwer.config import WerConfig

# annotation spans: [..], (..), <..>
_BRACKET_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|<[^>]*>")
# joining punctuation separates words ("route—approach" is two words, and
# "three-three-seven-four" is four digits) — substituted with a space BEFORE
# the deleting pass below, which would otherwise glue the fragments together
_GLUE_PUNCT_RE = re.compile(r"[-‐‑‒–—―_/]")
# the one hyphenation the vocab spells solid: NATO "x-ray"/"x ray" -> "xray"
_XRAY_RE = re.compile(r"\bx ray\b")
_PUNCT_EXCEPT_DOT = re.compile(r"[^a-z0-9\s.]")
_NON_DECIMAL_DOT_RE = re.compile(r"(?<!\d)\.|\.(?!\d)")
# 2+ dots is no decimal: "1.5.7" / "25.07.2017" are digit groups, not numbers
_MULTI_DOT_RE = re.compile(r"\b\d+(?:\.\d+){2,}\b")
_GLUED_RE = re.compile(r"\b([a-z]+)(\d+)\b")  # "qnh1017" -> "qnh 1017"
# every letter<->digit boundary, both directions: "2606papa" -> "2606 papa",
# "epsilon616mike" -> "epsilon 616 mike" (the letters-then-digits _GLUED_RE
# above remains the callsign-expansion gate; this one does the splitting)
_ALNUM_BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])")
_DOT_RE = re.compile(r"\.")
_WS_RE = re.compile(r"\s+")

_CONTRACTIONS: dict[str, str] = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "won't": "will not", "wouldn't": "would not", "can't": "cannot",
    "couldn't": "could not", "shouldn't": "should not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "it's": "it is", "that's": "that is", "we're": "we are",
    "you're": "you are", "they're": "they are", "i'm": "i am",
    "i'll": "i will", "we'll": "we will", "you'll": "you will",
}  # fmt: skip


def _map_words(text: str, mapping: dict[str, str]) -> str:
    return " ".join(mapping.get(tok, tok) for tok in text.split())


def _drop_words(text: str, words: frozenset[str]) -> str:
    return " ".join(tok for tok in text.split() if tok not in words)


def _expand_contractions(text: str) -> str:
    return " ".join(_CONTRACTIONS.get(tok, tok) for tok in text.split())


def _spell_acronyms(text: str) -> str:
    return " ".join(
        " ".join(tok) if tok in vocab.ACRONYMS else tok for tok in text.split()
    )


def _expand_callsigns(text: str) -> str:
    out: list[str] = []
    for tok in text.split():
        # only alnum codes still carrying a digit (plain words / numbers do not);
        # glued letters+digits expand only on a known operator prefix so codes
        # like "qnh1017" stay eligible for the glued split
        glued = _GLUED_RE.fullmatch(tok)
        if (
            any(c.isdigit() for c in tok)
            and any(c.isalpha() for c in tok)
            and (glued is None or glued.group(1) in vocab.ICAO_TELEPHONY)
        ):
            spoken = vocab.expand_callsign(tok)
            out.append(spoken if spoken is not None else tok)
        else:
            out.append(tok)
    return " ".join(out)


def normalize(text: str, config: WerConfig | None = None) -> str:
    """Normalize ``text`` to its canonical scored form under ``config``.

    >>> normalize("Turn heading two one zero, descend FL250")
    'turn heading two one zero descend flight level two five zero'
    """
    cfg = config if config is not None else CANONICAL
    # NFKD + strip combining marks: accented letters fold to their base
    # ("H\u00f4tel" -> "hotel") instead of being deleted to junk ("htel")
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for apostrophe in ("\u2018", "\u2019", "\u02bc", "\u2032", "\uff07"):
        s = s.replace(apostrophe, "'")
    if cfg.strip_tags:
        s = _BRACKET_RE.sub(" ", s)
    if cfg.expand_contractions:
        s = _expand_contractions(s)
    s = _GLUE_PUNCT_RE.sub(" ", s)
    s = _XRAY_RE.sub("xray", s)
    # delete, not space: "don't" -> "dont", "10,000" -> "10000"
    s = _PUNCT_EXCEPT_DOT.sub("", s)
    # a sentence dot is also a number-run boundary: "270. Three thousand"
    # must not fuse. The sentinel survives the token-wise steps below and is
    # consumed at the reconcile step (or stripped, for configs without it).
    s = _MULTI_DOT_RE.sub(lambda m: m.group(0).replace(".", " "), s)
    s = _NON_DECIMAL_DOT_RE.sub(" \x00 ", s)
    if cfg.strip_fillers:
        s = _drop_words(s, vocab.FILLERS)
    if cfg.fold_nato:
        s = _map_words(s, vocab.NATO_VARIANTS)
    if cfg.expand_callsigns:
        s = _expand_callsigns(s)
    if cfg.split_alnum:
        s = _ALNUM_BOUNDARY_RE.sub(" ", s)
    if cfg.spell_acronyms:
        s = _spell_acronyms(s)
    if cfg.reconcile_numbers:
        s = " ".join(reconcile(chunk) for chunk in s.split("\x00"))
    s = s.replace("\x00", " ")
    if cfg.fold_spelling:
        s = _map_words(s, vocab.SPELLING)
    if cfg.fold_procedure_words:
        s = _map_words(s, vocab.PROCEDURE_SYNONYMS)
    if cfg.drop_function_words:
        s = _drop_words(s, vocab.FUNCTION_WORDS)
    s = _DOT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()
