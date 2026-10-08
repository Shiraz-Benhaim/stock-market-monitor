# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                 # create .venv and install locked deps (yfinance -> pandas, requests, python-dotenv)
uv run app.py           # run one full scan locally (reads .env, sends a real Telegram message)
uv add <pkg>            # add a dependency (updates pyproject.toml + uv.lock; commit both)
```

The project uses uv; dependencies live in `pyproject.toml`/`uv.lock` (there is no requirements.txt). It is a non-packaged uv project (no `[build-system]`). There is no test suite, linter, or build step configured. Python 3.10+ is required (the code uses `dict | None` / `list[...]` annotations); `.python-version` pins 3.10 to match CI and Lambda.

Running locally requires a `.env` in the repo root (git-ignored) with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; `SYMBOLS` (comma-separated) and `HISTORY_PERIOD` (yfinance period string, default `3mo`) are optional. `Config.validate()` raises if the Telegram vars are missing.

## Architecture

A single-pass pipeline deployed as an AWS Lambda function (`app.lambda_handler`), triggered weekly by EventBridge (`cron(0 5 ? * SAT *)`).

- `app.py` (repo root — it was moved into `src/` once and reverted; the Lambda handler path and CI packaging depend on it being at the root) holds `run_pipeline()`: the hardcoded `active_indicators` list, the per-symbol loop, report formatting, and the Telegram send. Each symbol is wrapped in its own try/except so one failure doesn't stop the scan. Only one consolidated Telegram message is sent per run, and only if at least one indicator fired.
- `src/indicators/` uses the Strategy pattern: every indicator subclasses `IndicatorBase` and implements `evaluate(market_history: pd.DataFrame) -> dict | None`. A triggered result must include `indicator` and `message` keys (that's all `app.py` reads); return `None` when not triggered or when there isn't enough history. Adding an indicator = new module + export in `src/indicators/__init__.py` + instance in `active_indicators` in `app.py`.
- `src/config.py` — `Config` class with class attributes read from env at import time (`load_dotenv()` runs on import).
- `src/data_fetcher.py` — `yfinance.Ticker(symbol).history(period=Config.HISTORY_PERIOD)`; the same DataFrame is passed to every indicator for that symbol.
- `src/notifier.py` — posts to Telegram `sendMessage` with legacy `parse_mode=Markdown`, so dynamic text containing `_`, `*`, `` ` ``, `[` can break formatting/delivery. Its boolean return is currently ignored by `app.py`.

Gotchas:
- An indicator only fires if the fetched history has at least `window`/`period` rows. With the default `HISTORY_PERIOD=3mo` (~63 trading days), `SMACrossIndicator(window=200)` never triggers.
- `SMACrossIndicator.threshold_percentage` is a fraction (`0.05` = 5%), not a percent. It also writes an `SMA` column into the shared DataFrame.
- `RSIIndicator` uses a simple rolling mean (not Wilder smoothing) and only checks oversold.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`: it runs `uv export` to turn `uv.lock` into a requirements list, `uv pip install --target artifact/`, copies `app.py` and `src/` in, zips the result, uploads it to `s3://stock-market-monitor-deployments/`, and runs `aws lambda update-function-code` on the `stock-market-monitor` function in `us-east-1`. Any new top-level file or package the runtime needs must also be added to the copy step in the workflow. Lambda environment variables are configured in AWS, not in the repo.

## Docs

`README.md` is the full technical reference (configuration, deployment, indicator contract, troubleshooting); update it when behavior, config, or deployment changes.
