# Educational 5x3 Slot Game Mathematics
A small Python project that demonstrates how reel strips, paylines and a paytable determine the mathematical behaviour of a simple slot game.

## Game rules
- Five circular reels, each with 12 stop positions and with three visible symbols per reel. There are six regular symbols: `A`, `K`, `Q`, `J`, `10`, and `9`.
- Twenty fixed paylines. A line wins when its first three, four or five symbols match from left to right.
- Only the longest matching prefix on a line is paid.
- Payouts from different paylines are added together.
- No wilds, scatters, bonus rounds, free spins or progressive jackpots.
- Default bet: 1 credit per payline, or 20 credits per spin.
  
## Run the program
Requires Python 3.10 or newer. The program uses only the Python standard library.
```bash
python slot_machine.py
```
Choose a different simulation size or random seed:
```bash
python slot_machine.py --spins 1000000 --seed 7
```
The program first enumerates every possible combination of reel stops to calculate exact theoretical statistics. It then runs a Monte Carlo simulation and prints the estimated statistics for comparison.

## Metrics
- RTP: expected total payout, expressed as a percentage.
- Hit frequency: percentage of spins that produce at least one positive payline payout.
- Volatility measure: standard deviation of the payout divided by the number of credits per spin, measured in multiples of the bet.

## Tests
Install pytest if necessary and run:
```bash
python -m pytest -q
```

## Development approach

This project was developed iteratively with AI assistance (ChatGPT), which supported the initial implementation, code refinement, input validation, test development and documentation. The project is also a learning exercise in slot game mathematics, probability theory and Python software development. The implementation and mathematical results are being reviewed and independently validated.

**Important limitation**: this is an educational simulator, not a commercial game. Python's `random` module is not a certified gaming RNG, and the program does not implement regulatory, security, responsible-gaming or production requirements.
