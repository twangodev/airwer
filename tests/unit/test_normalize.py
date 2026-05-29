"""End-to-end normalization pipeline behavior."""

from __future__ import annotations

from airwer import normalize, profiles


def test_full_pipeline_flight_level():
    assert normalize("Descend FL250") == "descend flight level two five zero"


def test_tags_removed():
    assert normalize("turn right [unintelligible]") == "turn right"


def test_partial_word_fragment_removed():
    assert normalize("heading(-ding) two one zero") == "heading two one zero"


def test_filler_removed():
    assert normalize("uh turn right") == "turn right"


def test_nato_variant_folded():
    assert normalize("cleared alpha bravo") == "cleared alfa bravo"


def test_punctuation_and_case_neutralized():
    assert normalize("Descend, maintain.") == "descend maintain"


def test_xray_hyphen_stripped():
    assert normalize("hotel x-ray") == "hotel xray"


def test_acronym_spelled_letter_by_letter():
    assert normalize("ILS") == "i l s"
    assert (
        normalize("contact tower QNH 1017") == "contact tower q n h one zero one seven"
    )


def test_glued_alnum_split():
    assert normalize("runway25") == "runway two five"
    assert normalize("QNH1017") == "q n h one zero one seven"


def test_raw_profile_applies_no_atc_folds():
    assert normalize("alpha", profiles.RAW) == "alpha"
    assert normalize("FL250", profiles.RAW) == "fl250"
    assert normalize("ILS", profiles.RAW) == "ils"


def test_semantic_drops_function_words():
    assert normalize("descend to the runway", profiles.SEMANTIC) == "descend runway"


def test_semantic_expands_contraction():
    assert normalize("don't descend", profiles.SEMANTIC) == "do not descend"


def test_semantic_expands_callsign():
    assert normalize("EWG7AB", profiles.SEMANTIC) == "eurowings seven alfa bravo"
