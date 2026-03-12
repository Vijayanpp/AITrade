# Skill: trade-quick

## Purpose
Give the user a fast 60-second snapshot of a stock's current intraday position. No file output — print directly to terminal.

---

## Step 1 — Fetch Data

Run: `python scripts/data_fetcher.py --symbol <SYMBOL>.NS --interval 5m --bars 30`

This returns: timestamp, open, high, low, close, volume for the last 30 five-minute candles.

If it fails, fall back to: `python scripts/data_fetcher.py --symbol <SYMBOL>.NS --interval 15m --bars 20`

---

## Step 2 — Compute Inline

Using the returned data, compute:

1. **RSI (14)** — using `scripts/indicators.py --calc rsi --period 14 --data <csv_path>`
2. **MACD (12,26,9)** — `scripts/indicators.py --calc macd --data <csv_path>`
3. **VWAP** — `scripts/indicators.py --calc vwap --data <csv_path>`
4. **EMA 9 and EMA 21** — `scripts/indicators.py --calc ema --periods 9,21 --data <csv_path>`
5. **Last candle type** — Bullish (close > open) or Bearish (close < open)

---

## Step 3 — Determine Quick Signal

Apply simplified rules:

| Condition | Points |
|-----------|--------|
| RSI 45–70 | +1 (bullish) |
| RSI 30–55 | -1 (bearish) |
| MACD line > signal line | +1 |
| MACD line < signal line | -1 |
| Price > VWAP | +1 |
| Price < VWAP | -1 |
| EMA9 > EMA21 | +1 |
| EMA9 < EMA21 | -1 |
| Last candle bullish | +0.5 |
| Last candle bearish | -0.5 |

Score ≥ 2.5 → 🟢 BUY SETUP
Score ≤ -2.5 → 🔴 SELL SETUP
Between -2.5 and 2.5 → 🟡 NO CLEAR SETUP

---

## Step 4 — Print to Terminal

Print exactly this format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 QUICK SNAPSHOT — RELIANCE.NS — 10:47 AM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Price   : ₹2,458.40  (▲ 0.8% today)
 Signal  : 🟢 BUY SETUP
 RSI     : 61.4   → Bullish momentum
 MACD    : +ve crossover (2 candles ago)
 VWAP    : ₹2,441  → Price above VWAP ✓
 EMA9    : ₹2,452  → EMA21: ₹2,435  ✓

 Score   : +3.5 / 5.0

 Key Levels:
   Support   : ₹2,435 (VWAP)
   Resistance: ₹2,480 (recent swing high)

⚠ Quick scan only. Run /trade analyze RELIANCE for full signal.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Do not write any files. Terminal output only.
