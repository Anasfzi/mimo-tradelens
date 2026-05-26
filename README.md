# MiMo TradeLens

> AI-powered crypto trade analyst — turns OHLCV charts into structured, multi-modal trade theses using **Xiaomi MiMo V2.5**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MiMo V2.5](https://img.shields.io/badge/Powered%20by-Xiaomi%20MiMo%20V2.5-orange.svg)](https://platform.xiaomimimo.com)

MiMo TradeLens fetches live OHLCV data from any major crypto exchange via CCXT, renders an annotated technical chart, then routes it through Xiaomi MiMo V2.5's vision + reasoning models to produce a structured trade thesis: directional bias, conviction score, entry/stop/target levels, and an honest assessment of contradicting signals.

It is built to **demonstrate MiMo V2.5's two strongest capabilities in a single end-to-end agent loop**:

1. **`mimo-v2.5` (Omni / Full-modal)** — looks at the rendered chart image and extracts visual structure (trend, support/resistance, candle patterns).
2. **`mimo-v2.5-pro` (Deep Thinking)** — fuses the visual reading with quantitative indicators (RSI, MACD, ATR, EMAs) and produces a final trade thesis with explicit reasoning.

The result is shipped back to the user as JSON, Markdown, or printed to a CLI-friendly TTY.

---

## Why this exists

Every retail trader's TradingView chart contains the same information, yet the experience of reading it is wildly inconsistent. A noisy session, a missed candle, or simple cognitive bias can turn a clean setup into a losing trade.

MiMo TradeLens treats chart-reading as a **vision + reasoning task**, not a numeric one:

- A traditional indicator script can tell you "RSI is 27."
- A vision-language model can tell you "RSI is 27, **but** price made a higher low at the previous swing while RSI made a lower low — that's a textbook bullish divergence inside an oversold zone."

The latter is what experienced traders actually look for. MiMo V2.5's **deep-thinking + multi-modal** capabilities make this kind of reading possible from a single API call.

---

## Quick start

```bash
git clone https://github.com/Anasfzi/mimo-tradelens
cd mimo-tradelens
pip install -e .

export MIMO_API_KEY="your-mimo-api-key"     # from https://platform.xiaomimimo.com

# Quickest possible run — analyze BTC 4H using Binance data
mimo-tradelens analyze BTC/USDT --tf 4h
```

Output (truncated):

```
============================================================
MiMo TradeLens — BTC/USDT 4H — 2026-05-26 05:00 UTC
============================================================

VERDICT:    LONG (lean)
CONVICTION: 6.3 / 10
PRICE:      $77,840   ATR: $1,210 (1.55%)

VISUAL READ (mimo-v2.5):
- Price reclaimed 50 EMA on the most recent 4H bar with above-average volume.
- Two-week range bottom at $76,400 has been retested 3× and held — clean S/R level.
- Bullish divergence: lower low in price, higher low in RSI from the May 22 swing.
- Bollinger Bands tightened over the last 12 bars; expansion is forming on the upside.

QUANTITATIVE CONFLUENCE (mimo-v2.5-pro):
- Trend: EMA50 < EMA200 on 4H — counter-trend long. Reduces conviction.
- Momentum: RSI 47 (neutral, room to run); MACD histogram crossing zero.
- Volume: last bar 1.4× 20-bar SMA — confirms the EMA reclaim.
- ATR placement: stop at $76,400 = 1.86% risk; TP1 at +2.5R is feasible inside daily range.

TRADE PLAN:
- Entry:  $77,840  (market) or limit pullback into $77,200
- Stop:   $76,400   (-1.86%)
- TP1:    $80,440   (+3.34%, 1.8R)
- TP2:    $82,800   (+6.37%, 3.4R)

CONTRADICTING SIGNALS:
- 4H trend is still down (EMA50 < EMA200). This is a counter-trend mean-reversion long.
- BTC dominance ticked up overnight — alts likely to underperform if BTC stalls.
- If $76,400 fails, expect a flush to $74,800 (next weekly support).

⚠ Research output. Not financial advice. Always size risk before entering.
```

---

## Architecture

```
┌─────────────────┐  OHLCV   ┌────────────────┐
│  CCXT (Binance) ├──────────► chart.py       │
│  Bybit / OKX /  │           │ matplotlib     │
│  Bitget / etc.  │           │ + indicators   │
└─────────────────┘           └───────┬────────┘
                                      │ PNG bytes
                                      ▼
                              ┌────────────────┐
                              │ mimo-v2.5      │  <-- vision pass
                              │ (Omni / VL)    │      "describe what you see"
                              └───────┬────────┘
                                      │ visual_read JSON
                                      ▼
                              ┌────────────────┐
                              │ mimo-v2.5-pro  │  <-- reasoning pass
                              │ (Deep Thinking)│      vision + indicators ->
                              └───────┬────────┘      structured trade thesis
                                      │
                                      ▼
                              ┌────────────────┐
                              │ TradeThesis    │
                              │ (Pydantic)     │
                              └────────────────┘
```

Two model calls, one structured output. Both endpoints are OpenAI-compatible — you swap them with any other model by changing the base URL.

---

## CLI reference

```bash
# Most common: full analysis
mimo-tradelens analyze SYMBOL/QUOTE [options]

# Just render a chart (no AI call) — useful for inspecting what the model sees
mimo-tradelens chart SYMBOL/QUOTE --tf 1h --out chart.png

# Quote-only check (live mid + spread)
mimo-tradelens quote SYMBOL/QUOTE
```

| Option | Default | Description |
|---|---|---|
| `--tf` | `4h` | Timeframe: `5m`, `15m`, `1h`, `4h`, `1d`, `1w` |
| `--exchange` | `binance` | Any CCXT-supported exchange |
| `--limit` | `200` | Number of candles to fetch (max ~1000) |
| `--model` | `mimo-v2.5` / `mimo-v2.5-pro` | Override either model |
| `--output` | `tty` | `tty`, `json`, `markdown` |
| `--save-chart` | _(off)_ | Path to save the chart PNG used for vision |

---

## Python API

```python
from mimo_tradelens import TradeLens

lens = TradeLens()  # reads MIMO_API_KEY from env
thesis = lens.analyze("BTC/USDT", timeframe="4h", exchange="binance")

print(thesis.bias)         # "LONG" | "SHORT" | "NO_TRADE"
print(thesis.conviction)   # 0.0 - 10.0
print(thesis.entry)        # 77840.0
print(thesis.stop)         # 76400.0
print(thesis.targets)      # [80440.0, 82800.0]
print(thesis.contradictions)  # list of dissenting signals
print(thesis.to_markdown())   # serialized report
```

---

## Configuration

Environment variables (or pass directly to `TradeLens(...)`):

| Variable | Purpose |
|---|---|
| `MIMO_API_KEY` | Required. Get one at [platform.xiaomimimo.com](https://platform.xiaomimimo.com) |
| `MIMO_BASE_URL` | Default `https://api.xiaomimimo.com/v1` |
| `MIMO_VISION_MODEL` | Default `mimo-v2.5` |
| `MIMO_REASONING_MODEL` | Default `mimo-v2.5-pro` |
| `TRADELENS_CACHE_DIR` | Default `~/.cache/mimo-tradelens` |

---

## Examples

The [`examples/`](./examples/) folder contains complete, reproducible runs:

- `btc_4h.py` — bread-and-butter Bitcoin 4H setup
- `multi_asset_scan.py` — loop the engine over a basket and rank by conviction
- `chart_only.py` — chart rendering without the AI call (debugging visuals)
- `sample_outputs/` — five real outputs from production runs (Markdown + PNG)

---

## Project layout

```
mimo-tradelens/
├── mimo_tradelens/
│   ├── __init__.py
│   ├── cli.py             # Typer CLI
│   ├── core.py            # TradeLens orchestrator
│   ├── data.py            # CCXT OHLCV fetcher + indicator computation
│   ├── chart.py           # matplotlib chart rendering w/ overlays
│   ├── mimo_client.py     # OpenAI-compatible MiMo API wrapper
│   └── schema.py          # Pydantic trade thesis schema
├── examples/
├── tests/
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Roadmap

- [x] Vision + reasoning two-pass pipeline
- [x] CLI with TTY / JSON / Markdown output modes
- [x] CCXT exchange abstraction
- [ ] Backtest harness — replay the model on historical bars and score predictions
- [ ] Streaming mode — keep a 1H watchlist scanned every 5 min
- [ ] Multi-timeframe ensemble — fuse 4H + 1D verdicts into a single conviction
- [ ] Telegram / Discord output adapters

---

## License

MIT © 2026 [Anasfzi](https://github.com/Anasfzi)

Built for the [Xiaomi MiMo Orbit 100 Trillion Token Creator Incentive Program](https://100t.xiaomimimo.com).

> ⚠ This is research software. Trade ideas generated by MiMo TradeLens are explicitly **not financial advice**. The author is not responsible for any trading losses incurred by using this tool. Always do your own analysis and size risk appropriately.
