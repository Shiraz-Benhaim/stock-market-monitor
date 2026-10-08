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
4. Pushes the report to a Telegram chat. If no indicator fires, nothing is sent.

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
│   Config.validate()                                          │
│        │                                                     │
│        ▼                                                     │
│   for each symbol in SYMBOLS:                                │
│        ├─► data_fetcher.fetch_market_history()  ──► yfinance │
│        ├─► indicator.evaluate()  × N indicators              │
│        └─► collect triggered alerts                          │
│        │                                                     │
│        ▼                                                     │
│   build consolidated report                                  │
└──────────┬───────────────────────────────────────────────────┘
           │ HTTPS POST (only if ≥1 alert)
           ▼
┌──────────────────────┐
│   Telegram Bot API   │ ──► your chat / channel
└──────────────────────┘
```

### Execution flow

| Step | Component | Description |
|---|---|---|
| 1 | `Config.validate()` | Fails fast if `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing. |
| 2 | `data_fetcher.fetch_market_history()` | Downloads daily OHLCV data from Yahoo Finance via `yfinance` for the period set by `HISTORY_PERIOD`. |
| 3 | `IndicatorBase.evaluate()` | Each active indicator inspects the DataFrame. It returns an alert `dict` when its condition is met and `None` otherwise. |
| 4 | `run_pipeline()` | Collects the triggered alerts for each symbol and formats them into one Markdown block per symbol that includes the latest close price. |
| 5 | `notifier.send_telegram_alert()` | Joins all symbol blocks with a separator and sends them as a single Telegram message. |

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
│       └── deploy.yml           # CI/CD: package & deploy to Lambda on push to main
└── src/
    ├── config.py                # Environment-driven configuration & validation
    ├── data_fetcher.py          # Market data retrieval (yfinance)
    ├── notifier.py              # Telegram delivery
    └── indicators/
        ├── __init__.py          # Public indicator exports
        ├── base.py              # IndicatorBase — abstract strategy interface
        ├── sma_cross_indicator.py
        └── rsi_indicator.py
```

| Module | Responsibility |
|---|---|
| `app.py` | Defines the active indicator set, iterates over symbols, builds the report, and exposes `lambda_handler(event, context)`. |
| `src/config.py` | Loads `.env` (via `python-dotenv`) and exposes typed settings on the `Config` class. |
| `src/data_fetcher.py` | Thin wrapper around `yfinance.Ticker(symbol).history(...)` that returns a `pandas.DataFrame`. |
| `src/notifier.py` | Sends a message through the Telegram `sendMessage` endpoint with `parse_mode=Markdown`. |
| `src/indicators/base.py` | The `IndicatorBase` abstract class. Every indicator must implement it. |

---

## 4. Indicators

The active indicator set is defined in `app.py`:

```python
active_indicators: list[IndicatorBase] = [
    SMACrossIndicator(window=20,  threshold_percentage=0.0),  # SMA 20
    SMACrossIndicator(window=50,  threshold_percentage=0.0),  # SMA 50
    SMACrossIndicator(window=200, threshold_percentage=0.0),  # SMA 200
    RSIIndicator(period=14, oversold=35.0),                   # RSI oversold
]
```

### 4.1 SMA Cross — `SMACrossIndicator`

Fires when the latest closing price is **at or below** its Simple Moving Average (SMA), optionally by at least a given margin.

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
{
    "indicator": "SMA_50",
    "latest_price": 182.31,
    "sma_value": 188.90,
    "diff_percentage": -3.49,
    "message": "Price ($182.31) is below SMA_50 ($188.90) by 3.49%"
}
```

