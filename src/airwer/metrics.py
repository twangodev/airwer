"""WER scoring built on jiwer, with ATC-aware reporting.

The edit-distance and alignment math is jiwer's; this module owns ATC
normalization (applied symmetrically to both sides) and the reporting that the
raw ``jiwer.wer()`` scalar throws away:

* substitution / insertion / deletion / hit counts (via ``jiwer.process_words``),
  so a substituted altitude digit is distinguishable from a deleted filler;
* **bounded** per-utterance statistics: per-utterance WER is unbounded
  (a hallucinated repeat against a short reference can exceed 1.0 by a lot), so
  the headline distribution uses values clamped to ``[0, 1]`` while ``wer_max``
  and ``n_runaway`` preserve the raw signal;
* a numeric-only WER over the safety-critical digit content;
* a normalization *ladder* showing each rung's marginal effect.

Empty-reference utterances cannot be scored by WER (division by zero reference
length); they are excluded from the corpus metric and counted in
``n_empty_ref``.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING

import jiwer

from airwer.config import CANONICAL, RAW, SEMANTIC
from airwer.normalize import normalize
from airwer.numbers import NUMERIC_TOKENS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from airwer.config import WerConfig

_WORDS_TR = jiwer.Compose(
    [jiwer.RemoveMultipleSpaces(), jiwer.Strip(), jiwer.ReduceToListOfListOfWords()]
)
_CHARS_TR = jiwer.Compose(
    [jiwer.RemoveMultipleSpaces(), jiwer.Strip(), jiwer.ReduceToListOfListOfChars()]
)


@dataclass(frozen=True)
class WerResult:
    """Scored result for a reference/hypothesis corpus."""

    wer: float
    """Corpus WER (jiwer's reference-length-weighted aggregate)."""
    cer: float
    """Corpus character error rate."""
    numeric_wer: float
    """WER over numeric content only (digit words + the decimal marker);
    ``nan`` when no reference utterance has any numeric content."""
    hits: int
    substitutions: int
    insertions: int
    deletions: int
    n: int
    """Total utterances."""
    n_scored: int
    """Utterances with a non-empty reference (those in the corpus WER)."""
    n_empty_ref: int
    """Utterances dropped from corpus WER because the reference normalized empty."""
    wer_mean: float
    """Mean of per-utterance WER, each clamped to ``[0, 1]``."""
    wer_median: float
    wer_p90: float
    wer_max: float
    """Maximum *raw* (unclamped) per-utterance WER; exposes runaways."""
    n_runaway: int
    """Count of utterances whose raw per-utterance WER exceeds 1.0."""
    per_utt: tuple[float, ...]
    """Per-utterance WER, clamped to ``[0, 1]``, in input order."""


def _as_list(x: str | Sequence[str]) -> list[str]:
    return [x] if isinstance(x, str) else list(x)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo))


def _utt_wer(ref: str, hyp: str) -> float:
    """Raw (unbounded) per-utterance WER. Empty ref -> insertion count."""
    if not ref:
        return 0.0 if not hyp else float(len(hyp.split()))
    return float(
        jiwer.wer(
            ref, hyp, reference_transform=_WORDS_TR, hypothesis_transform=_WORDS_TR
        )
    )


def _numeric_only(text: str) -> str:
    return " ".join(tok for tok in text.split() if tok in NUMERIC_TOKENS)


def process(
    reference: str | Sequence[str],
    hypothesis: str | Sequence[str],
    config: WerConfig | None = None,
) -> WerResult:
    """Normalize and score a reference/hypothesis corpus.

    Accepts a single string pair or two equal-length sequences.
    """
    cfg = config if config is not None else CANONICAL
    refs = _as_list(reference)
    hyps = _as_list(hypothesis)
    if len(refs) != len(hyps):
        msg = f"reference/hypothesis length mismatch: {len(refs)} != {len(hyps)}"
        raise ValueError(msg)
    if not refs:
        msg = "empty input: at least one reference/hypothesis pair is required"
        raise ValueError(msg)

    nrefs = [normalize(r, cfg) for r in refs]
    nhyps = [normalize(h, cfg) for h in hyps]

    scored = [(r, h) for r, h in zip(nrefs, nhyps) if r]
    n_empty = len(nrefs) - len(scored)
    if scored:
        sr = [r for r, _ in scored]
        sh = [h for _, h in scored]
        words = jiwer.process_words(
            sr, sh, reference_transform=_WORDS_TR, hypothesis_transform=_WORDS_TR
        )
        wer = float(words.wer)
        hits, subs = words.hits, words.substitutions
        ins, dels = words.insertions, words.deletions
        cer = float(
            jiwer.cer(
                sr, sh, reference_transform=_CHARS_TR, hypothesis_transform=_CHARS_TR
            )
        )
    else:
        wer = cer = float("nan")
        hits = subs = ins = dels = 0

    per_raw = [_utt_wer(r, h) for r, h in zip(nrefs, nhyps)]
    per_bounded = [min(1.0, x) for x in per_raw]

    num_pairs = [
        (_numeric_only(r), _numeric_only(h))
        for r, h in zip(nrefs, nhyps)
        if _numeric_only(r)
    ]
    if num_pairs:
        numeric_wer = float(
            jiwer.wer(
                [r for r, _ in num_pairs],
                [h for _, h in num_pairs],
                reference_transform=_WORDS_TR,
                hypothesis_transform=_WORDS_TR,
            )
        )
    else:
        numeric_wer = float("nan")

    return WerResult(
        wer=wer,
        cer=cer,
        numeric_wer=numeric_wer,
        hits=hits,
        substitutions=subs,
        insertions=ins,
        deletions=dels,
        n=len(refs),
        n_scored=len(scored),
        n_empty_ref=n_empty,
        wer_mean=statistics.mean(per_bounded),
        wer_median=statistics.median(per_bounded),
        wer_p90=_percentile(per_bounded, 90),
        wer_max=max(per_raw),
        n_runaway=sum(1 for x in per_raw if x > 1.0),
        per_utt=tuple(per_bounded),
    )


