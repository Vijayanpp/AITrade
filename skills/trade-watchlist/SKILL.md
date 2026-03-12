# Skill: trade-watchlist

## Purpose
Manage the user's personal stock watchlist stored in `WATCHLIST.md`. Supports adding, removing, viewing, and clearing stocks.

---

## Sub-commands

### `/trade watchlist add <SYMBOL>`

1. Validate the symbol by running: `python scripts/data_fetcher.py --validate <SYMBOL>.NS`
2. If valid, append to `WATCHLIST.md` under the `## Stocks` table. If already present, print "Already in watchlist."
3. Print: `✅ Added RELIANCE.NS to watchlist. (Total: 8 stocks)`

---

### `/trade watchlist remove <SYMBOL>`

1. Read `WATCHLIST.md`, remove the matching row from the table.
2. Print: `🗑️ Removed WIPRO from watchlist. (Total: 7 stocks)`
3. If not found, print: `⚠️ WIPRO not found in watchlist.`

---

### `/trade watchlist show`

Print the current watchlist directly in the terminal:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MY WATCHLIST (8 stocks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. RELIANCE.NS
  2. HDFCBANK.NS
  3. TCS.NS
  4. INFY.NS
  5. BAJFINANCE.NS
  6. AXISBANK.NS
  7. SBIN.NS
  8. TATAMOTORS.NS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tip: Run /trade scan watchlist to scan all at once.
```

---

### `/trade watchlist clear`

Ask for confirmation: "Are you sure you want to clear all 8 stocks from your watchlist? Type YES to confirm."

If confirmed, reset `WATCHLIST.md` to its empty template. Print: `🗑️ Watchlist cleared.`

---

## WATCHLIST.md Format

Always maintain this exact format so `/trade scan watchlist` can parse it:

```markdown
# My Watchlist

Last updated: 11 Mar 2026

## Stocks

| # | Symbol | Added |
|---|--------|-------|
| 1 | RELIANCE.NS | 11 Mar 2026 |
| 2 | HDFCBANK.NS | 11 Mar 2026 |
```

---

## Error Handling

- If `WATCHLIST.md` does not exist yet, create it with the empty template when first `add` is called.
- If symbol validation fails (not found on NSE/BSE), suggest: "Try RELIANCE.NS or RELIANCE.BO — check the exact ticker on NSE India."
