import logging

from src import data_fetcher, notifier, report
from src.config import Config
from src.indicators import IndicatorBase, PriceBelowSMAIndicator, RSIIndicator
from src.scanner import scan_symbol


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ACTIVE_INDICATORS: list[IndicatorBase] = [
    PriceBelowSMAIndicator(window=20),
    PriceBelowSMAIndicator(window=50),
    PriceBelowSMAIndicator(window=200),
    RSIIndicator(period=14, oversold=35.0),
]


def run_pipeline(config: Config):
    """Scan every configured symbol and send one Telegram report if anything fired.

    Symbols that fail to load are listed in the report rather than skipped
    silently. Raises if the report cannot be delivered.
    """
    sections: list[str] = []
    failed_symbols: list[str] = []

    for symbol in config.symbols:
        try:
            market_history = data_fetcher.fetch_market_history(
                symbol, config.history_period
            )
            if market_history.empty:
                logger.warning("%s: no market data returned", symbol)
                failed_symbols.append(symbol)
                continue

            results = scan_symbol(symbol, market_history, ACTIVE_INDICATORS)
            if results:
                latest_price = float(market_history["Close"].iloc[-1])
                sections.append(
                    report.format_symbol_report(symbol, latest_price, results)
                )
        except Exception:
            logger.exception("Error processing %s", symbol)
            failed_symbols.append(symbol)

    if failed_symbols:
        sections.append(report.format_failures(failed_symbols))

    if not sections:
        logger.info("No indicators triggered today.")
        return

    for message in notifier.split_message(sections, report.REPORT_SEPARATOR):
        logger.info("Sending report:\n%s", report.to_plain_text(message))
        notifier.send_telegram_alert(
            config.telegram_bot_token, config.telegram_chat_id, message
        )

    logger.info("Summary report sent successfully.")


def lambda_handler(_event: dict, _context: object) -> dict[str, int | str]:
    run_pipeline(Config.from_env())
    return {"statusCode": 200, "body": "Pipeline executed successfully"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_pipeline(Config.from_env())
