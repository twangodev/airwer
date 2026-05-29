"""Built-in normalization profiles.

Convenience re-exports of the ready-made :class:`~airwer.config.WerConfig`
instances so callers can write ``airwer.profiles.CANONICAL``.
"""

from __future__ import annotations

from airwer.config import CANONICAL, RAW, SEMANTIC

__all__ = ["CANONICAL", "RAW", "SEMANTIC"]
