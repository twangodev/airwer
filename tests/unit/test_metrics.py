"""Scoring: equivalence, the verified bug regressions, and reporting."""

from __future__ import annotations

import math

import pytest

import airwer
from airwer import profiles


def test_equivalent_readouts_score_zero():
    assert airwer.wer("descend flight level two five zero", "descend FL250") == 0.0
    assert (
        airwer.wer("contact tower one one eight decimal one", "contact tower 118.1")
        == 0.0
    )
    assert airwer.wer("cleared alfa bravo", "cleared alpha bravo") == 0.0


def test_agreement_equivalent_readouts_is_one():
    assert (
        airwer.agreement("descend FL250", "descend flight level two five zero") == 1.0
    )


def test_agreement_both_blank_is_one():
    assert airwer.agreement("", "") == 1.0
    assert airwer.agreement("uh", "") == 1.0


def test_agreement_blank_vs_text_is_zero():
    assert airwer.agreement("", "cleared to land") == 0.0
    assert airwer.agreement("cleared to land", "") == 0.0


def test_agreement_is_symmetric():
    a, b = "turn heading two one zero", "turn heading 220"
    assert airwer.agreement(a, b) == airwer.agreement(b, a)


def test_agreement_partial_is_between_zero_and_one():
    score = airwer.agreement(
        "brickyard four niner six descend", "skyhawk four nine six climb"
    )
    assert 0.0 < score < 1.0


def test_genuine_error_is_kept():
    assert airwer.wer("turn heading two one zero", "turn heading 220") > 0.0


def test_flight_level_spelled_bug_fixed():
    assert airwer.wer("flight level one hundred", "FL100") == 0.0


def test_round_ten_thousand_bug_fixed():
    assert airwer.wer("climb maintain ten thousand", "climb maintain 10000") == 0.0


def test_leading_zero_bug_fixed():
    assert airwer.wer("fly zero one zero", "fly 010") == 0.0


def test_colloquial_cardinal_not_falsely_equal():
    # Regression: "two fifty" must NOT be declared equal to "five two" (was 52).
    assert airwer.wer("two fifty", "five two") > 0.0
    assert airwer.wer("two fifty", "two fifty") == 0.0


def test_and_separated_numbers_not_falsely_equal():
    # Regression: "two and three thousand" must not fuse to 5000.
    assert airwer.wer("between two and three thousand", "between 5000") > 0.0
    assert airwer.wer("two thousand and five hundred", "2500") == 0.0


def test_dangling_point_not_silently_deleted():
    # Regression: a trailing or leading "point" is a literal word, not a deletion.
    assert airwer.wer("hold at point two", "hold at two") > 0.0
    assert airwer.wer("at gate two point", "at gate two") > 0.0


def test_different_squawk_with_leading_zero_not_equal():
    # Regression: a leading zero must not be collapsed by a following tens word.
    assert airwer.wer("squawk zero ten", "squawk one zero") > 0.0


def test_filler_removal_scores_zero():
    assert airwer.wer("uh turn right", "turn right") == 0.0


def test_solid_vs_spelled_acronym_equal():
    assert airwer.wer("cleared ils approach", "cleared i l s approach") == 0.0
    assert airwer.wer("qnh1017", "q n h one zero one seven") == 0.0


def test_sid_breakdown():
    r = airwer.process(["turn left", "descend now"], ["turn right", "descend now"])
    assert r.substitutions == 1
    assert r.hits == 3
    assert r.insertions == 0
    assert r.deletions == 0
    assert r.n == 2
    assert r.n_scored == 2


def test_per_utterance_wer_is_bounded_but_runaway_is_visible():
    r = airwer.process(["roger"], ["roger roger roger roger roger"])
    assert r.per_utt[0] == 1.0  # clamped to [0, 1]
    assert r.n_runaway == 1
    assert r.wer_max == 4.0  # raw signal preserved


def test_empty_reference_excluded_from_corpus():
    r = airwer.process(["", "cleared to land"], ["noise", "cleared to land"])
    assert r.n_empty_ref == 1
    assert r.n_scored == 1
    assert r.wer == 0.0


def test_numeric_only_wer():
    r = airwer.process("heading two one zero descend", "heading two one five descend")
    assert math.isclose(r.numeric_wer, 1 / 3, rel_tol=1e-9)


def test_ladder_rungs_and_monotonic_fold():
    rungs = airwer.ladder(["cleared alfa"], ["cleared alpha"])
    assert [name for name, _ in rungs] == [
        "raw",
        "+tags+fillers",
        "+nato",
        "canonical",
        "semantic",
    ]
    assert rungs[0][1] > 0.0  # raw: alfa != alpha
    assert rungs[2][1] == 0.0  # +nato folds them equal


def test_accepts_string_or_sequence():
    assert airwer.wer("a b c", "a b c") == 0.0
    assert airwer.wer(["a b c"], ["a b c"]) == 0.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError, match="length mismatch"):
        airwer.process(["a"], ["a", "b"])


def test_empty_input_raises():
    with pytest.raises(ValueError, match="empty input"):
        airwer.process([], [])


def test_semantic_callsign_expansion_scores_zero():
    assert airwer.wer("lufthansa one two three", "DLH123", profiles.SEMANTIC) == 0.0


def test_semantic_profile_changes_score():
    # "affirmative" vs "affirm" is a substitution under canonical, equal under semantic.
    assert airwer.wer("affirmative", "affirm") > 0.0
    assert airwer.wer("affirmative", "affirm", profiles.SEMANTIC) == 0.0


def test_scalar_wer_on_empty_normalizing_reference():
    # jiwer-compatible scalar semantics instead of a silent NaN
    assert airwer.wer("", "descend and maintain") == 1.0
    assert airwer.wer("uh", "descend") == 1.0  # filler-only ref normalizes empty
    assert airwer.wer("", "") == 0.0
    assert airwer.wer("uh", "um") == 0.0  # both sides normalize empty
    assert airwer.cer("", "descend") == 1.0
