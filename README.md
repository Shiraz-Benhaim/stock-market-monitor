# Stock Market Monitor 📈

> A serverless, event-driven market monitoring engine that evaluates custom technical indicators and dispatches real-time alerts via Telegram.

![AWS Serverless Architecture](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazon-aws)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Architecture](https://img.shields.io/badge/Design-Clean%20Architecture-green)

---

## 💡 Overview

**Stock Market Monitor** automates daily financial technical analysis to eliminate manual portfolio tracking. Built with extensibility in mind using the **Strategy Pattern**, developers can easily plug in new custom technical indicators (SMA, RSI, MACD, etc.).

The system is deployed on **AWS Serverless infrastructure** running on a daily cron schedule via **Amazon EventBridge** and **AWS Lambda**.

## 🏗️ Architecture

```text
[ Amazon EventBridge ] (Weekly Cron Schedule)
         │
         ▼
  [ AWS Lambda ] ──► Fetch Market Data (yfinance API)
         │
         ├──► Evaluate Technical Indicators (SMA, RSI, etc.)
         │
         ▼
[ Telegram Bot API ] ──► Real-Time Alert to User
```

---

## ✨ Key Features

- **Extensible Indicator Engine**: Clean Object-Oriented design using Abstract Classes for seamless addition of new technical indicators.
- **Serverless Architecture**: Event-driven execution via AWS Lambda & EventBridge (Zero Server Overhead).
- **Security First**: Strict separation of secrets using Environment Variables and AWS SSM Parameter Store.
- **Real-Time Push Notifications**: Immediate alert dispatch via Telegram Bot API with Markdown formatting.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Cloud Provider**: AWS (Lambda, EventBridge, CloudWatch)
- **Data & APIs**: yfinance, pandas, Telegram Bot API
- **Design Pattern**: Strategy Pattern (Open/Closed Principle)

---

## 🚀 Quick Start (Local Setup)

1. **Clone Repository:**
   ```bash
   git clone [https://github.com/Shiraz-Benhaim/stock-market-monitor.git](https://github.com/Shiraz-Benhaim/stock-market-monitor.git)
   cd stock-market-monitor
   ```

2. **Setup Virtual Environment & Install Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file and fill in your `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and target `SYMBOLS`.

4. **Run Locally:**
   ```bash
   python -m app.py
   ```

---

## ☁️ Deployment (AWS Lambda)

1. **Package Code:**
   Package the code along with dependencies into a deployment zip file or Lambda Layer.

2. **Create Lambda Function:**
   Create an AWS Lambda function with Python 3.10+ runtime and set `app.lambda_handler` as the entry point.

3. **Set Environment Variables:**
   Configure Environment Variables in the AWS Lambda Console (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SYMBOLS`).

4. **Configure EventBridge Trigger:**
   Add an **Amazon EventBridge** schedule trigger with a cron expression to run on saterday morning:
   ```text
   cron(0 5 ? * SAT *)
   ```

---

## 📄 License
MIT License
