"""
pattern_scanner.py — PIT Solutions Intraday Trade Analyst
Detects candlestick patterns in OHLCV data.
"""

import argparse
import json
import sys

try:
    import pandas as pd
except ImportError:
    print("ERROR: Run: pip install pandas")
    sys.exit(1)


def candle_body(row) -> float:
    return abs(row["close"] - row["open"])


def candle_range(row) -> float:
    return row["high"] - row["low"]


def upper_wick(row) -> float:
    return row["high"] - max(row["close"], row["open"])


def lower_wick(row) -> float:
    return min(row["close"], row["open"]) - row["low"]


def is_bullish(row) -> bool:
    return row["close"] > row["open"]


def is_bearish(row) -> bool:
    return row["close"] < row["open"]


def is_doji(row) -> bool:
    body = candle_body(row)
    total = candle_range(row)
    return total > 0 and body / total < 0.1


def volume_spike(df: pd.DataFrame, idx: int, multiplier: float = 1.2) -> bool:
    if idx < 5:
        return False
    avg_vol = df["volume"].iloc[idx - 5:idx].mean()
    return df["volume"].iloc[idx] >= avg_vol * multiplier


def detect_patterns(df: pd.DataFrame) -> list:
    """
    Scan the last 10 candles and return all detected patterns.
    Each result: {pattern, type, candle_index, confirmed, strength}
    """
    patterns = []
    n = len(df)
    scan_range = min(10, n - 2)

    for i in range(n - scan_range, n):
        row = df.iloc[i]
        body = candle_body(row)
        total = candle_range(row)
        uw = upper_wick(row)
        lw = lower_wick(row)
        if total == 0:
            continue

        confirmed = volume_spike(df, i)

        # ── Single candle patterns ──────────────────────────────────────────

        # Hammer (bullish reversal at bottom)
        if lw >= 2 * body and uw <= 0.1 * total and total > 0:
            patterns.append({
                "pattern": "Hammer",
                "type": "BULLISH",
                "candle_index": i,
                "candles_ago": n - 1 - i,
                "confirmed": confirmed,
                "strength": "STRONG" if confirmed else "WEAK"
            })

        # Shooting Star (bearish reversal at top)
        if uw >= 2 * body and lw <= 0.1 * total and is_bearish(row):
            patterns.append({
                "pattern": "Shooting Star",
                "type": "BEARISH",
                "candle_index": i,
                "candles_ago": n - 1 - i,
                "confirmed": confirmed,
                "strength": "STRONG" if confirmed else "WEAK"
            })

        # Doji
        if is_doji(row):
            patterns.append({
                "pattern": "Doji",
                "type": "NEUTRAL",
                "candle_index": i,
                "candles_ago": n - 1 - i,
                "confirmed": False,
                "strength": "WEAK"
            })

        # ── Two candle patterns ─────────────────────────────────────────────

        if i >= 1:
            prev = df.iloc[i - 1]
            prev_body = candle_body(prev)

            # Bullish Engulfing
            if (is_bearish(prev) and is_bullish(row)
                    and row["open"] < prev["close"]
                    and row["close"] > prev["open"]
                    and body > prev_body):
                patterns.append({
                    "pattern": "Bullish Engulfing",
                    "type": "BULLISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": confirmed,
                    "strength": "STRONG" if confirmed else "MODERATE"
                })

            # Bearish Engulfing
            if (is_bullish(prev) and is_bearish(row)
                    and row["open"] > prev["close"]
                    and row["close"] < prev["open"]
                    and body > prev_body):
                patterns.append({
                    "pattern": "Bearish Engulfing",
                    "type": "BEARISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": confirmed,
                    "strength": "STRONG" if confirmed else "MODERATE"
                })

            # Piercing Line (bullish)
            if (is_bearish(prev) and is_bullish(row)
                    and row["open"] < prev["low"]
                    and row["close"] > (prev["open"] + prev["close"]) / 2):
                patterns.append({
                    "pattern": "Piercing Line",
                    "type": "BULLISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": confirmed,
                    "strength": "MODERATE"
                })

            # Dark Cloud Cover (bearish)
            if (is_bullish(prev) and is_bearish(row)
                    and row["open"] > prev["high"]
                    and row["close"] < (prev["open"] + prev["close"]) / 2):
                patterns.append({
                    "pattern": "Dark Cloud Cover",
                    "type": "BEARISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": confirmed,
                    "strength": "MODERATE"
                })

        # ── Three candle patterns ───────────────────────────────────────────

        if i >= 2:
            c1 = df.iloc[i - 2]
            c2 = df.iloc[i - 1]
            c3 = row

            # Morning Star (bullish reversal)
            if (is_bearish(c1)
                    and candle_body(c2) < candle_body(c1) * 0.4
                    and is_bullish(c3)
                    and c3["close"] > (c1["open"] + c1["close"]) / 2):
                patterns.append({
                    "pattern": "Morning Star",
                    "type": "BULLISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": volume_spike(df, i),
                    "strength": "STRONG"
                })

            # Evening Star (bearish reversal)
            if (is_bullish(c1)
                    and candle_body(c2) < candle_body(c1) * 0.4
                    and is_bearish(c3)
                    and c3["close"] < (c1["open"] + c1["close"]) / 2):
                patterns.append({
                    "pattern": "Evening Star",
                    "type": "BEARISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": volume_spike(df, i),
                    "strength": "STRONG"
                })

            # Three White Soldiers (bullish)
            if (is_bullish(c1) and is_bullish(c2) and is_bullish(c3)
                    and c2["close"] > c1["close"]
                    and c3["close"] > c2["close"]
                    and candle_body(c2) > candle_body(c1) * 0.5
                    and candle_body(c3) > candle_body(c2) * 0.5):
                patterns.append({
                    "pattern": "Three White Soldiers",
                    "type": "BULLISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": True,
                    "strength": "STRONG"
                })

            # Three Black Crows (bearish)
            if (is_bearish(c1) and is_bearish(c2) and is_bearish(c3)
                    and c2["close"] < c1["close"]
                    and c3["close"] < c2["close"]
                    and candle_body(c2) > candle_body(c1) * 0.5
                    and candle_body(c3) > candle_body(c2) * 0.5):
                patterns.append({
                    "pattern": "Three Black Crows",
                    "type": "BEARISH",
                    "candle_index": i,
                    "candles_ago": n - 1 - i,
                    "confirmed": True,
                    "strength": "STRONG"
                })

    # Sort by recency (most recent first) and strength
    strength_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
    patterns.sort(key=lambda x: (x["candles_ago"], strength_order.get(x["strength"], 3)))

    return patterns


