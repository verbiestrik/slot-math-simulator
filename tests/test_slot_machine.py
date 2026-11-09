"""Tests for the educational slot-machine simulator."""

import pytest

from slot_machine import PAYLINES, REEL_STRIPS, SlotMachine


def test_default_game_has_five_reels_and_twenty_unique_paylines() -> None:
    machine = SlotMachine(seed=1)

    assert len(machine.reels) == 5
    assert len(machine.paylines) == 20
    assert len(set(machine.paylines)) == 20
    assert len(PAYLINES) == 20
    assert all(len(reel) == 12 for reel in REEL_STRIPS)


def test_visible_grid_has_three_rows_and_five_columns() -> None:
    machine = SlotMachine(seed=1)
    result = machine.evaluate_stops((0, 0, 0, 0, 0))

    assert len(result.grid) == 3
    assert all(len(row) == 5 for row in result.grid)


def test_reel_window_wraps_around_at_end_of_strip() -> None:
    machine = SlotMachine(seed=1)
    result = machine.evaluate_stops((11, 11, 11, 11, 11))

    # The first default reel ends in 9, then wraps to A, K.
    assert result.grid[0][0] == "9"
    assert result.grid[1][0] == "A"
    assert result.grid[2][0] == "K"


def test_five_matching_symbols_pay_five_symbol_award() -> None:
    reels = (("A",), ("A",), ("A",), ("A",), ("A",))
    paylines = ((1, 1, 1, 1, 1),)
    paytable = {"A": {3: 10, 4: 20, 5: 50}}
    machine = SlotMachine(reels=reels, paylines=paylines, paytable=paytable)

    result = machine.evaluate_stops((0, 0, 0, 0, 0))

    assert result.total_bet == 1
    assert result.total_payout == 50
    assert len(result.line_wins) == 1
    assert result.line_wins[0].matched_symbols == 5


def test_only_left_to_right_prefix_is_paid() -> None:
    reels = (("A",), ("A",), ("A",), ("K",), ("A",))
    paylines = ((1, 1, 1, 1, 1),)
    paytable = {"A": {3: 10, 4: 20, 5: 50}}
    machine = SlotMachine(reels=reels, paylines=paylines, paytable=paytable)

    result = machine.evaluate_stops((0, 0, 0, 0, 0))

    assert result.total_payout == 10
    assert result.line_wins[0].matched_symbols == 3


def test_non_matching_line_pays_nothing() -> None:
    reels = (("A",), ("K",), ("Q",), ("J",), ("9",))
    paylines = ((1, 1, 1, 1, 1),)
    paytable = {symbol: {3: 10, 4: 20, 5: 50} for symbol in ("A", "K", "Q", "J", "9")}
    machine = SlotMachine(reels=reels, paylines=paylines, paytable=paytable)

    result = machine.evaluate_stops((0, 0, 0, 0, 0))

    assert result.total_payout == 0
    assert result.line_wins == ()


def test_seed_makes_simulations_reproducible() -> None:
    first = SlotMachine(seed=1234).simulate(500)
    second = SlotMachine(seed=1234).simulate(500)

    assert first == second


def test_exact_analysis_of_single_outcome_game() -> None:
    reels = (("A",), ("A",), ("A",), ("A",), ("A",))
    paylines = ((1, 1, 1, 1, 1),)
    paytable = {"A": {3: 10, 4: 20, 5: 50}}
    machine = SlotMachine(reels=reels, paylines=paylines, paytable=paytable)

    metrics = machine.exact_analysis()

    assert metrics.trials == 1
    assert metrics.rtp_percent == 5000
    assert metrics.hit_frequency_percent == 100
    assert metrics.standard_deviation == 0


def test_invalid_spin_count_is_rejected() -> None:
    machine = SlotMachine(seed=1)

    with pytest.raises(ValueError):
        machine.simulate(0)


def test_invalid_reel_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        SlotMachine(reels=(("A",),) * 4)
