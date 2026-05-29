"""Number reconciliation: equivalence of spoken and written numeric forms."""

from __future__ import annotations

from airwer.numbers import reconcile


def test_digit_run_to_spoken():
    assert reconcile("250") == "two five zero"


def test_leading_zero_preserved():
    # The int("010") collapse bug: a digit run is a sequence, never an int.
    assert reconcile("010") == "zero one zero"
    assert reconcile("fly 010") == "fly zero one zero"


def test_digit_words_kept_as_sequence():
    assert reconcile("two one zero") == "two one zero"


def test_atc_pronunciation_variants():
    assert reconcile("niner tree fife") == "nine three five"
    assert reconcile("fower") == "four"


def test_composite_hundred():
    assert reconcile("two hundred") == "two zero zero"
    assert reconcile("200") == "two zero zero"


def test_round_ten_thousand_matches_digits():
    # The "one zero thousand" != "ten thousand" bug.
    assert reconcile("ten thousand") == reconcile("10000")
    assert reconcile("ten thousand") == "one zero zero zero zero"


def test_thousand_five_hundred():
    assert reconcile("two thousand five hundred") == "two five zero zero"
    assert reconcile("2500") == "two five zero zero"


def test_and_connector_inside_composite():
    assert reconcile("two thousand and five hundred") == "two five zero zero"


def test_scale_anchored_tens_and_units():
    # With an explicit scale word the value is unambiguous and folds.
    assert reconcile("two hundred fifty") == "two five zero"
    assert reconcile("twenty five hundred") == "two five zero zero"


def test_colloquial_scaleless_composite_not_evaluated():
    # "two fifty" is ambiguous (250 vs 2/50) -> left as words, never summed to 52.
    assert reconcile("two fifty") == "two fifty"
    assert reconcile("one twenty") == "one twenty"
    assert reconcile("twenty five") == "twenty five"


def test_leading_zero_not_dropped_by_a_tens_word():
    # A teen/tens word must not route a literal leading zero through int().
    assert reconcile("zero ten") == "zero ten"


def test_leading_weak_oh_folds_when_run_has_a_strong_token():
    assert reconcile("oh oh seven") == "zero zero seven"
    assert reconcile("seven oh oh") == "seven zero zero"


def test_flight_level_prefix_expands():
    assert reconcile("fl250") == "flight level two five zero"
    assert reconcile("fl 250") == "flight level two five zero"


def test_flight_level_spelled_matches_abbreviated():
    # The FL-spelled bug: "flight level one hundred" vs "FL100".
    assert reconcile("flight level one hundred") == reconcile("flight level 100")


def test_frequency_point_and_decimal_and_digits():
    assert reconcile("one one eight decimal one") == "one one eight decimal one"
    assert reconcile("one one eight point one") == "one one eight decimal one"
    assert reconcile("118.1") == "one one eight decimal one"


def test_weak_oh_standalone_is_not_a_number():
    assert reconcile("oh roger") == "oh roger"


def test_weak_oh_inside_run():
    assert reconcile("two oh") == "two zero"


def test_squawk_digits():
    assert reconcile("squawk 7421") == "squawk seven four two one"
    assert reconcile("squawk seven four two one") == "squawk seven four two one"


def test_non_numeric_text_untouched():
    assert reconcile("turn left then contact tower") == "turn left then contact tower"
