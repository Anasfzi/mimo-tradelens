"""Bread-and-butter Bitcoin 4H setup analysis.

Run with:
    export MIMO_API_KEY=...
    python examples/btc_4h.py
"""
from mimo_tradelens import TradeLens


def main() -> None:
    lens = TradeLens()
    thesis = lens.analyze("BTC/USDT", timeframe="4h", exchange="binance")
    print(thesis.to_markdown())


if __name__ == "__main__":
    main()
