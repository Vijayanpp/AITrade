# Skill: trade-report

## Purpose
Generate an end-of-day (EOD) summary report that aggregates all analysis files created today and provides a performance review, lessons, and tomorrow's watchlist.

---

## Step 1 — Collect Today's Analysis Files

Find all files matching: `ANALYSIS-*-[YYYYMMDD]*.md` in the current directory.

Also find: `SCAN-*-[YYYYMMDD]*.md`

If no files found for today, print:
```
⚠️ No analysis files found for today. Run /trade analyze <SYMBOL> first.
```

---

## Step 2 — Parse Each Analysis File

For each `ANALYSIS-*.md` file, extract:
- Symbol
- Signal (BUY / SELL / WAIT)
- Entry price
- Target 1 & 2
- Stop loss
- R:R ratio
- Confidence level
- Time of analysis

---

## Step 3 — Fetch Closing Prices

For each analyzed symbol, run:
`python scripts/data_fetcher.py --symbol <SYMBOL>.NS --interval 1d --bars 1`

Get today's closing price to calculate whether the signal was profitable.

---

## Step 4 — Calculate Performance

For each BUY/SELL signal:

```
If signal = BUY:
  Profit% = (Close - Entry) / Entry × 100
  Hit T1?  = Close >= Target1
  Hit T2?  = Close >= Target2
  Stopped? = Close <= StopLoss

If signal = SELL:
  Profit% = (Entry - Close) / Entry × 100
  Hit T1?  = Close <= Target1
  Stopped? = Close >= StopLoss
```

Label each signal:
- ✅ WIN — Target 1 hit
- ✅✅ WIN (T2) — Target 2 hit
- ❌ STOP — Stop loss hit
- 🔄 OPEN — Neither target nor stop hit by close

---

## Step 5 — Write Report File

Write to `REPORT-[YYYYMMDD].md`:

```markdown
# Trade Report — 11 Mar 2026
**PIT Solutions Intraday Analyst**

## Summary

| Metric | Value |
|--------|-------|
| Signals Given | 6 |
| BUY Signals | 4 |
| SELL Signals | 2 |
| Wins (T1) | 3 |
| Wins (T2) | 1 |
| Stops Hit | 1 |
| Still Open | 1 |
| Win Rate | 66.7% |
| Avg R:R | 1:1.8 |

## Signal Results

| Symbol | Signal | Entry | Close | Result | P&L% |
|--------|--------|-------|-------|--------|------|
| RELIANCE | 🟢 BUY | 2458 | 2497 | ✅ WIN (T1) | +1.6% |
| HDFCBANK | 🟢 BUY | 1645 | 1672 | ✅✅ WIN (T2) | +1.6% |
| TCS | 🟢 BUY | 3820 | 3810 | ❌ STOP | -0.8% |
| INFY | 🟢 BUY | 1520 | 1538 | 🔄 OPEN | +1.2% |
| WIPRO | 🔴 SELL | 285 | 278 | ✅ WIN (T1) | +2.5% |
| LT | 🔴 SELL | 3450 | 3460 | ❌ STOP | -0.9% |

## Today's Best Setup
WIPRO — Short signal at ₹285, closed at ₹278. Volume spike 2.0×, Bearish Engulfing confirmed. Perfect setup.

## Tomorrow's Watchlist
Stocks to watch for follow-through or reversal:
- RELIANCE — Watch ₹2,480 resistance break for continuation
- TCS — Check if support holds at ₹3,790 for potential bounce
- HDFCBANK — Breakout trade, set trailing stop

## Scan Summary
Scans run today: 2 (NIFTY50 at 9:30 AM, BANKNIFTY at 11:00 AM)

---
*Disclaimer: For informational purposes only. Not SEBI-registered investment advice.*
```

---

## Step 6 — Print Terminal Summary

```
📊 EOD Report Generated — 11 Mar 2026
   Signals: 6  |  Wins: 4  |  Stops: 1  |  Win Rate: 66.7%
   Report saved: REPORT-20260311.md
```
