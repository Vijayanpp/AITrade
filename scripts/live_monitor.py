"""
live_monitor.py — PIT Solutions Intraday Trade Analyst
Real-time trade monitoring agent.

Watches price action every N seconds and fires an entry alert
when a BUY or SELL trigger is crossed with volume confirmation.

Usage:
  python scripts/live_monitor.py --symbol MRPL.NS --buy-above 193 --sell-below 191.60
  python scripts/live_monitor.py --symbol MRPL.NS --buy-above 193 --t1 194 --t2 195.5 --stop-buy 191.80
  python scripts/live_monitor.py --symbol MRPL.NS --from-analysis ANALYSIS-MRPL-20260312-1443.md
"""

import argparse
import sys
import time
import os
import re
import json
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install yfinance pandas")
    sys.exit(1)

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import compute_all


# ─── ANSI Colors ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# Enable ANSI on Windows
if os.name == 'nt':
    os.system('color')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fp(price):
    """Format price as ₹X,XXX.XX"""
    if price is None or price != price:  # NaN check
        return "N/A"
    return f"₹{price:,.2f}"


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def time_session():
    """Return (time_str, session_label, is_power_hour)."""
    n = datetime.now()
    mins = n.hour * 60 + n.minute
    t = n.strftime("%H:%M:%S")

    if mins < 9 * 60 + 15:
        return t, "PRE-MARKET", False
    elif mins < 9 * 60 + 45:
        return t, "⚡ OPENING HOUR (volatile — wait for first 30 min)", False
    elif mins < 12 * 60:
        return t, "✅ MID-MORNING (good window for confirmed entries)", False
    elif mins < 14 * 60:
        return t, "⚠️  AFTERNOON LULL (low volume — entries risky)", False
    elif mins < 15 * 60 + 10:
        return t, "🔥 POWER HOUR (2–3:10 PM — biggest moves happen now)", True
    elif mins <= 15 * 60 + 30:
        return t, "⛔ CLOSING AUCTION — EXIT open positions, no new entries", False
    else:
        return t, "MARKET CLOSED", False


# ─── Data Fetcher ─────────────────────────────────────────────────────────────

def fetch_data(symbol: str, interval: str = "15m", bars: int = 50) -> pd.DataFrame:
    """Fetch latest OHLCV data via yfinance."""
    from data_fetcher import PERIOD_MAP
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


def compute_indicators(df: pd.DataFrame) -> dict:
    """Compute all indicators from OHLCV dataframe."""
    df_lower = df.copy()
    df_lower.columns = [c.lower() for c in df_lower.columns]
    try:
        return compute_all(df_lower)
    except Exception:
        return {}


# ─── Trigger Checker ──────────────────────────────────────────────────────────

def check_trigger(df: pd.DataFrame, buy_above: float, sell_below: float,
                  vol_multiplier: float = 1.3) -> tuple:
    """
    Check if the latest CLOSED candle triggered a BUY or SELL signal.

    Uses the second-to-last candle as the last confirmed closed candle.
    The most recent candle may still be forming.

    Returns: ('BUY' | 'SELL' | 'WAIT', current_price, vol_ratio, close_price)
    """
    if len(df) < 5:
        return 'WAIT', df['Close'].iloc[-1], 0, df['Close'].iloc[-1]

    # Last confirmed closed candle = df.iloc[-2]
    last = df.iloc[-2]
    current = df['Close'].iloc[-1]

    # Volume vs 20-candle average (excluding last 2 to avoid partial candles)
    lookback = df['Volume'].iloc[-22:-2]
    avg_vol = lookback.mean() if len(lookback) > 0 else 1
    vol_ratio = last['Volume'] / avg_vol if avg_vol > 0 else 0

    vol_ok = (vol_ratio >= vol_multiplier) or (avg_vol == 0)
    close = last['Close']

    if buy_above and close > buy_above and vol_ok:
        return 'BUY', current, vol_ratio, close

    if sell_below and close < sell_below and vol_ok:
        return 'SELL', current, vol_ratio, close

    # Near-miss — show distance
    return 'WAIT', current, vol_ratio, close