> **Data requirement:** the indicator needs at least `window` rows of history and returns `None` if it has fewer. See [`HISTORY_PERIOD`](#5-configuration).

### 4.2 RSI Oversold — `RSIIndicator`

Fires when the **Relative Strength Index** falls to or below the oversold threshold. This often points to a potential buy-the-dip opportunity.

**Logic**

```text
Δ            = Close.diff()
avg_gain     = rolling mean of positive Δ over `period`
avg_loss     = rolling mean of |negative Δ| over `period`
RSI          = 100 − 100 / (1 + avg_gain / avg_loss)
trigger if   RSI_latest ≤ oversold
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `14` | RSI look-back period in trading days. |
| `oversold` | `float` | `30.0` | Alert threshold (0–100). The pipeline uses `35.0`. |

> **Note:** this implementation averages gains and losses with a simple rolling mean (Cutler's RSI). It doesn't use Wilder's exponential smoothing, so its values can differ slightly from those shown on charting platforms such as TradingView.

---

## 5. Configuration

All settings are read from environment variables. When you run locally, they are loaded from a `.env` file in the project root, which is git-ignored.

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token issued by [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_CHAT_ID` | ✅ | — | Target chat, group, or channel ID. |
| `SYMBOLS` | ❌ | `AAPL,MSFT,NVDA,QQQ,SPY` | Comma-separated list of Yahoo Finance tickers. |
| `HISTORY_PERIOD` | ❌ | `3mo` | How much history to fetch. Accepts any `yfinance` period (`1mo`, `3mo`, `6mo`, `1y`, `2y`, …). |

### Example `.env`

```dotenv
TELEGRAM_BOT_TOKEN=123456789:AAExampleTokenValue
TELEGRAM_CHAT_ID=987654321
SYMBOLS=AAPL,MSFT,NVDA,GOOGL,QQQ,SPY
HISTORY_PERIOD=1y
```

> ⚠️ **Choosing `HISTORY_PERIOD`:** `3mo` provides only about 63 trading days, so **SMA 200 can never trigger**. SMA 50 also gets few data points. Use `1y` (about 252 trading days) or longer if you keep the SMA 200 indicator.

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

To manage dependencies, use `uv add <package>` and `uv remove <package>`. Both update `pyproject.toml` and `uv.lock` together. Commit both files.

The console output shows either `Summary report sent successfully.` followed by the report, or `No indicators triggered today.`

---

## 7. Deployment

### 7.1 Automated CI/CD (GitHub Actions)

Every push to `main` runs [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which does the following:

1. Sets up Python (version from `.python-version`) and uv on `ubuntu-latest`.
2. Exports the locked runtime dependencies with `uv export`, installs them into an `artifact/` directory with `uv pip install --target`, and copies in `app.py` and `src/`.
3. Zips the result into `deployment_package.zip`.
4. Uploads the zip to **S3** at `s3://stock-market-monitor-deployments/deployment_package.zip`.
5. Runs `aws lambda update-function-code` on the **`stock-market-monitor`** function in **`us-east-1`**.

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
   | Runtime | Python 3.10 (to match CI) |
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

The handler's `print` output, including per-symbol errors, goes to **Amazon CloudWatch Logs** under `/aws/lambda/stock-market-monitor`.

---

## 8. Extending: Writing a Custom Indicator

Adding an indicator takes three steps, and you never touch the pipeline logic.

**1. Implement the strategy.** Create `src/indicators/<name>_indicator.py`:

```python
import pandas as pd

from src.indicators.base import IndicatorBase


class VolumeSpikeIndicator(IndicatorBase):
    """Triggers when today's volume exceeds the average volume by a multiplier."""

    def __init__(self, window: int = 20, multiplier: float = 2.0):
        self.window = window
        self.multiplier = multiplier

    def evaluate(self, market_history: pd.DataFrame) -> dict | None:
        if len(market_history) < self.window + 1:
            return None

        avg_volume = market_history['Volume'].iloc[-self.window - 1:-1].mean()
        latest_volume = market_history['Volume'].iloc[-1]

        if latest_volume >= avg_volume * self.multiplier:
            ratio = latest_volume / avg_volume
            return {
                "indicator": f"VOLUME_SPIKE_{self.window}",
                "message": f"Volume is {ratio:.1f}x the {self.window}-day average"
            }
        return None
```

**2. Export it** in `src/indicators/__init__.py`:

```python
from .volume_spike_indicator import VolumeSpikeIndicator
```

**3. Register it** in `active_indicators` in `app.py`:

```python
VolumeSpikeIndicator(window=20, multiplier=2.0),
```

### The `evaluate()` contract

| Rule | Detail |
|---|---|
| **Input** | A `pandas.DataFrame` indexed by date, with columns `Open`, `High`, `Low`, `Close`, `Volume`, `Dividends`, and `Stock Splits`. |
| **Return when triggered** | A `dict` that **must** contain `indicator` (short label) and `message` (human-readable text). Additional keys are allowed and are useful for debugging. |
| **Return otherwise** | `None`. |
| **Insufficient data** | Return `None` rather than raising an exception. |
| **Markdown safety** | Messages are sent with Telegram's legacy Markdown, so avoid unescaped `_`, `*`, `` ` ``, and `[` in dynamic text. |
| **Side effects** | Avoid mutating `market_history`. The same DataFrame is passed to every indicator. |

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
| SMA 200 never appears | `HISTORY_PERIOD` is too short. | Set `HISTORY_PERIOD=1y` or longer. |
| Log says *"sent successfully"* but no message arrives | Telegram rejected the request (wrong chat ID, bot not in the chat, or a Markdown parse error). | Check the token and chat ID with `getUpdates`, make sure the bot has been started or added, and look for unescaped Markdown characters. |
| `Error processing XYZ: ...` in the logs | Invalid ticker or a Yahoo Finance outage or rate limit. | Check the ticker on finance.yahoo.com. Other symbols are not affected. |
| Lambda `Task timed out` | Timeout too low. | Raise the timeout to at least 60 s. |
| `Unable to import module 'app'` | Wrong handler, or the package was zipped with an extra parent folder. | Set the handler to `app.lambda_handler` and make sure `app.py` is at the zip root. |

---

## 11. Known Limitations & Roadmap

**Current limitations**

- The indicator set and its parameters are set in code. Changing them requires a redeploy.
- The return value of `send_telegram_alert` isn't checked, so delivery failures are not surfaced.
- Telegram limits a message to 4,096 characters, and very large watchlists with many alerts may exceed it.
- `RSIIndicator` detects oversold conditions only. Overbought detection is not implemented yet.
- There's no automated test suite yet.

**Possible next steps**

- [ ] Unit tests for indicators using fixed DataFrame fixtures (`pytest`).
- [ ] Overbought RSI, MACD, and Bollinger Band indicators.
- [ ] Move secrets to AWS SSM Parameter Store or Secrets Manager.
- [ ] Split long reports into multiple Telegram messages.
- [ ] Infrastructure as Code (AWS SAM / Terraform) for the one-time setup.
- [ ] Use GitHub OIDC for AWS authentication instead of long-lived access keys.

---

## 12. Disclaimer

This project is for **educational and informational purposes only**. It isn't financial advice. Technical indicators are lagging signals and don't guarantee future performance. Always do your own research before making investment decisions.

---

**License:** MIT
