"""Market data + indicator pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import ccxt
import pandas as pd
import pandas_ta_classic as ta


@dataclass
class MarketSnapshot:
    """Numeric snapshot of a symbol at the latest closed bar."""

    symbol: str
    timeframe: str
    exchange: str
    timestamp_utc: str
    df: pd.DataFrame  # full OHLCV + indicators
    last_price: float
    atr: float

    def indicator_summary(self) -> dict[str, float | str]:
        """Compact dict of last-bar indicators for the reasoning prompt."""
        last = self.df.iloc[-1]
        return {
            "price": float(last["close"]),
            "ema20": float(last["ema20"]),
            "ema50": float(last["ema50"]),
            "ema200": float(last["ema200"]),
            "rsi14": float(last["rsi"]),
            "macd_hist": float(last["MACDh_12_26_9"]),
            "atr14": float(last["atr"]),
            "bb_upper": float(last["BBU_20_2.0"]),
            "bb_lower": float(last["BBL_20_2.0"]),
            "supertrend_dir": int(last["SUPERTd_10_3.0"]),
            "supertrend_level": float(last["SUPERT_10_3.0"]),
            "vol_ratio_vs_20": float(
                last["volume"] / self.df["volume"].iloc[-21:-1].mean()
            ),
        }


def fetch_market(
    symbol: str,
    timeframe: str = "4h",
    exchange: str = "binance",
    limit: int = 200,
) -> MarketSnapshot:
    """Fetch OHLCV from a CCXT exchange and compute the standard indicator panel."""
    if not hasattr(ccxt, exchange):
        raise ValueError(f"Unknown exchange: {exchange!r}")
    ex = getattr(ccxt, exchange)({"enableRateLimit": True})
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not raw:
        raise RuntimeError(f"No OHLCV returned for {symbol} on {exchange}")

    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts")

    df["ema20"] = ta.ema(df["close"], 20)
    df["ema50"] = ta.ema(df["close"], 50)
    df["ema200"] = ta.ema(df["close"], 200)
    df["rsi"] = ta.rsi(df["close"], 14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], 14)
    df = df.join(ta.macd(df["close"]))
    df = df.join(ta.bbands(df["close"], length=20, std=2))
    df = df.join(
        ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0)
    )

    return MarketSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange,
        timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        df=df,
        last_price=float(df["close"].iloc[-1]),
        atr=float(df["atr"].iloc[-1]),
    )
