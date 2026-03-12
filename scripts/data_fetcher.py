"""
data_fetcher.py — PIT Solutions Intraday Trade Analyst
Fetches OHLCV stock data using yfinance and saves to CSV for agents to consume.
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: pip install yfinance pandas")
    sys.exit(1)

# NSE 50 constituents (symbol list for scan)
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
    "SUNPHARMA", "TITAN", "BAJFINANCE", "WIPRO", "NESTLEIND",
    "ULTRACEMCO", "POWERGRID", "NTPC", "ONGC", "TATAMOTORS",
    "TECHM", "BAJAJFINSV", "JSWSTEEL", "TATASTEEL", "ADANIPORTS",
    "DIVISLAB", "DRREDDY", "CIPLA", "EICHERMOT", "BRITANNIA",
    "HINDALCO", "VEDL", "COALINDIA", "BPCL", "GRASIM",
    "ADANIENT", "APOLLOHOSP", "BAJAJ-AUTO", "HEROMOTOCO", "M&M",
    "INDUSINDBK", "TATACONSUM", "SBILIFE", "HDFCLIFE", "UPL"
]

BANKNIFTY_SYMBOLS = [
    "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
    "INDUSINDBK", "BANDHANBNK", "IDFCFIRSTB", "FEDERALBNK", "PNB",
    "BANKBARODA", "CANBK"
]

NIFTY100_SYMBOLS = NIFTY50_SYMBOLS + [
    "ADANIGREEN", "AMBUJACEM", "ATGL", "AUROPHARMA", "BALKRISIND",
    "BERGEPAINT", "BIOCON", "BOSCHLTD", "CHOLAFIN", "COLPAL",
    "DABUR", "DLF", "GAIL", "GODREJCP", "HAL",
    "HAVELLS", "HINDPETRO", "ICICIGI", "ICICIPRULI", "INDUSTOWER",
    "IOC", "IRCTC", "LICI", "LUPIN", "MARICO",
    "MCDOWELL-N", "MFSL", "MOTHERSON", "MPHASIS", "OFSS",
    "PAGEIND", "PIIND", "PIDILITIND", "RECLTD", "SAIL",
    "SHREECEM", "SIEMENS", "SRF", "TORNTPHARM", "TRENT",
    "TVSMOTOR", "UBL", "VOLTAS", "WHIRLPOOL", "ZOMATO",
    "ZYDUSLIFE", "PERSISTENT", "COFORGE", "LTIM", "LTTS"
]

MIDCAP_SYMBOLS = [
    "ABCAPITAL", "APLAPOLLO", "ASHOKLEY", "ASTRAZEN", "BATAINDIA",
    "CEATLTD", "CROMPTON", "DEEPAKNTR", "ESCORTS", "EXIDEIND",
    "GMRINFRA", "GODREJPROP", "HFCL", "IDBI", "IPCALAB",
    "JKCEMENT", "JUBLFOOD", "KAJARIACER", "KEI", "LICHSGFIN",
    "LTTS", "MANAPPURAM", "NATCOPHARM", "NMDC", "OBEROIRLTY",
    "PETRONET", "PRESTIGE", "RAMCOCEM", "RBLBANK", "REDINGTON",
    "SAIL", "SCHAEFFLER", "SOLARINDS", "SUNDARMFIN", "SUPREMEIND",
    "SYNGENE", "TIINDIA", "TORNTPOWER", "TRENT", "TTKPRESTIG",
    "UNIONBANK", "VAIBHAVGBL", "VINATIORGA", "VOLTAS", "WIPRO",
    "ZEEL", "ZENITHEXPO", "ZENSARTECH", "ZODIACLOTH", "ZUARI"
]

INDEX_MAP = {
    "NIFTY50": NIFTY50_SYMBOLS,
    "BANKNIFTY": BANKNIFTY_SYMBOLS,
    "NIFTY100": NIFTY100_SYMBOLS,
    "MIDCAP": MIDCAP_SYMBOLS,
}

INTERVAL_MAP = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
}

PERIOD_MAP = {
    "1m": "1d",
    "2m": "5d",
    "5m": "5d",
    "15m": "5d",
    "30m": "1mo",
    "1h": "1mo",
    "1d": "3mo",
}


def validate_symbol(symbol: str) -> bool:
    """Check if a symbol is valid by fetching minimal data."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return hasattr(info, "last_price") and info.last_price is not None
    except Exception:
        return False


def fetch_data(symbol: str, interval: str, bars: int) -> pd.DataFrame:
    """Fetch OHLCV data for a symbol."""
    period = PERIOD_MAP.get(interval, "5d")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        return pd.DataFrame()

    df = df.tail(bars)
    df.index = pd.to_datetime(df.index)
    df.index.name = "Datetime"
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df


def list_symbols(index_name: str) -> list:
    """Return list of symbols for a given index."""
    index_name = index_name.upper()
    return INDEX_MAP.get(index_name, [])


def main():
    parser = argparse.ArgumentParser(description="PIT Solutions — Stock Data Fetcher")
    parser.add_argument("--symbol", help="Stock symbol (e.g., RELIANCE.NS)")
    parser.add_argument("--interval", default="15m", help="Candle interval (1m, 5m, 15m, 1h, 1d)")
    parser.add_argument("--bars", type=int, default=100, help="Number of candles to fetch")
    parser.add_argument("--output", help="Output CSV file path (default: auto-named)")
    parser.add_argument("--validate", help="Validate a symbol and exit")
    parser.add_argument("--list", help="List symbols for an index (NIFTY50, BANKNIFTY, etc.)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of CSV")

    args = parser.parse_args()

    # List mode
    if args.list:
        symbols = list_symbols(args.list)
        if not symbols:
            print(f"ERROR: Unknown index '{args.list}'. Valid: NIFTY50, BANKNIFTY, NIFTY100, MIDCAP")
            sys.exit(1)
        print(json.dumps({"index": args.list, "count": len(symbols), "symbols": symbols}))
        return

    # Validate mode
    if args.validate:
        is_valid = validate_symbol(args.validate)
        if is_valid:
            print(f"VALID: {args.validate} found on exchange")
        else:
            print(f"INVALID: {args.validate} not found. Try .NS (NSE) or .BO (BSE) suffix.")
            sys.exit(1)
        return

    if not args.symbol:
        print("ERROR: --symbol is required")
        parser.print_help()
        sys.exit(1)

    symbol = args.symbol
    if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not symbol.startswith("^"):
        symbol = symbol + ".NS"

    interval = args.interval
    if interval not in INTERVAL_MAP:
        print(f"ERROR: Invalid interval '{interval}'. Valid: {', '.join(INTERVAL_MAP.keys())}")
        sys.exit(1)

    print(f"Fetching {args.bars} candles of {interval} data for {symbol}...")

    df = fetch_data(symbol, interval, args.bars)

    if df.empty:
        print(f"ERROR: No data returned for {symbol}. Check symbol or market hours.")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        safe_symbol = symbol.replace(".", "_").replace("^", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = f"data_{safe_symbol}_{interval}_{ts}.csv"

    if args.json:
        print(df.reset_index().to_json(orient="records", date_format="iso", indent=2))
    else:
        df.to_csv(output_path)
        print(f"SUCCESS: Saved {len(df)} candles to {output_path}")
        print(f"  Symbol:   {symbol}")
        print(f"  Interval: {interval}")
        print(f"  From:     {df.index[0]}")
        print(f"  To:       {df.index[-1]}")
        print(f"  Last close: {df['Close'].iloc[-1]:.2f}")


if __name__ == "__main__":
    main()
