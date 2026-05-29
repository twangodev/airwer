"""Vocabulary tables and callsign expansion."""

from __future__ import annotations

from airwer import vocab


def test_expand_callsign_airline_prefix():
    assert vocab.expand_callsign("EWG7AB") == "eurowings seven alfa bravo"
    assert vocab.expand_callsign("RYR73AH") == "ryanair seven three alfa hotel"


def test_expand_callsign_registration_spellout():
    assert vocab.expand_callsign("OKLBA") == "oscar kilo lima bravo alfa"


def test_expand_callsign_rejects_bad_input():
    assert vocab.expand_callsign("OK-LBA") is None
    assert vocab.expand_callsign("") is None


def test_nato_alphabet_complete():
    assert len(vocab.NATO) == 26
    assert vocab.NATO["a"] == "alfa"
    assert vocab.NATO["x"] == "xray"
