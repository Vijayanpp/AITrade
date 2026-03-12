# Skill: trade-scan

## Purpose
Scan multiple stocks from a named index or the user's watchlist and surface only the stocks with active setups — ranked by signal strength.

---

## Step 1 — Load Stock List

Based on the index argument:

| Argument | Stocks to scan |
|----------|---------------|
| `NIFTY50` | All 50 NIFTY 50 constituents |
| `BANKNIFTY` | 12 BANKNIFTY constituents |
| `NIFTY100` | Top 100 NIFTY stocks |
| `MIDCAP` | NIFTY Midcap 50 |
| `watchlist` | Stocks in `WATCHLIST.md` |

Load the built-in list from `scripts/data_fetcher.py --list <INDEX>` which returns the symbol list as JSON.

If no argument is given, default to `watchlist`. If `WATCHLIST.md` is empty, ask the user to add stocks first: `/trade watchlist add <SYMBOL>`.

---

## Step 2 — Fetch and Scan Each Stock

For each symbol in the list:
1. Run `python scripts/data_fetcher.py --symbol <SYMBOL>.NS --interval 15m --bars 50`
2. Run `python scripts/signal_engine.py --data <csv_path> --symbol <SYMBOL>`

`signal_engine.py` returns a JSON result:
```json
{
  "symbol": "RELIANCE",
  "signal": "BUY",
  "score": 3.8,
  "rsi": 62.1,
  "macd_cross": true,
  "above_vwap": true,
  "volume_spike": 2.1,
  "pattern": "Bullish Engulfing",
  "support": 2435,
  "resistance": 2480,
  "entry": 2458,
  "target1": 2480,
  "target2": 2510,
  "stop": 2428,
  "rr_ratio": 1.8
}
```

Collect results for all stocks. Filter out signals with `score < 2.5` (no clear setup).

---

## Step 3 — Rank Results

Sort filtered results by score descending. Separate into:
- 🟢 BUY setups (score ≥ 2.5, signal = BUY)
- 🔴 SELL setups (score ≤ -2.5, signal = SELL)

Show maximum 10 stocks per category.

---

## Step 4 — Write Scan Output File

Write to `SCAN-[INDEX]-[YYYYMMDD-HHMM].md`:

```markdown
# Market Scan — NIFTY50 — 11 Mar 2026, 11:00 AM

## 🟢 BUY Setups (4 found)

| Rank | Symbol | Score | RSI | Vol Spike | Pattern | Entry | T1 | Stop | R:R |
|------|--------|-------|-----|-----------|---------|-------|----|------|-----|
| 1 | RELIANCE | 4.2 | 62 | 2.3× | Bull Engulf | 2458 | 2480 | 2428 | 1:2.0 |
| 2 | HDFCBANK | 3.8 | 58 | 1.8× | Hammer | 1645 | 1670 | 1625 | 1:1.8 |
| 3 | TCS | 3.5 | 55 | 1.5× | MACD Cross | 3820 | 3870 | 3790 | 1:1.7 |
| 4 | INFY | 3.1 | 52 | 1.4× | None | 1520 | 1545 | 1503 | 1:1.5 |

## 🔴 SELL Setups (2 found)

| Rank | Symbol | Score | RSI | Vol Spike | Pattern | Entry | T1 | Stop | R:R |
|------|--------|-------|-----|-----------|---------|-------|----|------|-----|
| 1 | WIPRO | -3.9 | 42 | 2.0× | Bear Engulf | 285 | 278 | 292 | 1:2.0 |
| 2 | LT | -3.2 | 44 | 1.6× | Shooting Star | 3450 | 3410 | 3480 | 1:1.5 |

## 🟡 No Clear Setup
42 stocks show no actionable signal at this time.

---
*Run `/trade analyze <SYMBOL>` for full deep-dive on any stock above.*
*Disclaimer: For informational purposes only. Not SEBI-registered investment advice.*
```

---

## Step 5 — Print Summary to Terminal

After writing, print a brief terminal summary:
```
✅ Scan complete — NIFTY50 (50 stocks)
🟢 BUY setups:  4
🔴 SELL setups: 2
🟡 No setup:   44

Top pick: RELIANCE.NS (Score 4.2) → /trade analyze RELIANCE
Full report: SCAN-NIFTY50-20260311-1100.md
```
