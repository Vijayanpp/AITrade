# Skill: trade-analyze

## Purpose
Run a full multi-agent intraday analysis for a given stock symbol. Synthesize findings from 4 parallel specialist agents into a single actionable trade signal.

---

## Step 1 — Validate Symbol

Parse the symbol from the user command. Accept formats: `RELIANCE`, `RELIANCE.NS`, `NIFTY`, `BANKNIFTY`.

- If no suffix is provided, append `.NS` automatically (NSE default).
- Run: `python scripts/data_fetcher.py --symbol <SYMBOL>.NS --interval 15m --bars 100`
- If the script returns an error or empty data, try `.BO` suffix (BSE). If both fail, report symbol not found and stop.

---

## Step 2 — Fetch Market Context

Before launching agents, gather market-wide context:

1. Run `python scripts/data_fetcher.py --symbol ^NSEI --interval 15m --bars 20` to get NIFTY 50 trend.
2. Check if NIFTY is trending UP, DOWN, or SIDEWAYS based on EMA(9) vs EMA(21).
3. Record market bias: **BULLISH / BEARISH / NEUTRAL**. This context is passed to all 4 agents.

---

## Step 3 — Launch 4 Parallel Subagents

Spawn these agents **simultaneously**. Each receives: symbol, raw OHLCV data path, market bias.

| Agent | File | Task |
|-------|------|------|
| trade-technical | `agents/trade-technical.md` | RSI, MACD, EMA, Bollinger Bands, VWAP, trend |
| trade-volume | `agents/trade-volume.md` | Volume spike, delivery %, OI, Put/Call ratio |
| trade-pattern | `agents/trade-pattern.md` | Candlestick patterns, support/resistance zones |
| trade-sentiment | `agents/trade-sentiment.md` | FII/DII, news, sector rotation, market breadth |

---

## Step 4 — Synthesize Signal

After all agents return results, apply this decision matrix:

### Signal Rules

**🟢 BUY** — All of the following must be true:
- RSI between 45–70 (momentum, not overbought)
- MACD line above signal line (or fresh crossover in last 3 candles)
- Price above VWAP
- Volume ≥ 1.3× 20-day average
- At least 1 bullish candlestick pattern confirmed
- Market bias is BULLISH or NEUTRAL

**🔴 SELL / SHORT** — All of the following must be true:
- RSI between 30–55 (momentum, not oversold)
- MACD line below signal line (or fresh crossover)
- Price below VWAP
- Volume ≥ 1.3× 20-day average
- At least 1 bearish candlestick pattern confirmed
- Market bias is BEARISH or NEUTRAL

**🟡 WAIT** — Any of the following:
- RSI > 75 (overbought, late entry) or RSI < 25 (oversold, late short)
- Conflicting signals from ≥ 2 agents
- Volume < 1× average (low conviction)
- Market bias conflicts with stock direction

### Entry, Target, and Stop Calculation

```
Entry Zone:  Current price ± 0.2% (account for spread)
Target 1:    Nearest resistance level from pattern agent
Target 2:    Next resistance / Fibonacci extension
Stop Loss:   Below nearest support (BUY) or above nearest resistance (SELL)
R:R Ratio:   (Target1 - Entry) / (Entry - Stop)
```

Only publish BUY or SELL signal if R:R ≥ 1.5. Otherwise output 🟡 WAIT.

---

## Step 5 — Write Output File

Create file `ANALYSIS-[SYMBOL]-[YYYYMMDD-HHMM].md` with this exact structure:

```markdown
# Trade Analysis — RELIANCE — 11 Mar 2026, 10:45 AM

## Signal
| Field | Value |
|-------|-------|
| Signal | 🟢 BUY |
| Entry Zone | ₹2,450 – ₹2,460 |
| Target 1 | ₹2,510 |
| Target 2 | ₹2,550 |
| Stop Loss | ₹2,420 |
| R:R Ratio | 1:2 |
| Timeframe | 15-min chart |
| Hold Duration | 1–3 hours |
| Confidence | HIGH |

## Reason
- RSI: 62 (bullish momentum, not overbought)
- MACD: Bullish crossover 3 candles ago
- Volume: 2.3× 20-day average (strong conviction)
- Pattern: Bullish Engulfing on 15-min, confirmed
- Level: Broke resistance at ₹2,440 with volume
- Market: NIFTY trending up, sector bullish

## Technical Details
[Paste trade-technical agent output here]

## Volume Analysis
[Paste trade-volume agent output here]

## Pattern Analysis
[Paste trade-pattern agent output here]

## Sentiment
[Paste trade-sentiment agent output here]

---
*Disclaimer: For informational purposes only. Not SEBI-registered investment advice. Always use your own judgment and risk management.*
```

---

## Step 6 — Print Summary to Terminal

After writing the file, always print the Signal block directly to the terminal so the user sees it immediately without opening the file.