# ─── Analysis File Parser ─────────────────────────────────────────────────────

def parse_analysis_file(path: str) -> dict:
    """
    Extract BUY trigger, SELL trigger, T1, T2, stops from an ANALYSIS-*.md file.
    Returns a dict with keys: buy_above, sell_below, t1, t2, stop_buy, stop_sell
    """
    levels = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Patterns to extract price levels from the analysis file
        patterns = {
            'buy_above': [
                r'BUY[^\n]*above[^\n₹]*₹([\d,]+\.?\d*)',
                r'BUY Trigger[^\n]*₹([\d,]+\.?\d*)',
                r'above ₹([\d,]+\.?\d*)',
            ],
            'sell_below': [
                r'SHORT[^\n]*below[^\n₹]*₹([\d,]+\.?\d*)',
                r'SHORT Trigger[^\n]*₹([\d,]+\.?\d*)',
                r'below ₹([\d,]+\.?\d*)',
            ],
            't1': [
                r'T1[^\n₹]*₹([\d,]+\.?\d*)',
                r'Target 1[^\n₹]*₹([\d,]+\.?\d*)',
            ],
            't2': [
                r'T2[^\n₹]*₹([\d,]+\.?\d*)',
                r'Target 2[^\n₹]*₹([\d,]+\.?\d*)',
            ],
        }

        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                m = re.search(pattern, content, re.IGNORECASE)
                if m:
                    val_str = m.group(1).replace(',', '')
                    try:
                        levels[key] = float(val_str)
                        break
                    except ValueError:
                        continue

    except FileNotFoundError:
        print(f"ERROR: Analysis file not found: {path}")
        sys.exit(1)

    return levels


# ─── Dashboard Printer ────────────────────────────────────────────────────────

