"""Render a chart PNG without the AI call. Useful for previewing the input the
vision model receives.

Run with:
    python examples/chart_only.py
"""
from pathlib import Path

from mimo_tradelens.chart import render_chart
from mimo_tradelens.data import fetch_market


def main() -> None:
    snap = fetch_market("BTC/USDT", timeframe="4h", exchange="binance", limit=200)
    out = Path("btc_4h_chart.png")
    render_chart(snap.df, snap.symbol, snap.timeframe, out_path=out)
    print(f"saved {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
