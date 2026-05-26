"""TradeLens orchestrator — fetch → render → vision → reason → thesis."""
from __future__ import annotations

from pathlib import Path

from .chart import render_chart
from .data import MarketSnapshot, fetch_market
from .mimo_client import MiMoClient
from .schema import TradeThesis, VisualRead


class TradeLens:
    """End-to-end pipeline: market data + chart + MiMo V2.5 → TradeThesis."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        vision_model: str | None = None,
        reasoning_model: str | None = None,
    ) -> None:
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if vision_model:
            kwargs["vision_model"] = vision_model
        if reasoning_model:
            kwargs["reasoning_model"] = reasoning_model
        self.client = MiMoClient(**kwargs)

    def analyze(
        self,
        symbol: str,
        timeframe: str = "4h",
        exchange: str = "binance",
        limit: int = 200,
        save_chart: str | Path | None = None,
    ) -> TradeThesis:
        """Run the full pipeline and return a structured TradeThesis."""
        snap = fetch_market(symbol, timeframe=timeframe, exchange=exchange, limit=limit)
        png = render_chart(
            snap.df, snap.symbol, snap.timeframe, out_path=save_chart
        )

        # Vision pass
        v_raw = self.client.visual_read(png, snap.symbol, snap.timeframe)
        visual = VisualRead(**v_raw)

        # Reasoning pass
        indicators = snap.indicator_summary()
        r_raw = self.client.reason(
            symbol=snap.symbol,
            timeframe=snap.timeframe,
            timestamp_utc=snap.timestamp_utc,
            indicators=indicators,
            visual_read=v_raw,
        )

        return _build_thesis(snap, visual, r_raw)


def _build_thesis(snap: MarketSnapshot, visual: VisualRead, r: dict) -> TradeThesis:
    """Coerce the model's reasoning output into a validated TradeThesis."""
    bias = (r.get("bias") or "NO_TRADE").upper()
    if bias not in {"LONG", "SHORT", "NO_TRADE"}:
        bias = "NO_TRADE"

    conviction = float(r.get("conviction") or 0.0)
    conviction = max(0.0, min(10.0, conviction))

    targets_raw = r.get("targets") or []
    if isinstance(targets_raw, (int, float)):
        targets_raw = [float(targets_raw)]
    targets = [float(x) for x in targets_raw if isinstance(x, (int, float))]

    entry = r.get("entry")
    stop = r.get("stop")
    if isinstance(entry, (int, float)):
        entry = float(entry)
    else:
        entry = None
    if isinstance(stop, (int, float)):
        stop = float(stop)
    else:
        stop = None

    return TradeThesis(
        symbol=snap.symbol,
        timeframe=snap.timeframe,
        timestamp_utc=snap.timestamp_utc,
        price=snap.last_price,
        atr=snap.atr,
        atr_pct=(snap.atr / snap.last_price) * 100.0 if snap.last_price else 0.0,
        bias=bias,  # type: ignore[arg-type]
        conviction=conviction,
        entry=entry,
        stop=stop,
        targets=targets,
        visual_read=visual,
        quantitative_confluence=list(r.get("quantitative_confluence") or []),
        contradictions=list(r.get("contradictions") or []),
        reasoning=str(r.get("reasoning") or ""),
    )
