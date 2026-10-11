import html
import logging
import re

import pandas as pd

from src import data_fetcher, notifier
from src.config import Config
from src.indicators import (
    IndicatorBase,
    IndicatorResult,
    PriceBelowSMAIndicator,
    RSIIndicator,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ACTIVE_INDICATORS: list[IndicatorBase] = [
    PriceBelowSMAIndicator(window=20),
    PriceBelowSMAIndicator(window=50),
    PriceBelowSMAIndicator(window=200),
    RSIIndicator(period=14, oversold=35.0),
]

REPORT_SEPARATOR = "\n\n───────────────\n\n"


def scan_symbol(
    symbol: str,
    market_history: pd.DataFrame,
    indicators: list[IndicatorBase],
) -> list[IndicatorResult]:
    """Run every indicator on one symbol's history and return those that fired."""
    results: list[IndicatorResult] = []
    for indicator in indicators:
        if len(market_history) < indicator.min_history:
            logger.warning(
                "%s: only %d rows of history, %s needs %d; skipping it",
                symbol,
                len(market_history),
                type(indicator).__name__,
                indicator.min_history,
            )
            continue

        result = indicator.evaluate(market_history)
        if result is not None:
            results.append(result)
    return results


def format_symbol_report(
    symbol: str, latest_price: float, results: list[IndicatorResult]
) -> str:
    """Format one symbol's triggered indicators as a Telegram HTML section."""
    alert_lines = "\n".join(
        f"  • <b>{html.escape(result.indicator)}:</b> {html.escape(result.message)}"
        for result in results
    )
    return (
        f"📊 <b>Market Summary for {html.escape(symbol)}</b>\n"
        f"💵 <b>Current Price:</b> ${latest_price:.2f}\n"
        f"⚠️ <b>Triggered Indicators:</b>\n"
        f"{alert_lines}"
    )


def format_failures(failed_symbols: list[str]) -> str:
    """Format the symbols that could not be scanned as a Telegram HTML section."""
    return f"❌ <b>Failed to scan:</b> {html.escape(', '.join(failed_symbols))}"


def to_plain_text(message: str) -> str:
    """Strip Telegram HTML markup so a message is readable in the logs."""
    return html.unescape(re.sub(r"<[^>]+>", "", message))


def run_pipeline(config: Config) -> None:
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
                sections.append(format_symbol_report(symbol, latest_price, results))
        except Exception:
            logger.exception("Error processing %s", symbol)
            failed_symbols.append(symbol)

    if failed_symbols:
        sections.append(format_failures(failed_symbols))

    if not sections:
        logger.info("No indicators triggered today.")
        return

    for message in notifier.split_message(sections, REPORT_SEPARATOR):
        logger.info("Sending report:\n%s", to_plain_text(message))
        notifier.send_telegram_alert(
            config.telegram_bot_token, config.telegram_chat_id, message
        )
    logger.info("Summary report sent successfully.")


def lambda_handler(_event: dict, _context: object) -> dict[str, int | str]:
    """AWS Lambda entry point."""
    run_pipeline(Config.from_env())
    return {"statusCode": 200, "body": "Pipeline executed successfully"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_pipeline(Config.from_env())