def get_primary_signal(patterns: list) -> dict:
    """Return the most relevant single pattern signal."""
    bullish = [p for p in patterns if p["type"] == "BULLISH" and p["candles_ago"] <= 3]
    bearish = [p for p in patterns if p["type"] == "BEARISH" and p["candles_ago"] <= 3]

    if bullish:
        best = bullish[0]
        return {"direction": "BULLISH", "pattern": best["pattern"],
                "confirmed": best["confirmed"], "strength": best["strength"],
                "candles_ago": best["candles_ago"]}
    if bearish:
        best = bearish[0]
        return {"direction": "BEARISH", "pattern": best["pattern"],
                "confirmed": best["confirmed"], "strength": best["strength"],
                "candles_ago": best["candles_ago"]}

    return {"direction": "NEUTRAL", "pattern": "None", "confirmed": False,
            "strength": "WEAK", "candles_ago": None}


def main():
    parser = argparse.ArgumentParser(description="PIT Solutions — Pattern Scanner")
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--primary-only", action="store_true", help="Return only the primary signal")

    args = parser.parse_args()

    try:
        df = pd.read_csv(args.data, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.data}")
        sys.exit(1)

    patterns = detect_patterns(df)
    primary = get_primary_signal(patterns)

    if args.primary_only:
        result = primary
    else:
        result = {
            "total_patterns": len(patterns),
            "primary_signal": primary,
            "all_patterns": patterns
        }

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Pattern results saved to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
