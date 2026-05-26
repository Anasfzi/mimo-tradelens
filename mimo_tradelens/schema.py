"""Pydantic schemas for structured MiMo outputs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VisualRead(BaseModel):
    """Output of the vision pass — what mimo-v2.5 sees in the chart image."""

    trend: Literal["up", "down", "sideways"] = Field(
        ..., description="Dominant visual trend over the last ~50 bars."
    )
    structure_notes: list[str] = Field(
        default_factory=list,
        description="Bullet observations: support/resistance levels, breakouts, candle patterns.",
    )
    momentum_notes: list[str] = Field(
        default_factory=list,
        description="What the indicator panes (RSI, MACD, etc.) visually suggest.",
    )
    volume_notes: list[str] = Field(
        default_factory=list,
        description="Visual volume observations: dry tape, climax candles, accumulation, etc.",
    )
    visual_bias: Literal["LONG", "SHORT", "NEUTRAL"] = Field(
        ..., description="Net visual bias before quantitative confluence."
    )


class TradeThesis(BaseModel):
    """Final structured trade thesis from the reasoning pass."""

    symbol: str
    timeframe: str
    timestamp_utc: str
    price: float
    atr: float
    atr_pct: float

    bias: Literal["LONG", "SHORT", "NO_TRADE"]
    conviction: float = Field(..., ge=0.0, le=10.0)

    entry: float | None = None
    stop: float | None = None
    targets: list[float] = Field(default_factory=list)

    visual_read: VisualRead
    quantitative_confluence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(
        default_factory=list,
        description="Honest list of signals that work against the thesis.",
    )
    reasoning: str = Field("", description="Free-form deep-thinking trace.")

    # ---- helpers ----

    def risk_reward(self) -> float | None:
        if not (self.entry and self.stop and self.targets):
            return None
        risk = abs(self.entry - self.stop)
        reward = abs(self.targets[0] - self.entry)
        return round(reward / risk, 2) if risk > 0 else None

    def to_markdown(self) -> str:
        rr = self.risk_reward()
        rr_str = f"{rr:.2f}" if rr else "—"
        out = [
            f"# {self.symbol} {self.timeframe} — {self.bias} (conv {self.conviction:.1f}/10)",
            "",
            f"- **Time (UTC):** {self.timestamp_utc}",
            f"- **Price:** {self.price:,.4f}   ATR: {self.atr:.4f} ({self.atr_pct:.2f}%)",
            f"- **R:R (to TP1):** {rr_str}",
            "",
            "## Visual read (mimo-v2.5)",
        ]
        v = self.visual_read
        out.append(f"- Trend: **{v.trend}**, visual bias: **{v.visual_bias}**")
        for note in v.structure_notes + v.momentum_notes + v.volume_notes:
            out.append(f"  - {note}")
        out.append("")
        out.append("## Quantitative confluence (mimo-v2.5-pro)")
        out.extend(f"- {x}" for x in self.quantitative_confluence)
        out.append("")
        if self.bias != "NO_TRADE":
            out.append("## Trade plan")
            out.append(f"- Entry: `{self.entry}`")
            out.append(f"- Stop: `{self.stop}`")
            for i, t in enumerate(self.targets, 1):
                out.append(f"- TP{i}: `{t}`")
            out.append("")
        if self.contradictions:
            out.append("## Contradictions")
            out.extend(f"- {x}" for x in self.contradictions)
            out.append("")
        out.append("> ⚠ Research output. Not financial advice.")
        return "\n".join(out)
