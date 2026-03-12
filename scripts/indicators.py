"""
indicators.py — PIT Solutions Intraday Trade Analyst
Computes technical indicators from OHLCV CSV data.
"""

import argparse
import json
import sys
import math

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install pandas numpy")
    sys.exit(1)


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("inf"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.round(2)


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean().round(2)


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd_line = (ema_fast - ema_slow).round(2)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().round(2)
    histogram = (macd_line - signal_line).round(2)
    return macd_line, signal_line, histogram


def compute_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = (sma + std_dev * std).round(2)
    lower = (sma - std_dev * std).round(2)
    return upper, sma.round(2), lower


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    return vwap.round(2)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    return atr.round(2)


def compute_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple:
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return k.round(2), d.round(2)


def detect_macd_cross(macd_line: pd.Series, signal_line: pd.Series, lookback: int = 5) -> dict:
    """Detect if a MACD crossover happened in the last N candles."""
    recent_macd = macd_line.iloc[-lookback:]
    recent_signal = signal_line.iloc[-lookback:]
    diff = recent_macd - recent_signal

    bullish_cross = False
    bearish_cross = False
    cross_candles_ago = None

    for i in range(len(diff) - 1, 0, -1):
        if diff.iloc[i] > 0 and diff.iloc[i - 1] <= 0:
            bullish_cross = True
            cross_candles_ago = len(diff) - 1 - i
            break
        elif diff.iloc[i] < 0 and diff.iloc[i - 1] >= 0:
            bearish_cross = True
            cross_candles_ago = len(diff) - 1 - i
            break

    return {
        "bullish_cross": bullish_cross,
        "bearish_cross": bearish_cross,
        "cross_candles_ago": cross_candles_ago,
        "current_macd": round(float(macd_line.iloc[-1]), 2),
        "current_signal": round(float(signal_line.iloc[-1]), 2),
        "histogram": round(float((macd_line - signal_line).iloc[-1]), 2)
    }


def compute_all(df: pd.DataFrame) -> dict:
    """Compute all indicators and return as a dict."""
    close = df["close"]

    rsi = compute_rsi(close, 14)
    ema9 = compute_ema(close, 9)
    ema21 = compute_ema(close, 21)
    ema50 = compute_ema(close, 50)
    macd_line, signal_line, histogram = compute_macd(close)
    bb_upper, bb_mid, bb_lower = compute_bollinger_bands(close)
    vwap = compute_vwap(df)
    atr = compute_atr(df)
    stoch_k, stoch_d = compute_stochastic(df)
    macd_cross = detect_macd_cross(macd_line, signal_line)

    last = df.iloc[-1]
    current_close = float(last["close"])
    current_vwap = float(vwap.iloc[-1])
    current_ema9 = float(ema9.iloc[-1])
    current_ema21 = float(ema21.iloc[-1])
    current_ema50 = float(ema50.iloc[-1])
    current_rsi = float(rsi.iloc[-1])
    current_atr = float(atr.iloc[-1])
    current_stoch_k = float(stoch_k.iloc[-1])
    current_bb_upper = float(bb_upper.iloc[-1])
    current_bb_lower = float(bb_lower.iloc[-1])
    current_bb_mid = float(bb_mid.iloc[-1])

    # Volume spike
    vol_avg_20 = float(df["volume"].tail(21).iloc[:-1].mean())
    current_vol = float(last["volume"])
    vol_spike = round(current_vol / vol_avg_20, 2) if vol_avg_20 > 0 else 0

    # Trend determination
    if current_ema9 > current_ema21 > current_ema50 and current_close > current_ema9:
        trend = "UPTREND"
    elif current_ema9 < current_ema21 < current_ema50 and current_close < current_ema9:
        trend = "DOWNTREND"
    else:
        trend = "SIDEWAYS"

    # BB position
    bb_range = current_bb_upper - current_bb_lower
    if bb_range > 0:
        bb_position = round((current_close - current_bb_lower) / bb_range * 100, 1)
    else:
        bb_position = 50.0

    return {
        "price": round(current_close, 2),
        "trend": trend,
        "rsi": round(current_rsi, 2),
        "macd": macd_cross,
        "ema": {
            "ema9": round(current_ema9, 2),
            "ema21": round(current_ema21, 2),
            "ema50": round(current_ema50, 2),
            "price_above_ema9": current_close > current_ema9,
            "ema9_above_ema21": current_ema9 > current_ema21,
        },
        "vwap": {
            "value": round(current_vwap, 2),
            "price_above_vwap": current_close > current_vwap,
            "gap_pct": round((current_close - current_vwap) / current_vwap * 100, 2)
        },
        "bollinger": {
            "upper": round(current_bb_upper, 2),
            "mid": round(current_bb_mid, 2),
            "lower": round(current_bb_lower, 2),
            "position_pct": bb_position,
        },
        "atr": {
            "value": round(current_atr, 2),
            "stop_buy": round(current_close - 1.5 * current_atr, 2),
            "stop_sell": round(current_close + 1.5 * current_atr, 2),
            "stop_pct": round(1.5 * current_atr / current_close * 100, 2)
        },
        "stochastic": {
            "k": round(current_stoch_k, 2),
            "d": round(float(stoch_d.iloc[-1]), 2),
            "overbought": current_stoch_k > 80,
            "oversold": current_stoch_k < 20,
        },
        "volume": {
            "current": int(current_vol),
            "avg_20": int(vol_avg_20),
            "spike_ratio": vol_spike,
            "is_spike": vol_spike >= 1.3,
            "candle_bullish": float(last["close"]) > float(last["open"])
        }
    }


def main():
    parser = argparse.ArgumentParser(description="PIT Solutions — Technical Indicators")
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--calc", default="all", help="Indicator to compute: rsi, macd, ema, vwap, atr, stoch, all")
    parser.add_argument("--all", dest="calc_all", action="store_true", help="Compute all indicators (alias for --calc all)")
    parser.add_argument("--period", type=int, default=14, help="Period for single-indicator calc")
    parser.add_argument("--periods", help="Comma-separated periods for EMA (e.g. 9,21,50)")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    if args.calc_all:
        args.calc = "all"

    try:
        df = pd.read_csv(args.data, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            print(f"ERROR: CSV must have columns: {required}")
            sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.data}")
        sys.exit(1)

    if args.calc == "all" or args.calc is None:
        result = compute_all(df)
    elif args.calc == "rsi":
        rsi = compute_rsi(df["close"], args.period)
        result = {"rsi": round(float(rsi.iloc[-1]), 2), "period": args.period}
    elif args.calc == "macd":
        ml, sl, hist = compute_macd(df["close"])
        result = detect_macd_cross(ml, sl)
    elif args.calc == "ema":
        periods = [int(p) for p in args.periods.split(",")] if args.periods else [9, 21, 50]
        result = {}
        for p in periods:
            ema = compute_ema(df["close"], p)
            result[f"ema{p}"] = round(float(ema.iloc[-1]), 2)
    elif args.calc == "vwap":
        vwap = compute_vwap(df)
        result = {
            "vwap": round(float(vwap.iloc[-1]), 2),
            "price": round(float(df["close"].iloc[-1]), 2),
            "above": float(df["close"].iloc[-1]) > float(vwap.iloc[-1])
        }
    elif args.calc == "atr":
        atr = compute_atr(df, args.period)
        price = float(df["close"].iloc[-1])
        atr_val = float(atr.iloc[-1])
        result = {
            "atr": round(atr_val, 2),
            "stop_buy": round(price - 1.5 * atr_val, 2),
            "stop_sell": round(price + 1.5 * atr_val, 2)
        }
    else:
        print(f"ERROR: Unknown indicator '{args.calc}'")
        sys.exit(1)

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Results saved to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
