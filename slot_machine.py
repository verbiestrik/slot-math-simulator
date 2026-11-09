"""Educational 5x3 slot-game mathematics simulator.

The game is fully specified by:
- five circular reel strips (weighted probabilites for the symbols 
  "A", "K", "Q", "J", "10", and "9"),
- a set of 20 fixed paylines,
- a paytable for 3, 4, or 5 matching symbols from left to right.

The program reports:
- theoretical RTP, hit frequency, and payout standard deviation by enumerating 
  all possible reel-stop combinations;
- the same statistics estimated through Monte Carlo simulation.

All paytable values are multipliers of the bet placed on one payline.
The default game uses a bet of 1 credit per line, so the total stake is
20 credits per spin.

"""

from __future__ import annotations

import argparse
import itertools
import math
import random
from dataclasses import dataclass
from typing import Sequence


# Each tuple is one circular reel strip. A symbol appearing more often on a
# strip has a greater probability of appearing at a particular visible row.
REEL_STRIPS: tuple[tuple[str, ...], ...] = (
    ("A", "K", "Q", "J", "10", "9", "K", "Q", "J", "10", "9", "9"),
    ("A", "K", "Q", "J", "10", "9", "A", "K", "Q", "J", "10", "9"),
    ("A", "K", "Q", "J", "10", "9", "A", "K", "Q", "J", "10", "9"),
    ("A", "K", "Q", "J", "10", "9", "K", "Q", "J", "10", "9", "9"),
    ("A", "K", "Q", "J", "10", "9", "K", "Q", "J", "10", "9", "9"),
)


# A payline contains one row index (0, 1, or 2) for each of the five reels.
# For example, (1, 1, 1, 1, 1) is the horizontal middle line.
PAYLINES: tuple[tuple[int, ...], ...] = (
    (1, 1, 1, 1, 1),
    (0, 0, 0, 0, 0),
    (2, 2, 2, 2, 2), 
    (0, 1, 2, 1, 0),
    (2, 1, 0, 1, 2),
    (0, 0, 1, 2, 2),
    (2, 2, 1, 0, 0),
    (1, 0, 0, 0, 1),
    (1, 2, 2, 2, 1),
    (0, 1, 1, 1, 0),
    (2, 1, 1, 1, 2),
    (1, 0, 1, 2, 1),
    (1, 2, 1, 0, 1),
    (0, 1, 0, 1, 0),
    (2, 1, 2, 1, 2),
    (0, 0, 1, 1, 2),
    (2, 2, 1, 1, 0),
    (1, 0, 1, 0, 1),
    (1, 2, 1, 2, 1),
    (0, 2, 0, 2, 0),
)


# Payouts per winning combination, expressed as multiples of one credit.
# The values are intentionally chosen to give this toy game an RTP near 95%.
PAYTABLE: dict[str, dict[int, float]] = {
    "A": {3: 37, 4: 146, 5: 730},
    "K": {3: 29, 4: 110, 5: 548},
    "Q": {3: 22, 4: 88, 5: 438},
    "J": {3: 15, 4: 58, 5: 292},
    "10": {3: 15, 4: 44, 5: 219},
    "9": {3: 7, 4: 29, 5: 146},
}


@dataclass(frozen=True)
class LineWin:
    """One winning payline and the payout it produces."""

    line_number: int  # 1-based payline number
    symbol: str
    matched_symbols: int
    payout: float


@dataclass(frozen=True)
class SpinResult:
    """The displayed grid and payout from one spin."""

    grid: tuple[tuple[str, ...], ...]  # three rows, five columns
    stops: tuple[int, ...]
    line_wins: tuple[LineWin, ...]
    total_payout: float
    total_bet: float

    @property
    def net_result(self) -> float:
        """Player's net result: payout minus stake."""
        return self.total_payout - self.total_bet


@dataclass(frozen=True)
class Metrics:
    """Game statistics for either exact analysis or simulated spins.

    standard_deviation is measured in multiples of the total spin stake.
    For example, 2.0 means a standard deviation of two times the total bet.
    """

    trials: int
    total_wagered: float
    total_paid: float
    rtp_percent: float
    hit_frequency_percent: float
    variance: float
    standard_deviation: float
    maximum_payout: float
    maximum_win_multiple: float