def wer(
    reference: str | Sequence[str],
    hypothesis: str | Sequence[str],
    config: WerConfig | None = None,
) -> float:
    """Corpus WER under the default CANONICAL profile, or ``config`` if given.

    When EVERY reference normalizes empty there is nothing to score against:
    matching jiwer's scalar semantics, the result is 1.0 if any hypothesis
    has content and 0.0 if the hypotheses are empty too (never NaN).
    """
    result = process(reference, hypothesis, config)
    if math.isnan(result.wer) and result.n_scored == 0 and result.n > 0:
        return _all_empty_ref_score(hypothesis, config)
    return result.wer


def _all_empty_ref_score(
    hypothesis: str | Sequence[str], config: WerConfig | None
) -> float:
    hyps = [hypothesis] if isinstance(hypothesis, str) else list(hypothesis)
    return 1.0 if any(normalize(h, config).strip() for h in hyps) else 0.0


def agreement(a: str, b: str, config: WerConfig | None = None) -> float:
    """Symmetric agreement between two transcripts, in ``[0, 1]`` (``1`` = identical).

    Neither side is a privileged reference: the score is the word edit distance
    normalized by the longer side, so it is symmetric and bounded. Defined for
    empties: two blanks agree (``1.0``), one blank against real words does not
    (``0.0``), which makes it safe for model-vs-model voting, where :func:`wer`
    would divide by an empty reference and return ``nan``.
    """
    cfg = config if config is not None else CANONICAL
    na, nb = normalize(a, cfg), normalize(b, cfg)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    words = jiwer.process_words(
        na, nb, reference_transform=_WORDS_TR, hypothesis_transform=_WORDS_TR
    )
    edits = words.substitutions + words.insertions + words.deletions
    longer = max(
        words.hits + words.substitutions + words.deletions,
        words.hits + words.substitutions + words.insertions,
    )
    return 1.0 - min(1.0, edits / longer)


def cer(
    reference: str | Sequence[str],
    hypothesis: str | Sequence[str],
    config: WerConfig | None = None,
) -> float:
    """Corpus character error rate under the default CANONICAL profile, or ``config``.

    Same empty-reference semantics as :func:`wer` (1.0/0.0, never NaN).
    """
    result = process(reference, hypothesis, config)
    if math.isnan(result.cer) and result.n_scored == 0 and result.n > 0:
        return _all_empty_ref_score(hypothesis, config)
    return result.cer


def numeric_wer(
    reference: str | Sequence[str],
    hypothesis: str | Sequence[str],
    config: WerConfig | None = None,
) -> float:
    """WER over numeric content only (safety-critical digits), under the default
    CANONICAL profile or ``config``. ``nan`` if no reference has numeric content."""
    return process(reference, hypothesis, config).numeric_wer


_LADDER: list[tuple[str, WerConfig]] = [
    ("raw", RAW),
    ("+tags+fillers", RAW.replace(strip_tags=True, strip_fillers=True)),
    ("+nato", RAW.replace(strip_tags=True, strip_fillers=True, fold_nato=True)),
    ("canonical", CANONICAL),
    ("semantic", SEMANTIC),
]


def ladder(
    reference: str | Sequence[str],
    hypothesis: str | Sequence[str],
) -> list[tuple[str, float]]:
    """Corpus WER at each normalization rung, to separate formatting noise from
    real errors. Walks the fixed RAW -> SEMANTIC rungs and returns
    ``[(rung_name, wer), ...]``."""
    return [(name, process(reference, hypothesis, cfg).wer) for name, cfg in _LADDER]
