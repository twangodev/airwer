"""Normalization configuration and built-in profiles.

A :class:`WerConfig` is an immutable set of toggles, each enabling one
normalization dimension. Content-neutral dimensions (that can only ever remove
spurious, formatting-only errors) default to ON; opinionated dimensions (that
could mask a genuine difference) default to OFF and are enabled by the
``SEMANTIC`` profile.

Normalization always lowercases, strips bracketed/non-speech annotations'
delimiters, and removes punctuation; those are unconditional and not toggles.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class WerConfig:
    """Which normalization dimensions to apply before scoring.

    Default (the ``CANONICAL`` profile) enables only content-neutral folds.
    """

    strip_tags: bool = True
    """Remove bracketed/parenthesized/angled spans, e.g. ``[unintelligible]``,
    ``(noise)``, ``<unk>``, and cut-off-word fragments like ``heading(-ding)``."""

    strip_fillers: bool = True
    """Drop radiotelephony fillers/hesitations (``uh``, ``um``, ``er`` ...)."""

    fold_nato: bool = True
    """Fold NATO phonetic spelling variants to one form (``alpha`` -> ``alfa``,
    ``juliet`` -> ``juliett``)."""

    reconcile_numbers: bool = True
    """Fold every numeric expression to one canonical digit-by-digit form, so
    spoken and written readouts compare equal (``two five zero`` == ``250``,
    ``flight level two five zero`` == ``FL250``, ``one one eight decimal one``
    == ``118.1``)."""

    split_alnum: bool = True
    """Split glued letter+digit tokens (``qnh1017`` -> ``qnh 1017``,
    ``runway25`` -> ``runway 25``) so context words and numbers fold separately."""

    spell_acronyms: bool = True
    """Spell curated ATC letter-acronyms (``ILS``, ``QNH`` ...) letter-by-letter
    so a solid acronym matches its spelled form (``ils`` == ``i l s``)."""

    expand_contractions: bool = False
    """Expand English contractions (``don't`` -> ``do not``)."""

    fold_spelling: bool = False
    """Fold British spelling to American (``centre`` -> ``center``)."""

    fold_procedure_words: bool = False
    """Fold ICAO procedure-word synonyms (``affirmative`` -> ``affirm``)."""

    drop_function_words: bool = False
    """Drop low-information function words (``the``, ``a``, ``and`` ...)."""

    expand_callsigns: bool = False
    """Expand alphanumeric callsign/registration codes to their spoken form
    (``EWG7AB`` -> ``eurowings seven alfa bravo``). Heuristic and lossy."""

    def replace(self, **changes: bool) -> WerConfig:
        """Return a copy with the given toggles overridden."""
        return replace(self, **changes)


#: jiwer-parity baseline: case-fold + punctuation only, no ATC folds.
RAW = WerConfig(
    strip_tags=False,
    strip_fillers=False,
    fold_nato=False,
    reconcile_numbers=False,
    split_alnum=False,
    spell_acronyms=False,
)

#: Default ATC scoring: all content-neutral folds, no opinionated ones.
CANONICAL = WerConfig()

#: Maximum normalization: every dimension on. Use for a "content" WER that
#: ignores formatting, spelling, procedure-word, and function-word differences.
SEMANTIC = WerConfig(
    expand_contractions=True,
    fold_spelling=True,
    fold_procedure_words=True,
    drop_function_words=True,
    expand_callsigns=True,
)
