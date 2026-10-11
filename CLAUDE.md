# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                 # create .venv and install locked deps (yfinance -> pandas, requests, python-dotenv)
uv run app.py           # run one full scan locally (reads .env, sends a real Telegram message)
uv add <pkg>            # add a dependency (updates pyproject.toml + uv.lock; commit both)
uv run pytest           # run the test suite (tests/)
uv run black .          # format (line length 88)
uv run ruff check .     # lint: PEP 8 + import order
```

The project uses uv; dependencies live in `pyproject.toml`/`uv.lock` (there is no requirements.txt). It is a non-packaged uv project (no `[build-system]`). Dev tools (black, ruff, pytest) live in the `dev` dependency group and are configured in `pyproject.toml`; CI runs all three before deploying. Python 3.10+ is required (the code uses `X | None` / `list[...]` annotations); `.python-version` pins 3.10 to match CI and Lambda.

Running locally requires a `.env` in the repo root (git-ignored) with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; `SYMBOLS` (comma-separated) and `HISTORY_PERIOD` (yfinance period string, default `1y`) are optional. `Config.from_env()` raises if the Telegram vars are missing.

## Architecture

A single-pass pipeline deployed as an AWS Lambda function (`app.lambda_handler`), triggered weekly by EventBridge (`cron(0 5 ? * SAT *)`).

- `app.py` (repo root — it was moved into `src/` once and reverted; the Lambda handler path and CI packaging depend on it being at the root) holds the module-level `ACTIVE_INDICATORS` list, `scan_symbol()`, the HTML report formatters, and `run_pipeline(config)`. Each symbol is wrapped in its own try/except so one failure doesn't stop the scan; failed or empty symbols are listed in a "Failed to scan" section. The report is sent only if at least one indicator fired or a symbol failed, split by `notifier.split_message()` to fit Telegram's 4096-char limit (usually one message).
- `src/indicators/` uses the Strategy pattern: every indicator subclasses `IndicatorBase` and implements a `min_history` property and `evaluate(market_history: pd.DataFrame) -> IndicatorResult | None` (`IndicatorResult` is a frozen dataclass in `base.py`: `indicator`, `message`, `details`). Return `None` when not triggered or when there isn't enough history, and never mutate `market_history`. Messages are plain text; `app.py` HTML-escapes them. Adding an indicator = new module + export in `src/indicators/__init__.py` + instance in `ACTIVE_INDICATORS` in `app.py` + tests.
- `src/config.py` — frozen `Config` dataclass; `Config.from_env()` calls `load_dotenv()` and reads the environment. It is built once in `lambda_handler` / `__main__` and passed down; modules don't import it.
- `src/data_fetcher.py` — `fetch_market_history(symbol, period)` wraps `yfinance.Ticker(symbol).history(period=...)`; the same DataFrame is passed to every indicator for that symbol.
- `src/notifier.py` — posts to Telegram `sendMessage` with `parse_mode=HTML` (dynamic text must go through `html.escape`) and a 10 s timeout; it calls `raise_for_status()`, so a rejected message fails the Lambda invocation.

Gotchas:
- `scan_symbol()` skips (and logs a warning for) any indicator whose `min_history` exceeds the fetched rows. `PriceBelowSMAIndicator(window=200)` needs `HISTORY_PERIOD` of `1y` or more; if the Lambda env still sets `3mo`, it never runs.
- `PriceBelowSMAIndicator` (formerly `SMACrossIndicator`) is a level check, not a crossover: it fires every run while price ≤ SMA. `threshold_percentage` is a fraction (`0.05` = 5%), not a percent.
- `RSIIndicator` uses Wilder smoothing (`ewm(alpha=1/period, adjust=False)`), returns `None` on flat prices (NaN RSI), and only checks oversold.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`: it runs `black --check`, `ruff check` and `pytest` (any failure blocks the deploy), then `uv export --frozen` to turn `uv.lock` into a requirements list, `uv pip install --target artifact/`, copies `app.py` and `src/` in, zips the result, uploads it to `s3://stock-market-monitor-deployments/`, and runs `aws lambda update-function-code` on the `stock-market-monitor` function in `us-east-1`. Any new top-level file or package the runtime needs must also be added to the copy step in the workflow. Lambda environment variables are configured in AWS, not in the repo. `.python-version` must match the Lambda runtime (compiled pandas/numpy wheels are version-specific).

## Docs

`README.md` is the full technical reference (configuration, deployment, indicator contract, troubleshooting); update it when behavior, config, or deployment changes.
