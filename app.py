from src.config import Config
from src.data_fetcher import fetch_market_data
from src.notifier import send_telegram_alert
from src.indicators.base import BaseIndicator
from src.indicators import RSIIndicator, SMACrossIndicator


def run_pipeline():
    Config.validate()

    active_indicators: list[BaseIndicator] = [
        SMACrossIndicator(window=20, threshold_pct=0.01),  # SMA 20
        SMACrossIndicator(window=50, threshold_pct=0.02),  # SMA 50
        RSIIndicator(period=14, oversold=35.0)  # RSI Oversold
    ]

    alerts = []

    for symbol in Config.SYMBOLS:
        try:
            df = fetch_market_data(symbol)
            if df.empty:
                continue

            for indicator in active_indicators:
                result = indicator.evaluate(df)

                if result:
                    alert_message = (
                        f"🚨 *Market Alert: {symbol}*\n"
                        f"• *Indicator:* {result['indicator']}\n"
                        f"• *Details:* {result['message']}\n"
                    )
                    alerts.append(alert_message)

        except Exception as error:
            print(f"Error processing {symbol}: {error}")

    if alerts:
        full_message = "\n\n".join(alerts)
        send_telegram_alert(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID, full_message)
        print(f"Sent {len(alerts)} alerts successfully.")

    else:
        print("No alerts triggered today.")


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    run_pipeline()
    return {"statusCode": 200, "body": "Pipeline executed successfully"}


if __name__ == "__main__":
    run_pipeline()
