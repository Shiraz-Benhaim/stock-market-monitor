import html
import re

from src.indicators import IndicatorResult

REPORT_SEPARATOR = "\n\n───────────────\n\n"


def format_symbol_report(
    symbol: str, latest_price: float, results: list[IndicatorResult]
) -> str:
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
    return f"❌ <b>Failed to scan:</b> {html.escape(', '.join(failed_symbols))}"


def to_plain_text(message: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", message))
