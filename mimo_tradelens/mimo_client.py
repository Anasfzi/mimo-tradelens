"""Wrapper around the OpenAI-compatible Xiaomi MiMo API."""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from openai import OpenAI


DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_VISION_MODEL = "mimo-v2.5"
DEFAULT_REASONING_MODEL = "mimo-v2.5-pro"


@dataclass
class MiMoClient:
    """Thin OpenAI-compatible client for both vision and reasoning passes.

    Uses the OpenAI Python SDK because the MiMo platform is fully OpenAI-API compatible
    (see https://platform.xiaomimimo.com/docs).
    """

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    vision_model: str = DEFAULT_VISION_MODEL
    reasoning_model: str = DEFAULT_REASONING_MODEL

    def __post_init__(self) -> None:
        api_key = self.api_key or os.environ.get("MIMO_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MIMO_API_KEY missing. Get one at https://platform.xiaomimimo.com "
                "and set it as the MIMO_API_KEY environment variable."
            )
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)

    # ---- low-level chat completion ----

    def _chat(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
        )
        return resp.choices[0].message.content or ""

    # ---- vision pass ----

    def visual_read(
        self,
        chart_png: bytes,
        symbol: str,
        timeframe: str,
        instruction: str | None = None,
    ) -> dict:
        """Ask the multimodal model what it sees in the chart.

        Returns a dict matching the VisualRead schema.
        """
        b64 = base64.b64encode(chart_png).decode()
        sys = (
            "You are MiMo, an AI assistant developed by Xiaomi. "
            "You are an expert technical chart reader. "
            "Read the provided crypto trading chart and return STRICT JSON. "
            "Do not add commentary outside the JSON object."
        )
        user_text = instruction or (
            f"Symbol: {symbol}    Timeframe: {timeframe}\n\n"
            "Look at the chart and return a JSON object with keys:\n"
            '{ "trend": "up" | "down" | "sideways",\n'
            '  "structure_notes": [string, ...],   // S/R levels, breakouts, candle patterns\n'
            '  "momentum_notes": [string, ...],    // RSI / MACD visual cues, divergences\n'
            '  "volume_notes": [string, ...],      // volume confirmation, climax, dry tape\n'
            '  "visual_bias": "LONG" | "SHORT" | "NEUTRAL" }\n\n'
            "Be specific about price levels, candle indices, and visual evidence. "
            "Be honest — if the picture is ambiguous, return NEUTRAL."
        )
        messages = [
            {"role": "system", "content": sys},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ]
        text = self._chat(self.vision_model, messages, max_tokens=1200, temperature=0.3)
        return _parse_json_blob(text)

    # ---- reasoning pass ----

    def reason(
        self,
        symbol: str,
        timeframe: str,
        timestamp_utc: str,
        indicators: dict,
        visual_read: dict,
    ) -> dict:
        """Fuse the visual read with quantitative indicators into a TradeThesis."""
        sys = (
            "You are MiMo, an AI assistant developed by Xiaomi. "
            "You are a senior crypto market analyst. "
            "Combine a visual chart read with quantitative indicator values to "
            "produce a structured trade thesis. Always include CONTRADICTING signals — "
            "do not produce one-sided narratives. Return STRICT JSON only."
        )
        user = (
            f"Symbol: {symbol}    Timeframe: {timeframe}    UTC: {timestamp_utc}\n\n"
            "Visual read (from vision model):\n"
            f"{json.dumps(visual_read, indent=2)}\n\n"
            "Quantitative indicators (latest closed bar):\n"
            f"{json.dumps(indicators, indent=2)}\n\n"
            "Return JSON with keys:\n"
            '{ "bias": "LONG" | "SHORT" | "NO_TRADE",\n'
            '  "conviction": float in [0,10],\n'
            '  "entry": float | null,\n'
            '  "stop": float | null,\n'
            '  "targets": [float, float],     // TP1, TP2; empty if NO_TRADE\n'
            '  "quantitative_confluence": [string, ...],\n'
            '  "contradictions": [string, ...],\n'
            '  "reasoning": string }\n\n'
            "Rules:\n"
            "- Stop must be invalidation-based (beyond a swing low/high or EMA), not an arbitrary %.\n"
            "- TP1 should target ~1.5R-2R; TP2 should target ~3R if structurally supported.\n"
            "- If visual_bias and quantitative signals disagree strongly, output NO_TRADE.\n"
            "- Always include at least one entry in `contradictions` (intellectual honesty).\n"
        )
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ]
        text = self._chat(self.reasoning_model, messages, max_tokens=2000, temperature=0.4)
        return _parse_json_blob(text)


# ---------------- helpers ----------------


def _parse_json_blob(text: str) -> dict:
    """Best-effort extraction of a JSON object from a model response."""
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fence
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip("`").strip()
    # find outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Model did not return JSON. Got:\n{text[:400]}")
    blob = text[start : end + 1]
    return json.loads(blob)
