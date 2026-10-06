from src import data_fetcher, notifier
from src.config import Config
from src.indicators import IndicatorBase, RSIIndicator, SMACrossIndicator


def run_pipeline():
    Config.validate()

    active_indicators: list[IndicatorBase] = [
        SMACrossIndicator(window=20, threshold_percentage=0.0),  # SMA 20
        SMACrossIndicator(window=50, threshold_percentage=0.0),  # SMA 50
        SMACrossIndicator(window=200, threshold_percentage=0.0),  # SMA 200
        RSIIndicator(period=14, oversold=35.0)  # RSI Oversold
    ]

    messages_to_send: list[str] = []

    for symbol in Config.SYMBOLS:
        try:
            market_history = data_fetcher.fetch_market_history(symbol)
            if market_history.empty:
                continue

            symbol_alerts: list[str] = []
            latest_price = round(float(market_history['Close'].iloc[-1]), 2)

            # הרצת כל האינדיקטורים על המניה
            for indicator in active_indicators:
                result = indicator.evaluate(market_history)
                if result:
                    symbol_alerts.append(f"  • *{result['indicator']}:* {result['message']}")

            # אם לפחות אינדיקטור אחד קפץ - בונים הודעה מאוגדת למניה הזו
            if symbol_alerts:
                formatted_msg = (
                    f"📊 *Market Summary for {symbol}*\n"
                    f"💵 *Current Price:* ${latest_price}\n"
                    f"⚠️ *Triggered Indicators:*\n" +
                    "\n".join(symbol_alerts)
                )
                messages_to_send.append(formatted_msg)

        except Exception as error:
            print(f"Error processing {symbol}: {error}")

    if messages_to_send:
        full_report = "\n\n───────────────\n\n".join(messages_to_send)
        notifier.send_telegram_alert(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID, full_report)
        print("Summary report sent successfully.")
    else:
        print("No indicators triggered today.")

    for message in messages_to_send:
        print(message)
        print('\n')


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    run_pipeline()
    return {"statusCode": Config.SUCCESS_HTTP_STATUS_CODE, "body": "Pipeline executed successfully"}


if __name__ == "__main__":
    run_pipeline()
