"""Typer CLI."""
from __future__ import annotations

import json as jsonlib
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .chart import render_chart
from .core import TradeLens
from .data import fetch_market

app = typer.Typer(
    add_completion=False,
    help="MiMo TradeLens — AI-powered crypto trade analyst.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    symbol: str = typer.Argument(..., help="Trading pair, e.g. BTC/USDT"),
    tf: str = typer.Option("4h", "--tf", help="Timeframe: 5m / 15m / 1h / 4h / 1d / 1w"),
    exchange: str = typer.Option("binance", "--exchange", help="Any CCXT-supported exchange"),
    limit: int = typer.Option(200, "--limit", help="Number of candles to fetch"),
    output: str = typer.Option("tty", "--output", help="tty | json | markdown"),
    save_chart: str | None = typer.Option(None, "--save-chart", help="Path to save chart PNG"),
    model: str | None = typer.Option(None, "--model", help="Override reasoning model id"),
):
    """Run the full TradeLens pipeline on SYMBOL and print a trade thesis."""
    kwargs = {}
    if model:
        kwargs["reasoning_model"] = model
    lens = TradeLens(**kwargs)
    try:
        thesis = lens.analyze(
            symbol, timeframe=tf, exchange=exchange, limit=limit, save_chart=save_chart
        )
    except Exception as exc:
        console.print(f"[bold red]error:[/] {exc}")
        raise typer.Exit(1)

    if output == "json":
        typer.echo(thesis.model_dump_json(indent=2))
        return
    if output == "markdown":
        typer.echo(thesis.to_markdown())
        return

    _render_tty(thesis)


@app.command()
def chart(
    symbol: str = typer.Argument(..., help="Trading pair, e.g. BTC/USDT"),
    tf: str = typer.Option("4h", "--tf"),
    exchange: str = typer.Option("binance", "--exchange"),
    limit: int = typer.Option(200, "--limit"),
    out: str = typer.Option("chart.png", "--out", help="Output PNG path"),
):
    """Render a chart PNG (no AI call). Useful for inspecting what the model sees."""
    snap = fetch_market(symbol, timeframe=tf, exchange=exchange, limit=limit)
    render_chart(snap.df, snap.symbol, snap.timeframe, out_path=Path(out))
    console.print(f"[green]✓[/] saved {out}")


@app.command()
def quote(
    symbol: str = typer.Argument(..., help="Trading pair, e.g. BTC/USDT"),
    exchange: str = typer.Option("binance", "--exchange"),
):
    """Fetch the latest mid + spread for SYMBOL."""
    import ccxt  # local to keep startup fast for analyze/chart

    if not hasattr(ccxt, exchange):
        console.print(f"[red]Unknown exchange:[/] {exchange}")
        raise typer.Exit(1)
    ex = getattr(ccxt, exchange)({"enableRateLimit": True})
    t = ex.fetch_ticker(symbol)
    bid, ask, last = t.get("bid"), t.get("ask"), t.get("last")
    spread = (ask - bid) if (bid and ask) else None
    table = Table(title=f"{symbol} on {exchange}", show_header=False)
    table.add_row("last", f"{last}")
    table.add_row("bid", f"{bid}")
    table.add_row("ask", f"{ask}")
    if spread is not None:
        table.add_row("spread", f"{spread:.6f} ({spread / last * 100:.4f}%)")
    console.print(table)


# -------- TTY rendering --------


def _render_tty(thesis) -> None:
    color = {"LONG": "green", "SHORT": "red", "NO_TRADE": "yellow"}[thesis.bias]
    header = (
        f"[bold]{thesis.symbol}[/]  "
        f"[dim]{thesis.timeframe}[/]  "
        f"[dim]{thesis.timestamp_utc}[/]"
    )
    console.print(Panel(header, border_style="cyan"))

    rr = thesis.risk_reward()
    rr_str = f"{rr:.2f}" if rr else "—"
    summary = Table(show_header=False, box=None, padding=(0, 1))
    summary.add_row("[bold]VERDICT[/]", f"[{color}]{thesis.bias}[/]")
    summary.add_row("[bold]CONVICTION[/]", f"{thesis.conviction:.1f} / 10")
    summary.add_row("[bold]PRICE[/]", f"{thesis.price:,.4f}")
    summary.add_row("[bold]ATR[/]", f"{thesis.atr:.4f} ({thesis.atr_pct:.2f}%)")
    summary.add_row("[bold]R:R (TP1)[/]", rr_str)
    console.print(summary)

    console.print()
    console.rule("[bold]Visual read[/] (mimo-v2.5)")
    v = thesis.visual_read
    console.print(f"trend: [bold]{v.trend}[/]   visual bias: [bold]{v.visual_bias}[/]")
    for note in v.structure_notes:
        console.print(f" • {note}")
    for note in v.momentum_notes:
        console.print(f" • {note}")
    for note in v.volume_notes:
        console.print(f" • {note}")

    console.print()
    console.rule("[bold]Quantitative confluence[/] (mimo-v2.5-pro)")
    for x in thesis.quantitative_confluence:
        console.print(f" • {x}")

    if thesis.bias != "NO_TRADE":
        console.print()
        console.rule("[bold]Trade plan[/]")
        plan = Table(show_header=False, box=None, padding=(0, 1))
        plan.add_row("Entry", f"{thesis.entry}")
        plan.add_row("Stop", f"{thesis.stop}")
        for i, t in enumerate(thesis.targets, 1):
            plan.add_row(f"TP{i}", f"{t}")
        console.print(plan)

    if thesis.contradictions:
        console.print()
        console.rule("[bold]Contradictions[/]")
        for x in thesis.contradictions:
            console.print(f" • {x}")

    console.print()
    console.print("[dim italic]⚠ Research output. Not financial advice.[/]")


if __name__ == "__main__":
    app()