class SlotMachine:
    """A configurable 5-reel, 3-row slot game."""

    def __init__(
        self,
        reels: Sequence[Sequence[str]] = REEL_STRIPS,
        paylines: Sequence[Sequence[int]] = PAYLINES,
        paytable: dict[str, dict[int, float]] = PAYTABLE,
        line_bet: float = 1.0,
        seed: int | None = None,
    ) -> None:
        if len(reels) != 5:
            raise ValueError("A 5x3 slot must have exactly five reels.")
        if any(not reel for reel in reels):
            raise ValueError("Every reel strip must contain at least one symbol.")
        if any(not isinstance(symbol, str) or not symbol for reel in reels for symbol in reel):
            raise ValueError("Reel symbols must be non-empty strings.")
        if not paylines:
            raise ValueError("At least one payline is required.")
        if len({tuple(line) for line in paylines}) != len(paylines):
            raise ValueError("Paylines must be unique.")
        for line in paylines:
            if len(line) != 5 or any(row not in (0, 1, 2) for row in line):
                raise ValueError("Each payline must contain five row indices (0, 1, or 2).")
        if not math.isfinite(line_bet) or line_bet <= 0:
            raise ValueError("The bet per line must be a positive finite number.")

        copied_paytable: dict[str, dict[int, float]] = {}
        for symbol, awards in paytable.items():
            copied_awards: dict[int, float] = {}
            for match_count, multiplier in awards.items():
                if match_count not in (3, 4, 5):
                    raise ValueError("Paytable match counts must be 3, 4, or 5.")
                if not math.isfinite(multiplier) or multiplier < 0:
                    raise ValueError("Paytable payouts must be non-negative finite numbers.")
                copied_awards[match_count] = float(multiplier)
            copied_paytable[symbol] = copied_awards

        reel_symbols = {symbol for reel in reels for symbol in reel}
        if not set(copied_paytable).issubset(reel_symbols):
            raise ValueError("Every symbol in the paytable must appear on at least one reel.")

        self.reels = tuple(tuple(reel) for reel in reels)
        self.paylines = tuple(tuple(line) for line in paylines)
        self.paytable = copied_paytable
        self.line_bet = float(line_bet)
        self._rng = random.Random(seed)

    @property
    def total_bet(self) -> float:
        """Total stake per spin across all active paylines."""
        return self.line_bet * len(self.paylines)

    def _grid_from_stops(self, stops: Sequence[int]) -> tuple[tuple[str, ...], ...]:
        """Build the 3x5 visible grid from five reel stop positions."""
        if len(stops) != 5:
            raise ValueError("Exactly five reel stop positions are required.")

        columns: list[tuple[str, ...]] = []
        for reel, stop in zip(self.reels, stops):
            if not isinstance(stop, int) or isinstance(stop, bool):
                raise ValueError("Reel stops must be integers.")
            if not 0 <= stop < len(reel):
                raise ValueError("A reel stop is outside its reel strip.")
            # The modulo operation makes the reel circular: after its last
            # symbol, the visible window continues again from the first one.
            columns.append(tuple(reel[(stop + row) % len(reel)] for row in range(3)))

        # Internally we store rows first: grid[row][reel].
        return tuple(
            tuple(columns[reel_index][row] for reel_index in range(5))
            for row in range(3)
        )

    def evaluate_stops(self, stops: Sequence[int]) -> SpinResult:
        """Evaluate a specified set of reel stops without using randomness.

        This method is useful both for testing and for exact probability
        calculations, where every possible set of reel stops is enumerated.
        """
        stops_tuple = tuple(stops)
        grid = self._grid_from_stops(stops_tuple)
        line_wins: list[LineWin] = []

        for line_index, line in enumerate(self.paylines, start=1):
            first_symbol = grid[line[0]][0]
            matched = 1

            # Only consecutive matches beginning on the leftmost reel count.
            for reel_index in range(1, 5):
                if grid[line[reel_index]][reel_index] != first_symbol:
                    break
                matched += 1

            multiplier = self.paytable.get(first_symbol, {}).get(matched, 0.0)
            if matched >= 3 and multiplier > 0:
                line_wins.append(
                    LineWin(
                        line_number=line_index,
                        symbol=first_symbol,
                        matched_symbols=matched,
                        payout=multiplier * self.line_bet,
                    )
                )

        total_payout = sum(win.payout for win in line_wins)
        return SpinResult(
            grid=grid,
            stops=stops_tuple,
            line_wins=tuple(line_wins),
            total_payout=total_payout,
            total_bet=self.total_bet,
        )

    def spin(self) -> SpinResult:
        """Generate one random spin and evaluate its payout."""
        stops = tuple(self._rng.randrange(len(reel)) for reel in self.reels)
        return self.evaluate_stops(stops)

    @staticmethod
    def _build_metrics(
        trials: int,
        total_bet: float,
        total_paid: float,
        hit_count: int,
        sum_return_ratios: float,
        sum_squared_return_ratios: float,
        maximum_payout: float,
    ) -> Metrics:
        if trials <= 0:
            raise ValueError("The number of trials must be positive.")

        mean_return = sum_return_ratios / trials
        variance = max(0.0, sum_squared_return_ratios / trials - mean_return**2)
        standard_deviation = math.sqrt(variance)
        total_wagered = trials * total_bet

        return Metrics(
            trials=trials,
            total_wagered=total_wagered,
            total_paid=total_paid,
            rtp_percent=(total_paid / total_wagered) * 100.0,
            hit_frequency_percent=(hit_count / trials) * 100.0,
            variance=variance,
            standard_deviation=standard_deviation,
            maximum_payout=maximum_payout,
            maximum_win_multiple=maximum_payout / total_bet,
        )

    def simulate(self, spins: int = 100000) -> Metrics:
        """Estimate the game's statistics with Monte Carlo simulation."""
        if not isinstance(spins, int) or isinstance(spins, bool) or spins <= 0:
            raise ValueError("The number of spins must be a positive integer.")

        total_paid = 0.0
        hit_count = 0
        sum_return_ratios = 0.0
        sum_squared_return_ratios = 0.0
        maximum_payout = 0.0

        for _ in range(spins):
            result = self.spin()
            payout = result.total_payout
            return_ratio = payout / self.total_bet

            total_paid += payout
            hit_count += payout > 0
            sum_return_ratios += return_ratio
            sum_squared_return_ratios += return_ratio**2
            maximum_payout = max(maximum_payout, payout)

        return self._build_metrics(
            trials=spins,
            total_bet=self.total_bet,
            total_paid=total_paid,
            hit_count=hit_count,
            sum_return_ratios=sum_return_ratios,
            sum_squared_return_ratios=sum_squared_return_ratios,
            maximum_payout=maximum_payout,
        )

    def exact_analysis(self) -> Metrics:
        """Calculate exact statistics by enumerating every reel-stop tuple.

        Every stop on each reel is selected with equal probability. Therefore,
        each tuple of five stops is equally likely, and exhaustive enumeration
        gives exact theoretical statistics for this model.

        The number of combinations is the product of the five reel lengths.
        Exact enumeration can become expensive for much longer reel strips.
        """
        stop_ranges = (range(len(reel)) for reel in self.reels)
        total_outcomes = math.prod(len(reel) for reel in self.reels)

        total_paid = 0.0
        hit_count = 0
        sum_return_ratios = 0.0
        sum_squared_return_ratios = 0.0
        maximum_payout = 0.0

        for stops in itertools.product(*stop_ranges):
            result = self.evaluate_stops(stops)
            payout = result.total_payout
            return_ratio = payout / self.total_bet

            total_paid += payout
            hit_count += payout > 0
            sum_return_ratios += return_ratio
            sum_squared_return_ratios += return_ratio**2
            maximum_payout = max(maximum_payout, payout)

        return self._build_metrics(
            trials=total_outcomes,
            total_bet=self.total_bet,
            total_paid=total_paid,
            hit_count=hit_count,
            sum_return_ratios=sum_return_ratios,
            sum_squared_return_ratios=sum_squared_return_ratios,
            maximum_payout=maximum_payout,
        )


