"""
signal_engine.py — PIT Solutions Intraday Trade Analyst
Generates a buy/sell/wait signal from indicator data for a given stock.
Used by the scan skill to process multiple stocks quickly.
"""

import argparse
import json
import sys

try:
    import pandas as pd
except ImportError:
    print("ERROR: Run: pip install pandas")
    sys.exit(1)

from indicators import compute_all


def find_support_resistance(df: pd.DataFrame, lookback: int = 50, cluster_pct: float = 0.003):
    """
    Find support and resistance levels from swing highs and lows.
    Returns lists of (price, strength) tuples.
    """
    highs = []
    lows = []
    df_tail = df.tail(lookback)

    for i in range(1, len(df_tail) - 1):
        h = df_tail.iloc[i]["high"]
        l = df_tail.iloc[i]["low"]
        prev_h = df_tail.iloc[i - 1]["high"]
        next_h = df_tail.iloc[i + 1]["high"]
        prev_l = df_tail.iloc[i - 1]["low"]
        next_l = df_tail.iloc[i + 1]["low"]
        if h > prev_h and h > next_h:
            highs.append(h)
        if l < prev_l and l < next_l:
            lows.append(l)

    def cluster(levels, direction="above", current_price=None):
        if not levels:
            return []
        levels.sort()
        clusters = []
        used = [False] * len(levels)
        for i in range(len(levels)):
            if used[i]:
                continue
            group = [levels[i]]
            for j in range(i + 1, len(levels)):
                if not used[j] and abs(levels[j] - levels[i]) / levels[i] <= cluster_pct:
                    group.append(levels[j])
                    used[j] = True
            clusters.append((round(sum(group) / len(group), 2), len(group)))
        if current_price:
            if direction == "above":
                clusters = [(p, s) for p, s in clusters if p > current_price]
            else:
                clusters = [(p, s) for p, s in clusters if p < current_price]
        clusters.sort(key=lambda x: x[0])
        return clusters

    current_price = float(df_tail["close"].iloc[-1])
    resistance_zones = cluster(highs, "above", current_price)
    support_zones = cluster(lows, "below", current_price)

    return support_zones, resistance_zones


def generate_signal(symbol: str, indicators: dict, support_zones: list, resistance_zones: list) -> dict:
    """Apply trading rules and generate a signal with entry, target, stop."""
    price = indicators["price"]
    rsi = indicators["rsi"]
    macd = indicators["macd"]
    ema = indicators["ema"]
    vwap = indicators["vwap"]
    volume = indicators["volume"]
    stoch = indicators["stochastic"]

    score = 0.0
    reasons = []
    pattern = "None"

    # RSI scoring
    if 45 <= rsi <= 70:
        score += 1
        reasons.append(f"RSI {rsi} (bullish zone)")
    elif 30 <= rsi <= 55:
        score -= 1
        reasons.append(f"RSI {rsi} (bearish zone)")
    elif rsi > 75:
        reasons.append(f"RSI {rsi} (overbought — avoid late entry)")
    elif rsi < 25:
        reasons.append(f"RSI {rsi} (oversold — avoid late short)")

    # MACD scoring
    if macd["bullish_cross"]:
        score += 1
        cago = macd["cross_candles_ago"]
        reasons.append(f"MACD bullish cross {cago} candles ago")
    elif macd["bearish_cross"]:
        score -= 1
        cago = macd["cross_candles_ago"]
        reasons.append(f"MACD bearish cross {cago} candles ago")
    elif macd["histogram"] > 0:
        score += 0.5
    elif macd["histogram"] < 0:
        score -= 0.5

    # EMA scoring
    if ema["price_above_ema9"]:
        score += 1
        reasons.append("Price above EMA9")
    else:
        score -= 1
        reasons.append("Price below EMA9")

    if ema["ema9_above_ema21"]:
        score += 0.5
    else:
        score -= 0.5

    # VWAP scoring
    if vwap["price_above_vwap"]:
        score += 1
        reasons.append(f"Above VWAP ({vwap['value']})")
    else:
        score -= 1
        reasons.append(f"Below VWAP ({vwap['value']})")

    # Volume scoring
    if volume["is_spike"] and volume["candle_bullish"]:
        score += 1
        reasons.append(f"Volume spike {volume['spike_ratio']}× on bullish candle")
    elif volume["is_spike"] and not volume["candle_bullish"]:
        score -= 1
        reasons.append(f"Volume spike {volume['spike_ratio']}× on bearish candle")

    # Stochastic modifier
    if stoch["overbought"] and score > 0:
        score -= 0.5
        reasons.append("Stochastic overbought (weakens buy)")
    elif stoch["oversold"] and score < 0:
        score += 0.5
        reasons.append("Stochastic oversold (weakens sell)")

    # Determine signal
    if score >= 2.5:
        signal = "BUY"
    elif score <= -2.5:
        signal = "SELL"
    else:
        signal = "WAIT"

    # Compute entry, targets, stop
    entry = price
    target1 = None
    target2 = None
    stop = None
    rr_ratio = None

    atr_val = indicators["atr"]["value"]

    if signal == "BUY":
        stop = indicators["atr"]["stop_buy"]
        if resistance_zones:
            target1 = resistance_zones[0][0]
            target2 = resistance_zones[1][0] if len(resistance_zones) > 1 else round(entry + 2 * (target1 - entry), 2)
        else:
            target1 = round(entry + 2 * atr_val, 2)
            target2 = round(entry + 3.5 * atr_val, 2)
        risk = entry - stop
        reward = target1 - entry
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    elif signal == "SELL":
        stop = indicators["atr"]["stop_sell"]
        if support_zones:
            target1 = support_zones[-1][0]
            target2 = support_zones[-2][0] if len(support_zones) > 1 else round(entry - 2 * (entry - target1), 2)
        else:
            target1 = round(entry - 2 * atr_val, 2)
            target2 = round(entry - 3.5 * atr_val, 2)
        risk = stop - entry
        reward = entry - target1
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    # Downgrade to WAIT if R:R is too low
    if signal in ("BUY", "SELL") and rr_ratio is not None and rr_ratio < 1.5:
        signal = "WAIT"
        reasons.append(f"R:R {rr_ratio} < 1.5 (insufficient reward — WAIT)")

    return {
        "symbol": symbol,
        "signal": signal,
        "score": round(score, 2),
        "confidence": "HIGH" if abs(score) >= 4 else "MEDIUM" if abs(score) >= 2.5 else "LOW",
        "rsi": rsi,
        "macd_cross": macd["bullish_cross"] or macd["bearish_cross"],
        "above_vwap": vwap["price_above_vwap"],
        "volume_spike": volume["spike_ratio"],
        "pattern": pattern,
        "support": support_zones[-1][0] if support_zones else None,
        "resistance": resistance_zones[0][0] if resistance_zones else None,
        "entry": round(entry, 2),
        "target1": target1,
        "target2": target2,
        "stop": stop,
        "rr_ratio": rr_ratio,
        "reasons": reasons,
        "trend": indicators["trend"]
    }


def main():
    parser = argparse.ArgumentParser(description="PIT Solutions — Signal Engine")
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--lookback", type=int, default=50, help="Candles for S/R detection")

    args = parser.parse_args()

    try:
        df = pd.read_csv(args.data, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.data}")
        sys.exit(1)

    indicators = compute_all(df)
    support_zones, resistance_zones = find_support_resistance(df, args.lookback)
    result = generate_signal(args.symbol, indicators, support_zones, resistance_zones)

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Signal saved to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
