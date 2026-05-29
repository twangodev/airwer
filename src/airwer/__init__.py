"""airwer — Word Error Rate for Air Traffic Control, built on jiwer.

A configurable suite of *equivalence-class* normalizations for scoring ATC ASR:
spoken and written readouts of the same callsign, altitude, heading, squawk, or
frequency fold to one canonical form, so formatting differences never count as
errors while genuine value differences still do.

Quickstart::

    import airwer

    airwer.wer("descend flight level two five zero", "descend FL250")  # 0.0
    result = airwer.process(refs, hyps)        # rich: S/I/D, bounded per-utt, numeric WER
    airwer.ladder(refs, hyps)                  # marginal effect of each normalization rung
    airwer.wer(refs, hyps, airwer.profiles.SEMANTIC)
"""

from __future__ import annotations

from airwer import profiles, vocab
from airwer._version import __version__
from airwer.config import WerConfig
from airwer.metrics import WerResult, cer, ladder, numeric_wer, process, wer
from airwer.normalize import normalize

__all__ = [
    "WerConfig",
    "WerResult",
    "__version__",
    "cer",
    "ladder",
    "normalize",
    "numeric_wer",
    "process",
    "profiles",
    "vocab",
    "wer",
]
