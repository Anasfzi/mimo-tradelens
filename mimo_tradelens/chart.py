"""Render an annotated PNG chart that the vision model can read."""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.facecolor"] = "#0e1117"
plt.rcParams["figure.facecolor"] = "#0e1117"
plt.rcParams["savefig.facecolor"] = "#0e1117"
plt.rcParams["text.color"] = "#e6e6e6"
plt.rcParams["axes.labelcolor"] = "#e6e6e6"
plt.rcParams["xtick.color"] = "#9aa0a6"
plt.rcParams["ytick.color"] = "#9aa0a6"
plt.rcParams["grid.color"] = "#222831"
plt.rcParams["grid.alpha"] = 0.4


def render_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    out_path: Path | str | None = None,
    bars: int = 120,
) -> bytes:
    """Render a multi-pane TradingView-style chart and return PNG bytes.

    Layout (top to bottom):
      1. Price candles + EMA20/EMA50/EMA200 + Bollinger Bands + Supertrend
      2. Volume histogram
      3. RSI(14) with 30/70 lines
      4. MACD(12,26,9) histogram + signal/MACD lines
    """
    sub = df.tail(bars).copy()

    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    gs = GridSpec(4, 1, figure=fig, height_ratios=[3.2, 1, 1, 1.2])
    ax_p = fig.add_subplot(gs[0])
    ax_v = fig.add_subplot(gs[1], sharex=ax_p)
    ax_r = fig.add_subplot(gs[2], sharex=ax_p)
    ax_m = fig.add_subplot(gs[3], sharex=ax_p)

    # --- 1. Price + overlays
    width = 0.6 * (mdates.date2num(sub.index[1]) - mdates.date2num(sub.index[0]))
    for idx, row in sub.iterrows():
        color = "#26a69a" if row["close"] >= row["open"] else "#ef5350"
        ax_p.vlines(idx, row["low"], row["high"], color=color, linewidth=0.8)
        ax_p.add_patch(
            plt.Rectangle(
                (mdates.date2num(idx) - width / 2, min(row["open"], row["close"])),
                width,
                abs(row["close"] - row["open"]) or (row["close"] * 0.0001),
                color=color,
            )
        )
    ax_p.plot(sub.index, sub["ema20"], color="#fbbf24", linewidth=1.0, label="EMA 20")
    ax_p.plot(sub.index, sub["ema50"], color="#3b82f6", linewidth=1.2, label="EMA 50")
    ax_p.plot(sub.index, sub["ema200"], color="#a78bfa", linewidth=1.2, label="EMA 200")
    ax_p.plot(sub.index, sub["BBU_20_2.0"], color="#64748b", linewidth=0.8, alpha=0.6)
    ax_p.plot(sub.index, sub["BBL_20_2.0"], color="#64748b", linewidth=0.8, alpha=0.6)
    ax_p.fill_between(
        sub.index, sub["BBL_20_2.0"], sub["BBU_20_2.0"],
        color="#64748b", alpha=0.05,
    )
    ax_p.plot(sub.index, sub["SUPERT_10_3.0"], color="#f97316", linewidth=0.9, alpha=0.7, label="Supertrend")

    last = sub.iloc[-1]
    ax_p.axhline(last["close"], color="#e6e6e6", linewidth=0.6, linestyle="--", alpha=0.5)
    ax_p.text(
        sub.index[-1], last["close"], f"  {last['close']:.4f}",
        va="center", color="#e6e6e6", fontsize=9,
    )
    ax_p.set_title(f"{symbol}   {timeframe}    last close {last['close']:.4f}", color="#e6e6e6")
    ax_p.legend(loc="upper left", fontsize=8, framealpha=0.6)
    ax_p.grid(True)

    # --- 2. Volume
    colors_v = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(sub["close"], sub["open"])]
    ax_v.bar(sub.index, sub["volume"], color=colors_v, width=width, align="center")
    ax_v.set_ylabel("Vol", fontsize=8)
    ax_v.grid(True)

    # --- 3. RSI
    ax_r.plot(sub.index, sub["rsi"], color="#22d3ee", linewidth=1.0)
    ax_r.axhline(70, color="#ef5350", linewidth=0.6, alpha=0.5)
    ax_r.axhline(30, color="#26a69a", linewidth=0.6, alpha=0.5)
    ax_r.axhline(50, color="#9aa0a6", linewidth=0.5, linestyle="--", alpha=0.4)
    ax_r.fill_between(sub.index, 70, sub["rsi"], where=sub["rsi"] >= 70, color="#ef5350", alpha=0.15)
    ax_r.fill_between(sub.index, 30, sub["rsi"], where=sub["rsi"] <= 30, color="#26a69a", alpha=0.15)
    ax_r.set_ylim(0, 100)
    ax_r.set_ylabel("RSI 14", fontsize=8)
    ax_r.grid(True)

    # --- 4. MACD
    ax_m.bar(
        sub.index, sub["MACDh_12_26_9"],
        color=["#26a69a" if x >= 0 else "#ef5350" for x in sub["MACDh_12_26_9"]],
        width=width, align="center",
    )
    ax_m.plot(sub.index, sub["MACD_12_26_9"], color="#3b82f6", linewidth=1.0, label="MACD")
    ax_m.plot(sub.index, sub["MACDs_12_26_9"], color="#fbbf24", linewidth=1.0, label="signal")
    ax_m.axhline(0, color="#9aa0a6", linewidth=0.5, alpha=0.5)
    ax_m.set_ylabel("MACD 12/26/9", fontsize=8)
    ax_m.legend(loc="upper left", fontsize=7, framealpha=0.6)
    ax_m.grid(True)

    ax_m.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_m.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate(rotation=30, ha="right")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    png = buf.getvalue()

    if out_path is not None:
        Path(out_path).write_bytes(png)
    return png
