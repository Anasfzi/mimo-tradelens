"""Smoke tests — run with `pytest` from the repo root.

These tests intentionally do NOT call the MiMo API. They validate the
data pipeline, chart renderer, and schema serialization in isolation so
contributors without an API key can still run the test suite.
"""
from __future__ import annotations

import json

import pandas as pd

from mimo_tradelens.chart import render_chart
from mimo_tradelens.data import fetch_market, MarketSnapshot
from mimo_tradelens.schema import TradeThesis, VisualRead


def test_visual_read_schema_round_trip():
    v = VisualRead(
        trend="up",
        structure_notes=["bouncing off 100 EMA at $30k"],
        momentum_notes=["RSI 55, healthy"],
        volume_notes=["climax candle two bars ago"],
        visual_bias="LONG",
    )
    parsed = VisualRead(**json.loads(v.model_dump_json()))
    assert parsed.visual_bias == "LONG"
    assert parsed.structure_notes == ["bouncing off 100 EMA at $30k"]


def test_thesis_markdown_includes_trade_plan():
    v = VisualRead(trend="up", visual_bias="LONG")
    t = TradeThesis(
        symbol="BTC/USDT",
        timeframe="4h",
        timestamp_utc="2026-05-26 05:00 UTC",
        price=77840.0,
        atr=1210.0,
        atr_pct=1.55,
        bias="LONG",
        conviction=6.3,
        entry=77840.0,
        stop=76400.0,
        targets=[80440.0, 82800.0],
        visual_read=v,
        quantitative_confluence=["RSI 47 neutral", "vol 1.4x"],
        contradictions=["EMA50 < EMA200, counter-trend long"],
    )
    md = t.to_markdown()
    assert "BTC/USDT" in md
    assert "LONG" in md
    assert "Entry" in md
    assert "Contradictions" in md
    assert "EMA50 < EMA200" in md
    assert t.risk_reward() is not None and t.risk_reward() > 1.5


def test_thesis_no_trade_skips_plan_section():
    v = VisualRead(trend="sideways", visual_bias="NEUTRAL")
    t = TradeThesis(
        symbol="ETH/USDT",
        timeframe="1h",
        timestamp_utc="2026-05-26 05:00 UTC",
        price=3000.0,
        atr=20.0,
        atr_pct=0.66,
        bias="NO_TRADE",
        conviction=2.1,
        visual_read=v,
        quantitative_confluence=["chop"],
    )
    md = t.to_markdown()
    assert "NO_TRADE" in md
    assert "Trade plan" not in md
    assert t.risk_reward() is None


def _add_indicators(df):
    """Helper for tests — add the indicator panel matching what render_chart expects."""
    import pandas_ta_classic as ta
    df = df.copy()
    df["ema20"] = ta.ema(df["close"], 20)
    df["ema50"] = ta.ema(df["close"], 50)
    df["ema200"] = ta.ema(df["close"], 200)
    df["rsi"] = ta.rsi(df["close"], 14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], 14)
    df = df.join(ta.macd(df["close"]))
    df = df.join(ta.bbands(df["close"], length=20, std=2))
    df = df.join(ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0))
    # Supertrend leaves NaN in the side-specific column that's not active —
    # only drop rows where the *required* columns are NaN.
    needed = ["ema20", "ema50", "ema200", "rsi", "atr",
              "MACDh_12_26_9", "BBU_20_2.0", "BBL_20_2.0",
              "SUPERT_10_3.0", "SUPERTd_10_3.0"]
    return df.dropna(subset=needed)


def test_chart_render_outputs_valid_png(tmp_path):
    """Render a chart from synthetic OHLCV; verify PNG magic bytes."""
    import numpy as np
    rng = pd.date_range("2026-01-01", periods=300, freq="4h")
    np.random.seed(42)
    returns = np.random.randn(300) * 0.005
    prices = 30000 * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.003,
        "low": prices * 0.997,
        "close": prices,
        "volume": np.random.randint(80, 200, 300),
    }, index=rng)
    df.index.name = "ts"

    df = _add_indicators(df)
    assert len(df) > 50, f"expected > 50 rows after dropna, got {len(df)}"

    out = tmp_path / "synthetic.png"
    png = render_chart(df, "TEST/USDT", "4h", out_path=out)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert out.exists() and out.stat().st_size > 1000


def test_market_snapshot_indicator_summary():
    """Validate that indicator_summary returns the expected keys."""
    import numpy as np
    rng = pd.date_range("2026-01-01", periods=300, freq="4h")
    np.random.seed(7)
    returns = np.random.randn(300) * 0.004
    prices = 30000 * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.003,
        "low": prices * 0.997,
        "close": prices,
        "volume": np.random.randint(80, 200, 300),
    }, index=rng)
    df.index.name = "ts"
    df = _add_indicators(df)
    assert len(df) > 50

    snap = MarketSnapshot(
        symbol="TEST/USDT", timeframe="4h", exchange="test",
        timestamp_utc="2026-05-26 05:00 UTC",
        df=df, last_price=float(df["close"].iloc[-1]),
        atr=float(df["atr"].iloc[-1]),
    )
    s = snap.indicator_summary()
    for key in ("price", "ema20", "ema50", "rsi14", "macd_hist", "atr14", "vol_ratio_vs_20"):
        assert key in s, f"missing {key}"
