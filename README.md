# roblox-up-and-coming-forecast-01

Entry for the make.fun bounty "Predict Roblox's Up-and-Coming top 10".

## Program

`main.py` (Python 3.13, standard library only) reads `/input/history.ndjson` (hourly snapshots of Roblox's Up-and-Coming chart) and `/input/task.json`, and writes `/output/forecast.json`: probabilities for each game at each of places 1-10, plus a top-10 guess in order.

## Method

The chart moves fast, so a persistence forecast loses. Each game is scored by recent rank (dominant), bounded rank momentum (climbing games gain), player-count growth, and stability (presence in the recent top 20). For each place, probability is spread over the top candidates with a Gaussian kernel on expected rank, so a wrong top guess does not hit the log-score floor. Backtest on the last 10 practice reads: -34.98 vs -35.59 for the persistence baseline.

## Files

- `main.py` — the forecaster
- `LICENSE` — MIT

Verified: deterministic, runs twice with identical output.