def print_dashboard(symbol, df, ind, buy_above, sell_below,
                    t1, t2, stop_buy, stop_sell,
                    status, vol_ratio, refresh_secs, countdown,
                    alert_count, last_alert_time):

    clear()

    current = df['Close'].iloc[-1]
    open_price = df['Open'].iloc[0]
    day_high = df['High'].max()
    day_low = df['Low'].min()
    prev = df['Close'].iloc[-2] if len(df) > 1 else current
    change = current - prev
    chg_pct = (change / prev * 100) if prev > 0 else 0
    chg_sym = "+" if change >= 0 else ""

    rsi = ind.get('rsi', 0)
    trend = ind.get('trend', 'N/A')
    vwap = ind.get('vwap', {}).get('value', 0)
    above_vwap = ind.get('vwap', {}).get('price_above_vwap', False)
    ema9 = ind.get('ema', {}).get('ema9', 0)
    macd_d = ind.get('macd', {})
    macd_bull = macd_d.get('current_macd', 0) > macd_d.get('current_signal', 0)
    atr = ind.get('atr', {}).get('value', 0)
    vol_spike = ind.get('volume', {}).get('spike_ratio', 0)

    t_str, session, is_power = time_session()

    # Header
    print(f"{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}  📡 LIVE MONITOR — {symbol:<16} {t_str} IST{RESET}")
    color_session = YELLOW if is_power else CYAN
    print(f"  {color_session}{session}{RESET}")
    print(f"{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    # Price block
    chg_color = GREEN if change >= 0 else RED
    print(f"\n  Price  : {BOLD}{fp(current)}{RESET}  "
          f"{chg_color}{chg_sym}{fp(change)} ({chg_sym}{chg_pct:.2f}%){RESET}")
    print(f"  High   : {fp(day_high)}   Low : {fp(day_low)}   Open: {fp(open_price)}")
    print(f"  VWAP   : {fp(vwap)}  ({'ABOVE' if above_vwap else 'BELOW'} — "
          f"{'institutional buy bias' if above_vwap else 'sellers in control'})")
    print(f"  RSI    : {rsi:.1f}  |  Trend: {trend}  |  ATR: {fp(atr)}")
    print(f"  MACD   : {'🟢 Bullish' if macd_bull else '🔴 Bearish'}"
          f"   Volume: {vol_spike:.1f}× avg  "
          f"{'🔥' if vol_spike >= 2.0 else '✅' if vol_spike >= 1.3 else '⚠️ '}")

    # Status bar
    print(f"\n{BOLD}{'─'*64}{RESET}")
    if status == 'BUY':
        print(f"  {GREEN}{BOLD}🔔 BUY SIGNAL ACTIVE — see alert above / check alert log{RESET}")
    elif status == 'SELL':
        print(f"  {RED}{BOLD}🔔 SELL SIGNAL ACTIVE — see alert above / check alert log{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}👁  WATCHING — waiting for trigger{RESET}")
    print(f"{'─'*64}")

    # Trigger levels
    print()
    if buy_above:
        dist = buy_above - current
        dist_pct = dist / current * 100
        color = GREEN if dist < 0 else DIM
        arrow = "✅ CROSSED" if dist < 0 else f"  {fp(dist)} away ({dist_pct:.2f}%)"
        print(f"  👆  {GREEN}BUY {RESET} trigger : close above {BOLD}{fp(buy_above)}{RESET}  → {color}{arrow}{RESET}")

    if sell_below:
        dist = current - sell_below
        dist_pct = dist / current * 100
        color = RED if dist < 0 else DIM
        arrow = "✅ CROSSED" if dist < 0 else f"  {fp(dist)} away ({dist_pct:.2f}%)"
        print(f"  👇  {RED}SHORT{RESET} trigger: close below {BOLD}{fp(sell_below)}{RESET}  → {color}{arrow}{RESET}")

    if buy_above and sell_below:
        zone_width = buy_above - sell_below
        zone_pct = zone_width / current * 100
        print(f"\n  {YELLOW}❌ No-Trade Zone: {fp(sell_below)} – {fp(buy_above)}"
              f"  (width: {fp(zone_width)}, {zone_pct:.2f}%){RESET}")

    # Targets & stops
    if t1 or t2 or stop_buy or stop_sell:
        print(f"\n{'─'*64}")
        print(f"  Trade Plan:")
        if buy_above:
            entry_b = (buy_above or current) * 1.001
            if t1:
                rr_b = (t1 - entry_b) / (entry_b - stop_buy) if stop_buy and stop_buy < entry_b else 0
                print(f"  {GREEN}BUY {RESET}: Entry ~{fp(entry_b)}  →  T1: {fp(t1)}"
                      f"{'  T2: ' + fp(t2) if t2 else ''}"
                      f"  SL: {fp(stop_buy) if stop_buy else 'not set'}"
                      f"{'  R:R 1:' + f'{rr_b:.1f}' if rr_b > 0 else ''}")
        if sell_below:
            entry_s = (sell_below or current) * 0.999
            if t1:
                rr_s = (entry_s - t1) / (stop_sell - entry_s) if stop_sell and stop_sell > entry_s else 0
                print(f"  {RED}SHORT{RESET}: Entry ~{fp(entry_s)}  →  T1: {fp(t1)}"
                      f"{'  T2: ' + fp(t2) if t2 else ''}"
                      f"  SL: {fp(stop_sell) if stop_sell else 'not set'}"
                      f"{'  R:R 1:' + f'{rr_s:.1f}' if rr_s > 0 else ''}")

    # Alerts fired
    if alert_count > 0:
        print(f"\n  {GREEN if status == 'BUY' else RED}🔔 {alert_count} alert(s) fired — last at {last_alert_time}{RESET}")

    # Refresh countdown bar
    filled = int(30 * (refresh_secs - countdown) / refresh_secs) if refresh_secs > 0 else 0
    bar = "█" * filled + "░" * (30 - filled)
    print(f"\n{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  [{bar}]  Refreshing in {countdown}s")
    print(f"  Press {BOLD}Ctrl+C{RESET} to stop monitoring")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def print_alert(symbol, signal, current_price, trigger_price,
                t1, t2, stop, ind, vol_ratio):
    """Print a large prominent alert when a trigger fires."""
    color = GREEN if signal == 'BUY' else RED
    icon  = "🟢" if signal == 'BUY' else "🔴"
    action = "BUY" if signal == 'BUY' else "SHORT"

    rsi = ind.get('rsi', 0)
    macd_d = ind.get('macd', {})
    macd_bull = macd_d.get('current_macd', 0) > macd_d.get('current_signal', 0)
    above_vwap = ind.get('vwap', {}).get('price_above_vwap', False)

    t_str, _, _ = time_session()
    entry = current_price * 1.001 if signal == 'BUY' else current_price * 0.999

    # Compute R:R
    rr_str = ""
    if t1 and stop:
        if signal == 'BUY' and stop < entry:
            rr = (t1 - entry) / (entry - stop)
            rr_str = f"1:{rr:.1f}"
        elif signal == 'SELL' and stop > entry:
            rr = (entry - t1) / (stop - entry)
            rr_str = f"1:{rr:.1f}"

    print()
    print(f"{color}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{color}{BOLD}║  {icon}  {action} SIGNAL TRIGGERED — {symbol:<16} {t_str}  ║{RESET}")
    print(f"{color}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  Candle closed {'above' if signal == 'BUY' else 'below'} {fp(trigger_price)} with {vol_ratio:.1f}× volume — CONFIRMED.")
    print()
    print(f"  {BOLD}┌─ TRADE DETAILS ──────────────────────────────────────────┐{RESET}")
    print(f"  │  Action   : {color}{BOLD}{action}{RESET}")
    print(f"  │  Entry    : {fp(entry)}  (limit order near market price)")
    print(f"  │  Target 1 : {fp(t1) if t1 else 'not set'}{'  (+' + fp(t1 - entry) + ')' if t1 else ''}")
    print(f"  │  Target 2 : {fp(t2) if t2 else 'not set'}{'  (+' + fp(t2 - entry) + ')' if t2 else ''}")
    print(f"  │  Stop Loss: {fp(stop) if stop else 'not set'}")
    print(f"  │  R:R      : {rr_str if rr_str else 'calculate manually'}")
    print(f"  {BOLD}└──────────────────────────────────────────────────────────┘{RESET}")
    print()
    print(f"  {BOLD}Confirmation checklist:{RESET}")

    rsi_ok   = (45 <= rsi <= 72 and signal == 'BUY') or (28 <= rsi <= 55 and signal == 'SELL')
    vol_ok   = vol_ratio >= 1.3
    macd_ok  = (macd_bull and signal == 'BUY') or (not macd_bull and signal == 'SELL')
    vwap_ok  = (above_vwap and signal == 'BUY') or (not above_vwap and signal == 'SELL')

    def ck(ok): return f"{GREEN}✅{RESET}" if ok else f"{YELLOW}⚠️ {RESET}"

    print(f"  {ck(vol_ok)}  Volume: {vol_ratio:.1f}× average  "
          f"({'Strong conviction' if vol_ratio >= 1.5 else 'Moderate' if vol_ratio >= 1.0 else 'LOW — be careful'})")
    print(f"  {ck(rsi_ok)}  RSI: {rsi:.1f}  "
          f"({'Momentum zone ✓' if rsi_ok else 'Check: may be overbought/oversold'})")
    print(f"  {ck(macd_ok)}  MACD: {'Bullish ✓' if macd_bull else 'Bearish ✓' if not macd_bull else 'Neutral'}")
    print(f"  {ck(vwap_ok)}  VWAP: Price {'above ✓' if above_vwap else 'below ✓'} VWAP")

    confirmed = sum([vol_ok, rsi_ok, macd_ok, vwap_ok])
    if confirmed >= 3:
        print(f"\n  {GREEN}{BOLD}  → {confirmed}/4 checks passed — HIGH CONFIDENCE entry{RESET}")
    elif confirmed == 2:
        print(f"\n  {YELLOW}{BOLD}  → {confirmed}/4 checks passed — MODERATE confidence — size down{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}  → {confirmed}/4 checks passed — LOW confidence — wait or skip{RESET}")

    print()
    print(f"  {DIM}⚠️  Not SEBI-registered advice. Use your own risk management.{RESET}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PIT Solutions — Live Trade Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor with manual levels from your analysis:
  python scripts/live_monitor.py --symbol MRPL.NS --buy-above 193 --sell-below 191.60 --t1 194 --t2 195.5 --stop-buy 191.80

  # Auto-load levels from an existing analysis file:
  python scripts/live_monitor.py --symbol MRPL.NS --from-analysis ANALYSIS-MRPL-20260312-1443.md

  # Fast 1-minute candle monitoring:
  python scripts/live_monitor.py --symbol MRPL.NS --buy-above 193 --interval 1m --refresh 30

  # Alert once and exit (for scripts/automation):
  python scripts/live_monitor.py --symbol MRPL.NS --buy-above 193 --once
        """
    )
    parser.add_argument("--symbol",         required=True,       help="Stock symbol, e.g. MRPL.NS or MRPL")
    parser.add_argument("--buy-above",       type=float,          help="BUY trigger: fire alert if candle closes above this price")
    parser.add_argument("--sell-below",      type=float,          help="SELL trigger: fire alert if candle closes below this price")
    parser.add_argument("--t1",             type=float,          help="Target 1 (shown in alert)")
    parser.add_argument("--t2",             type=float,          help="Target 2 (shown in alert)")
    parser.add_argument("--stop-buy",        type=float,          help="Stop loss for BUY trade")
    parser.add_argument("--stop-sell",       type=float,          help="Stop loss for SHORT trade")
    parser.add_argument("--interval",        default="15m",       help="Candle interval: 1m, 5m, 15m (default: 15m)")
    parser.add_argument("--refresh",         type=int, default=60, help="Seconds between data refreshes (default: 60)")
    parser.add_argument("--bars",            type=int, default=50, help="Candles to load per refresh (default: 50)")
    parser.add_argument("--vol-confirm",     type=float, default=1.3, help="Volume multiplier needed to confirm trigger (default: 1.3)")
    parser.add_argument("--no-volume-check", action="store_true", help="Fire alert on price crossing alone, without volume check")
    parser.add_argument("--from-analysis",                        help="Load BUY/SELL triggers from an ANALYSIS-*.md file")
    parser.add_argument("--once",            action="store_true", help="Alert once and exit instead of looping")
    parser.add_argument("--log",                                   help="Save alerts to a log file (e.g. alerts.log)")

    args = parser.parse_args()

    # ── Symbol normalisation
    symbol = args.symbol
    if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not symbol.startswith("^"):
        symbol += ".NS"

    # ── Load levels from analysis file if requested
    if args.from_analysis:
        print(f"📂 Loading levels from {args.from_analysis}...")
        levels = parse_analysis_file(args.from_analysis)
        if levels.get('buy_above') and not args.buy_above:
            args.buy_above = levels['buy_above']
        if levels.get('sell_below') and not args.sell_below:
            args.sell_below = levels['sell_below']
        if levels.get('t1') and not args.t1:
            args.t1 = levels['t1']
        if levels.get('t2') and not args.t2:
            args.t2 = levels['t2']
        print(f"  Loaded → BUY above: {fp(args.buy_above)}  |  SELL below: {fp(args.sell_below)}")
        print(f"           T1: {fp(args.t1)}  |  T2: {fp(args.t2)}")
        time.sleep(2)

    if not args.buy_above and not args.sell_below:
        print("ERROR: Provide --buy-above and/or --sell-below levels.")
        print("       Or use --from-analysis ANALYSIS-MRPL-YYYYMMDD-HHMM.md")
        sys.exit(1)

    vol_multiplier = 1.0 if args.no_volume_check else args.vol_confirm

    # ── Startup banner
    clear()
    print(f"\n{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}  📡 PIT Solutions — Live Trade Monitor{RESET}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    print(f"  Symbol     : {BOLD}{symbol}{RESET}")
    print(f"  Interval   : {args.interval} candles")
    print(f"  Refresh    : every {args.refresh}s")
    print(f"  BUY above  : {GREEN}{BOLD}{fp(args.buy_above)}{RESET}" if args.buy_above else f"  BUY above  : not set")
    print(f"  SELL below : {RED}{BOLD}{fp(args.sell_below)}{RESET}" if args.sell_below else f"  SELL below : not set")
    if args.t1:     print(f"  Target 1   : {fp(args.t1)}")
    if args.t2:     print(f"  Target 2   : {fp(args.t2)}")
    if args.stop_buy:  print(f"  Stop (BUY) : {fp(args.stop_buy)}")
    if args.stop_sell: print(f"  Stop (SELL): {fp(args.stop_sell)}")
    print(f"  Vol check  : {vol_multiplier}× average")
    print(f"\n  Starting in 3 seconds... Press Ctrl+C to stop.\n")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(3)

    # ── State
    alert_count = 0
    last_alert_time = ""
    last_status = 'WAIT'
    log_file = open(args.log, 'a', encoding='utf-8') if args.log else None

    try:
        while True:
            # ── Fetch data
            try:
                df = fetch_data(symbol, args.interval, args.bars)
                if df.empty:
                    clear()
                    print(f"\n⚠️  No data for {symbol}. Market may be closed. Retrying in {args.refresh}s...")
                    time.sleep(args.refresh)
                    continue
            except Exception as e:
                clear()
                print(f"\n⚠️  Data error: {e}\n  Retrying in {args.refresh}s...")
                time.sleep(args.refresh)
                continue

            # ── Compute indicators
            ind = compute_indicators(df)

            # ── Check triggers
            status, current_price, vol_ratio, close_price = check_trigger(
                df, args.buy_above, args.sell_below, vol_multiplier
            )

            # ── Determine stop for display
            stop_buy  = args.stop_buy  or ind.get('atr', {}).get('stop_buy')
            stop_sell = args.stop_sell or ind.get('atr', {}).get('stop_sell')

            # ── Fire alert if newly triggered
            if status in ('BUY', 'SELL') and last_status != status:
                trigger_price = args.buy_above if status == 'BUY' else args.sell_below
                stop = stop_buy if status == 'BUY' else stop_sell
                print_alert(symbol, status, current_price, trigger_price,
                            args.t1, args.t2, stop, ind, vol_ratio)
                alert_count += 1
                last_alert_time = now_str()

                # Log to file
                if log_file:
                    log_file.write(
                        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"{status} TRIGGERED — {symbol} @ {current_price:.2f} "
                        f"(trigger: {trigger_price}, vol: {vol_ratio:.1f}x)\n"
                    )
                    log_file.flush()

                if args.once:
                    break

                print(f"\n  {DIM}Continuing to monitor... Press Ctrl+C to stop.{RESET}")
                time.sleep(5)

            last_status = status

            # ── Live countdown
            for countdown in range(args.refresh, 0, -1):
                print_dashboard(
                    symbol, df, ind,
                    args.buy_above, args.sell_below,
                    args.t1, args.t2, stop_buy, stop_sell,
                    status, vol_ratio, args.refresh, countdown,
                    alert_count, last_alert_time
                )
                time.sleep(1)

    except KeyboardInterrupt:
        clear()
        print(f"\n{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  📡 Live monitor stopped — {symbol}")
        print(f"  Alerts fired: {alert_count}")
        if last_alert_time:
            print(f"  Last alert  : {last_alert_time}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    finally:
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
