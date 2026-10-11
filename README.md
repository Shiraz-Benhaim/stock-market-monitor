# Stock Market Monitor 📈

> A serverless market-scanning pipeline that runs technical indicators against a watchlist of tickers and delivers a consolidated alert report to Telegram.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=awslambda&logoColor=white)
![Amazon EventBridge](https://img.shields.io/badge/Amazon-EventBridge-FF4F8B?logo=amazonaws&logoColor=white)
![uv](https://img.shields.io/badge/Package%20Manager-uv-DE5FE9?logo=uv&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Telegram](https://img.shields.io/badge/Alerts-Telegram-26A5E4?logo=telegram&logoColor=white)

This document explains how the system works, how to configure and deploy it, and how to extend it with new indicators.

---

## Table of Contents

1. [Overview](#1-overview)
2. [How It Works](#2-how-it-works)
3. [Project Structure](#3-project-structure)
4. [Indicators](#4-indicators)
5. [Configuration](#5-configuration)
6. [Running Locally](#6-running-locally)
7. [Deployment](#7-deployment)
8. [Extending: Writing a Custom Indicator](#8-extending-writing-a-custom-indicator)
9. [Example Alert](#9-example-alert)
10. [Troubleshooting](#10-troubleshooting)
11. [Known Limitations & Roadmap](#11-known-limitations--roadmap)
12. [Disclaimer](#12-disclaimer)

---

## 1. Overview

**Stock Market Monitor** replaces manual chart-checking with a scheduled, automated scan. On each run it:

1. Downloads recent daily price history for every symbol on your watchlist.
2. Runs each configured technical indicator against that history.
3. Groups all triggered signals per symbol into a single, readable report.
4. Pushes the report to a Telegram chat. Symbols that failed to load are listed at the end. If nothing fires and nothing fails, no message is sent.

### Design goals

| Goal | How it is achieved |
|---|---|
| **Zero infrastructure to manage** | Runs as an AWS Lambda function, triggered by an Amazon EventBridge schedule. |
| **Easy to extend** | Indicators follow the **Strategy Pattern**. Each one implements a single `evaluate()` method, so you can add an indicator without changing the pipeline (Open/Closed Principle). |
| **Low noise** | You get one message per run that covers only the symbols with triggered indicators, not one message per signal. |
| **Fault isolation** | Errors are handled per symbol, so one bad ticker or a data-provider hiccup doesn't abort the whole scan. |
| **Secrets kept out of code** | Credentials come from environment variables: a git-ignored `.env` file locally, Lambda configuration in the cloud. |

---

## 2. How It Works

### Architecture

```text
┌──────────────────────┐
│  Amazon EventBridge  │   cron(0 5 ? * SAT *)  — every Saturday 05:00 UTC
└──────────┬───────────┘
           │ invokes
           ▼
┌──────────────────────────────────────────────────────────────┐
│  AWS Lambda  —  app.lambda_handler                           │
│                                                              │
│   Config.from_env()                                          │
│        │                                                     │
│        ▼                                                     │
│   run_pipeline(config) — for each symbol in SYMBOLS:         │
│        ├─► data_fetcher.fetch_market_history()  ──► yfinance │
│        ├─► scan_symbol()  →  indicator.evaluate() × N        │
│        └─► format_symbol_report()                            │
│        │                                                     │
│        ▼                                                     │
│   add failed symbols, split into ≤ 4096-char messages        │
└──────────┬───────────────────────────────────────────────────┘
           │ HTTPS POST (only if ≥1 alert or failure)
           ▼
┌──────────────────────┐
│   Telegram Bot API   │ ──► your chat / channel
└──────────────────────┘
```

### Execution flow

| Step | Component | Description |
|---|---|---|
| 1 | `Config.from_env()` | Builds an immutable `Config` from environment variables. Fails fast if `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing. |
| 2 | `data_fetcher.fetch_market_history()` | Downloads daily OHLCV data from Yahoo Finance via `yfinance` for the period set by `HISTORY_PERIOD`. |
| 3 | `scan_symbol()` | Runs each active indicator whose `min_history` is satisfied (logging a warning for any that are skipped). `evaluate()` returns an `IndicatorResult` when its condition is met and `None` otherwise. |
| 4 | `format_symbol_report()` | Formats the triggered alerts for each symbol into one HTML block that includes the latest close price. Symbols that failed to load are collected into a final "Failed to scan" block. |
| 5 | `notifier.split_message()` / `send_telegram_alert()` | Joins the blocks with a separator into as few messages as fit Telegram's 4,096-character limit and sends them. A rejected message raises, so the Lambda invocation fails visibly. |

---

## 3. Project Structure

```text
stock-market-monitor/
├── app.py                       # Entry point: pipeline orchestration + Lambda handler
├── pyproject.toml               # Project metadata & dependencies (managed by uv)
├── uv.lock                      # Pinned dependency versions
├── .python-version              # Python version used by uv and CI (3.10)
├── .github/
│   └── workflows/
│       └── deploy.yml           # CI/CD: lint, test, package & deploy to Lambda on push to main
├── tests/                       # pytest suite (indicators, report formatting, pipeline)
└── src/
    ├── config.py                # Environment-driven configuration & validation
    ├── data_fetcher.py          # Market data retrieval (yfinance)
    ├── notifier.py              # Telegram delivery & message splitting
    └── indicators/
        ├── __init__.py          # Public indicator exports
        ├── base.py              # IndicatorBase & IndicatorResult — the strategy interface
        ├── price_below_sma_indicator.py
        └── rsi_indicator.py
```

| Module | Responsibility |
|---|---|
| `app.py` | Defines `ACTIVE_INDICATORS`, scans each symbol, formats the report, and exposes `lambda_handler(event, context)`. |
| `src/config.py` | The frozen `Config` dataclass. `Config.from_env()` loads `.env` (via `python-dotenv`) and reads the environment. |
| `src/data_fetcher.py` | Thin wrapper around `yfinance.Ticker(symbol).history(period=...)` that returns a `pandas.DataFrame`. |
| `src/notifier.py` | Splits the report to fit Telegram's message limit and sends it through the `sendMessage` endpoint with `parse_mode=HTML`. |
| `src/indicators/base.py` | The `IndicatorBase` abstract class every indicator implements, and the `IndicatorResult` it returns. |

---

## 4. Indicators

The active indicator set is defined in `app.py`:

```python
ACTIVE_INDICATORS: list[IndicatorBase] = [
    PriceBelowSMAIndicator(window=20),
    PriceBelowSMAIndicator(window=50),
    PriceBelowSMAIndicator(window=200),
    RSIIndicator(period=14, oversold=35.0),
]
```

### 4.1 Price Below SMA — `PriceBelowSMAIndicator`

Fires when the latest closing price is **at or below** its Simple Moving Average (SMA), optionally by at least a given margin. This is a level check, not a crossover: it fires on every run while the price stays below the SMA.

**Logic**

```text
SMA          = mean(Close over last `window` days)
target       = SMA × (1 − threshold_percentage)
trigger if   Close_latest ≤ target
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `window` | `int` | `20` | Number of trading days in the moving average. |
| `threshold_percentage` | `float` | `0.0` | Required margin below the SMA, as a **fraction**. For example, `0.05` means the price must be at least 5% below the SMA. |

**Alert payload**

```python
IndicatorResult(
    indicator="SMA_50",
    message="Price ($182.31) is below SMA_50 ($188.90) by 3.49%",
    details={"latest_price": 182.31, "sma_value": 188.90, "diff_percentage": -3.49},
)
```

> **Data requirement:** the indicator needs at least `window` rows of history and returns `None` if it has fewer. See [`HISTORY_PERIOD`](#5-configuration).

### 4.2 RSI Oversold — `RSIIndicator`

Fires when the **Relative Strength Index** falls to or below the oversold threshold. This often points to a potential buy-the-dip opportunity.

**Logic**

```text
Δ            = Close.diff()
avg_gain     = Wilder-smoothed mean of positive Δ   (EWM, α = 1 / period)
avg_loss     = Wilder-smoothed mean of |negative Δ| (EWM, α = 1 / period)
RSI          = 100 − 100 / (1 + avg_gain / avg_loss)
trigger if   RSI_latest ≤ oversold   (no trigger when prices are flat: RSI is undefined)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `14` | RSI look-back period in trading days. |
| `oversold` | `float` | `30.0` | Alert threshold (0–100). The pipeline uses `35.0`. |

> **Note:** Wilder's smoothing matches the RSI shown on charting platforms such as TradingView once there is enough history to warm up (a few multiples of `period`; the default `1y` is plenty).

---

## 5. Configuration

All settings are read from environment variables. When you run locally, they are loaded from a `.env` file in the project root, which is git-ignored.

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token issued by [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_CHAT_ID` | ✅ | — | Target chat, group, or channel ID. |
| `SYMBOLS` | ❌ | `AAPL,MSFT,NVDA,QQQ,SPY` | Comma-separated list of Yahoo Finance tickers. Blank entries are ignored and tickers are upper-cased. |
| `HISTORY_PERIOD` | ❌ | `1y` | How much history to fetch. Accepts any `yfinance` period (`1mo`, `3mo`, `6mo`, `1y`, `2y`, …). |

### Example `.env`

```dotenv
TELEGRAM_BOT_TOKEN=123456789:AAExampleTokenValue
TELEGRAM_CHAT_ID=987654321
SYMBOLS=AAPL,MSFT,NVDA,GOOGL,QQQ,SPY
HISTORY_PERIOD=1y
```

> ⚠️ **Choosing `HISTORY_PERIOD`:** each indicator declares a `min_history`, and is skipped (with a warning in the logs) when the fetched history is shorter. `3mo` provides only about 63 trading days, so **SMA 200 would never run**. Keep `1y` (about 252 trading days) or longer while the SMA 200 indicator is active.

### Getting Telegram credentials

1. In Telegram, message **@BotFather**, send `/newbot`, and follow the prompts. Copy the token it gives you into `TELEGRAM_BOT_TOKEN`.
2. Send any message to your new bot, or add the bot to a group or channel.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and find `"chat":{"id": ...}` in the response. That value is your `TELEGRAM_CHAT_ID`. Group and channel IDs are negative numbers.

---

## 6. Running Locally

**Prerequisites:** [uv](https://docs.astral.sh/uv/getting-started/installation/). You don't need to install Python yourself: uv reads `.python-version` and downloads Python 3.10 if it isn't already available.

```bash
# Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh                                  # macOS / Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

# 1. Clone
git clone https://github.com/Shiraz-Benhaim/stock-market-monitor.git
cd stock-market-monitor

# 2. Create the virtual environment (.venv) and install the locked dependencies
uv sync

# 3. Configure
#    Create a .env file as shown in the Configuration section

# 4. Run a scan
uv run app.py
```

To manage dependencies, use `uv add <package>` and `uv remove <package>`. Both update `pyproject.toml` and `uv.lock` together. Commit both files. Dev-only tools go in the `dev` group (`uv add --dev <package>`) and are left out of the Lambda package.

The console output shows either the report followed by `Summary report sent successfully.`, or `No indicators triggered today.`

### Tests & code style

The code follows PEP 8 and is formatted with [black](https://black.readthedocs.io/) (line length 88). [ruff](https://docs.astral.sh/ruff/) checks PEP 8 and import order. CI runs all three before every deploy:

```bash
uv run black .          # format
uv run ruff check .     # lint (add --fix to auto-fix)
uv run pytest           # tests
```

---

## 7. Deployment

### 7.1 Automated CI/CD (GitHub Actions)

Every push to `main` runs [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which does the following:

1. Sets up Python (version from `.python-version`) and a pinned uv version on `ubuntu-latest`.
2. Runs `black --check`, `ruff check`, and `pytest`. A failure stops the deploy.
3. Exports the locked runtime dependencies with `uv export --frozen` (CI fails if `uv.lock` is missing), installs them into an `artifact/` directory with `uv pip install --target`, and copies in `app.py` and `src/`.
4. Zips the result into `deployment_package.zip`.
5. Uploads the zip to **S3** at `s3://stock-market-monitor-deployments/deployment_package.zip`.
6. Runs `aws lambda update-function-code` on the **`stock-market-monitor`** function in **`us-east-1`**.

The package goes through S3 because `pandas` and `numpy` make it larger than Lambda's 50 MB limit for direct uploads.

**Required repository secrets** (*Settings → Secrets and variables → Actions*):

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key for an IAM user that can deploy. |
| `AWS_SECRET_ACCESS_KEY` | Matching secret key. |

**Minimum IAM permissions for the deploy user:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::stock-market-monitor-deployments/*"
    },
    {
      "Effect": "Allow",
      "Action": "lambda:UpdateFunctionCode",
      "Resource": "arn:aws:lambda:us-east-1:*:function:stock-market-monitor"
    }
  ]
}
```

### 7.2 One-time AWS setup

The workflow only *updates* existing resources. Create these once before the first deploy:

1. **S3 bucket** named `stock-market-monitor-deployments` in `us-east-1`.
2. **Lambda function** named `stock-market-monitor`:
   | Setting | Recommended value |
   |---|---|
   | Runtime | Python 3.10. **Must match `.python-version`**: compiled wheels (`pandas`, `numpy`) are built for that exact version, so bump both together. |
   | Handler | `app.lambda_handler` |
   | Memory | 512 MB |
   | Timeout | 60 s or more. The 3 s default is too short for network calls across several symbols. |
   | Environment variables | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SYMBOLS`, `HISTORY_PERIOD` |
3. **EventBridge schedule** that targets the function:
   ```text
   cron(0 5 ? * SAT *)      # Every Saturday at 05:00 UTC
   ```
   For a scan before every trading day instead, use `cron(0 12 ? * MON-FRI *)`.

### 7.3 Lambda response

On success, the handler returns:

```json
{ "statusCode": 200, "body": "Pipeline executed successfully" }
```

If the Telegram message is rejected, the handler raises instead, so the invocation shows up as an error in the Lambda metrics.

The handler's log output, including per-symbol errors with tracebacks, goes to **Amazon CloudWatch Logs** under `/aws/lambda/stock-market-monitor`.

---

## 8. Extending: Writing a Custom Indicator

Adding an indicator takes three steps, and you never touch the pipeline logic.

**1. Implement the strategy.** Create `src/indicators/<name>_indicator.py`:

```python
import pandas as pd

from src.indicators.base import IndicatorBase, IndicatorResult


class VolumeSpikeIndicator(IndicatorBase):
    """Trigger when today's volume exceeds the average volume by a multiplier."""

    def __init__(self, window: int = 20, multiplier: float = 2.0):
        self.window = window
        self.multiplier = multiplier

    @property
    def min_history(self) -> int:
        return self.window + 1

    def evaluate(self, market_history: pd.DataFrame) -> IndicatorResult | None:
        if len(market_history) < self.min_history:
            return None

        volumes = market_history["Volume"]
        avg_volume = volumes.iloc[-self.window - 1 : -1].mean()
        latest_volume = volumes.iloc[-1]

        if latest_volume < avg_volume * self.multiplier:
            return None

        ratio = latest_volume / avg_volume
        return IndicatorResult(
            indicator=f"VOLUME_SPIKE_{self.window}",
            message=f"Volume is {ratio:.1f}x the {self.window}-day average",
        )
```

**2. Export it** in `src/indicators/__init__.py` (import and `__all__`):

```python
from .volume_spike_indicator import VolumeSpikeIndicator
```

**3. Register it** in `ACTIVE_INDICATORS` in `app.py`:

```python
VolumeSpikeIndicator(window=20, multiplier=2.0),
```

Then add tests for it under `tests/`.

### The `evaluate()` contract

| Rule | Detail |
|---|---|
| **Input** | A `pandas.DataFrame` indexed by date, with columns `Open`, `High`, `Low`, `Close`, `Volume`, `Dividends`, and `Stock Splits`. |
| **`min_history`** | A property returning the minimum number of rows `evaluate()` needs. The pipeline skips the indicator (with a warning) when there is less history. |
| **Return when triggered** | An `IndicatorResult` with `indicator` (short label) and `message` (human-readable plain text). Put extra values in `details`; they are useful for debugging. |
| **Return otherwise** | `None`. |
| **Insufficient data** | Return `None` rather than raising an exception. |
| **Formatting** | Return plain text. The report is sent with Telegram's HTML parse mode, and the pipeline HTML-escapes `indicator` and `message`. |
| **Side effects** | Don't mutate `market_history`. The same DataFrame is passed to every indicator. |

---

## 9. Example Alert

```text
📊 Market Summary for NVDA
💵 Current Price: $118.42
⚠️ Triggered Indicators:
  • SMA_20: Price ($118.42) is below SMA_20 ($124.10) by 4.58%
  • SMA_50: Price ($118.42) is below SMA_50 ($121.77) by 2.75%
  • RSI_14: RSI is oversold at 33.12 (Threshold: 35.0)

───────────────

📊 Market Summary for AAPL
💵 Current Price: $201.05
⚠️ Triggered Indicators:
  • SMA_20: Price ($201.05) is below SMA_20 ($203.40) by 1.16%
```

*The values above are illustrative.*

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID` | Environment variables not set. | Add them to `.env` locally or to the Lambda configuration. |
| SMA 200 never appears; log says *"only N rows of history"* | `HISTORY_PERIOD` is too short. | Set `HISTORY_PERIOD=1y` or longer. |
| `requests.exceptions.HTTPError: 400`/`403` from `api.telegram.org` | Telegram rejected the message (wrong chat ID, or the bot isn't in the chat). | Check the token and chat ID with `getUpdates`, and make sure the bot has been started or added. |
| `Error processing XYZ` in the logs, and *"Failed to scan: XYZ"* in the report | Invalid ticker or a Yahoo Finance outage or rate limit. | Check the ticker on finance.yahoo.com. Other symbols are not affected. |
| Lambda `Task timed out` | Timeout too low. | Raise the timeout to at least 60 s. |
| `Unable to import module 'app'` | Wrong handler, or the package was zipped with an extra parent folder. | Set the handler to `app.lambda_handler` and make sure `app.py` is at the zip root. |

---

## 11. Known Limitations & Roadmap

**Current limitations**

- The indicator set and its parameters are set in code. Changing them requires a redeploy.
- `PriceBelowSMAIndicator` is a level check, so it repeats every run while a price stays below its SMA.
- `RSIIndicator` detects oversold conditions only. Overbought detection is not implemented yet.

**Possible next steps**

- [ ] Configure the indicator set from the environment instead of code.
- [ ] A true SMA crossover indicator (fires only on the run the price crosses).
- [ ] Overbought RSI, MACD, and Bollinger Band indicators.
- [ ] Move secrets to AWS SSM Parameter Store or Secrets Manager.
- [ ] Infrastructure as Code (AWS SAM / Terraform) for the one-time setup.
- [ ] Use GitHub OIDC for AWS authentication instead of long-lived access keys.

---

## 12. Disclaimer

This project is for **educational and informational purposes only**. It isn't financial advice. Technical indicators are lagging signals and don't guarantee future performance. Always do your own research before making investment decisions.

---

**License:** MIT
