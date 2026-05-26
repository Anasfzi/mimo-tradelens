"""Loop the engine over a basket of majors and rank by conviction.

Run with:
    export MIMO_API_KEY=...
    python examples/multi_asset_scan.py
"""
from rich.console import Console
from rich.table import Table

from mimo_tradelens import TradeLens

UNIVERSE = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "TON/USDT"]


def main() -> None:
    console = Console()
    lens = TradeLens()
    rows = []
    for sym in UNIVERSE:
        try:
            t = lens.analyze(sym, timeframe="4h", exchange="binance")
            rows.append((t.symbol, t.bias, t.conviction, t.entry, t.stop, t.targets))
        except Exception as exc:  # noqa: BLE001
            rows.append((sym, "ERROR", 0.0, None, None, []))
            console.print(f"[yellow]{sym}[/]: {exc}")

    rows.sort(key=lambda r: r[2], reverse=True)

    table = Table(title="MiMo TradeLens — multi-asset 4H scan", show_lines=True)
    table.add_column("symbol")
    table.add_column("bias")
    table.add_column("conv")
    table.add_column("entry")
    table.add_column("stop")
    table.add_column("TP1 / TP2")
    for sym, bias, conv, entry, stop, tps in rows:
        tp_str = " / ".join(f"{t}" for t in tps[:2]) if tps else "—"
        table.add_row(
            sym,
            f"[bold]{bias}[/]",
            f"{conv:.1f}",
            f"{entry}" if entry else "—",
            f"{stop}" if stop else "—",
            tp_str,
        )
    console.print(table)


if __name__ == "__main__":
    main()