def print_metrics(title: str, metrics: Metrics) -> None:
    """Print a compact, readable summary of game statistics."""
    print(f"\n{title}")
    print("-" * len(title))
    print(f"Outcomes analysed : {metrics.trials:,}")
    print(f"Total wagered     : {metrics.total_wagered:,.2f} credits")
    print(f"Total paid        : {metrics.total_paid:,.2f} credits")
    print(f"RTP               : {metrics.rtp_percent:.4f}%")
    print(f"Hit frequency     : {metrics.hit_frequency_percent:.4f}%")
    print(f"Variance          : {metrics.variance:.6f} (bet multiples squared)")
    print(f"Std. deviation    : {metrics.standard_deviation:.6f} x total bet")
    print(f"Maximum win       : {metrics.maximum_payout:,.2f} credits")
    print(f"Maximum win       : {metrics.maximum_win_multiple:.4f} x total bet")


def print_grid(result: SpinResult) -> None:
    """Display a spin as three rows and five columns."""
    print("\nExample spin (three rows by five reels):")
    for row in result.grid:
        print(" | ".join(f"{symbol:>2}" for symbol in row))
    print(f"Total bet: {result.total_bet:g} credits")
    print(f"Total payout: {result.total_payout:g} credits")
    if result.line_wins:
        print("Winning paylines:")
        for win in result.line_wins:
            print(
                f"  Line {win.line_number:>2}: {win.matched_symbols} x {win.symbol}"
                f" -> {win.payout:g} credits"
            )
    else:
        print("No winning paylines.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse and simulate a simple 5-reel x 3-row slot game."
    )
    parser.add_argument(
        "--spins",
        type=int,
        default=100_000,
        help="number of Monte Carlo spins (default: 100000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="random seed for reproducible simulation (default: 42)",
    )
    args = parser.parse_args()

    if args.spins <= 0:
        parser.error("--spins must be a positive integer")

    # Use a separate instance for the displayed example so it does not change
    # the random sequence used by the Monte Carlo experiment.
    example = SlotMachine(seed=args.seed).spin()
    print_grid(example)

    machine = SlotMachine(seed=args.seed)
    print_metrics("Exact theoretical analysis", machine.exact_analysis())
    print_metrics("Monte Carlo simulation", machine.simulate(args.spins))


if __name__ == "__main__":
    main()
