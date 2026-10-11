import pandas as pd
import pytest

import app
from src.config import Config, parse_symbols
from src.indicators import IndicatorResult, PriceBelowSMAIndicator
from src.notifier import split_message
from src.report import format_symbol_report
from src.scanner import scan_symbol


@pytest.fixture
def config() -> Config:
    return Config(
        telegram_bot_token="token",
        telegram_chat_id="chat",
        symbols=("AAPL", "BAD"),
        history_period="1y",
    )


def test_parse_symbols_drops_blanks_and_uppercases():
    assert parse_symbols(" aapl,,MSFT , ") == ("AAPL", "MSFT")


def test_from_env_requires_symbols(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("SYMBOLS", " , ")

    with pytest.raises(ValueError, match="SYMBOLS"):
        Config.from_env()


def test_format_symbol_report_escapes_html():
    results = [IndicatorResult(indicator="SMA_20", message="a < b & c")]

    report = format_symbol_report("BRK_B", 123.456, results)

    assert "a &lt; b &amp; c" in report
    assert "$123.46" in report
    assert "BRK_B" in report


def test_scan_symbol_skips_indicators_without_enough_history():
    history = pd.DataFrame({"Close": [10.0] * 19 + [5.0]})
    indicators = [PriceBelowSMAIndicator(window=20), PriceBelowSMAIndicator(200)]

    results = scan_symbol("AAPL", history, indicators)

    assert [result.indicator for result in results] == ["SMA_20"]


def test_split_message_packs_sections_within_limit():
    sections = ["a" * 4, "b" * 4, "c" * 4]

    assert split_message(sections, "--", max_length=10) == ["aaaa--bbbb", "cccc"]


def test_split_message_keeps_oversized_section_whole():
    assert split_message(["x" * 20, "y"], "--", max_length=10) == ["x" * 20, "y"]


def test_run_pipeline_reports_failed_symbols(monkeypatch, config):
    def fake_fetch(symbol, period):
        if symbol == "BAD":
            raise RuntimeError("boom")
        return pd.DataFrame({"Close": [10.0] * 30})

    sent: list[str] = []
    monkeypatch.setattr(app.data_fetcher, "fetch_market_history", fake_fetch)
    monkeypatch.setattr(
        app.notifier,
        "send_telegram_alert",
        lambda token, chat_id, message: sent.append(message),
    )

    app.run_pipeline(config)

    assert len(sent) == 1
    assert "Failed to scan:</b> BAD" in sent[0]


def test_run_pipeline_sends_nothing_when_quiet(monkeypatch, config):
    sent: list[str] = []
    monkeypatch.setattr(
        app.data_fetcher,
        "fetch_market_history",
        lambda symbol, period: pd.DataFrame({"Close": [10.0 + i for i in range(30)]}),
    )
    monkeypatch.setattr(
        app.notifier,
        "send_telegram_alert",
        lambda token, chat_id, message: sent.append(message),
    )

    app.run_pipeline(config)

    assert sent == []
