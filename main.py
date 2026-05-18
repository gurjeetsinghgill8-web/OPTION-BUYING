"""
BITCOIN OPTIONS ENGINE — MAIN LOOP
====================================
LEGO Block 3 of 4 — main.py

Strategy:
  Indicator  : SuperTrend (Period=10, Mult=1, default 15m candles)
  Price Basis: 15m CLOSED candle close — NEVER live tick
  Signal     : close > ST → BUY CALL | close < ST → BUY PUT
  Exit       : Premium hits 2x entry → auto-book profit
  Flip       : Trend flips → close current options → enter opposite
  Force-close: 3:20 PM IST every day (no overnight theta risk)
  Loop speed : Every 5 minutes
====================================
"""
import time
import datetime
import socket
import sys
import os
import traceback
import pandas as pd
import numpy as np
import requests
import requests.packages.urllib3.util.connection as urllib3_cn

# ── Force IPv4 ────────────────────────────────────────────────
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

import db
import options_executor as oe

try:
    from utils import send_telegram_msg, log_terminal
except ImportError:
    def send_telegram_msg(msg): print(f"TG: {msg}")
    def log_terminal(msg, typ="INFO"): print(f"[{typ}] {msg}")

# ═══════════════════════════════════════════════════════════
# VPN IP GUARD — PERMANENT — NEVER CHANGE THIS
# Delta Exchange India ONLY accepts: 46.224.133.16
# This is the VPN IP on the VPS. Any other IP = 401 rejected.
# ═══════════════════════════════════════════════════════════
ALLOWED_TRADING_IP = "46.224.133.16"   # PERMANENT — DO NOT CHANGE
_vpn_alert_sent_at = 0

def _get_current_ip():
    """Returns current public IP. Used to verify VPN is connected."""
    try:
        return requests.get("https://api.ipify.org", timeout=4).text.strip()
    except Exception:
        return None

def _check_vpn_guard():
    """
    Returns True if trading is allowed (VPN connected, IP correct).
    Returns False + sends Telegram alert if VPN disconnected.
    Only alerts once per 5 minutes to avoid spam.
    """
    global _vpn_alert_sent_at
    current_ip = _get_current_ip()
    if current_ip and current_ip != ALLOWED_TRADING_IP:
        now = time.time()
        if now - _vpn_alert_sent_at > 300:   # alert max once per 5 min
            msg = (f"⚠️ VPN DISCONNECTED!\n"
                   f"Current IP : {current_ip}\n"
                   f"Need IP    : {ALLOWED_TRADING_IP}\n"
                   f"Trading    : PAUSED until VPN reconnects.")
            log_terminal(msg, "ALERT")
            send_telegram_msg(msg)
            _vpn_alert_sent_at = now
        return False
    return True

# ═══════════════════════════════════════════════════════════
# CANDLE-CHANGE GUARD
# Stored in DB — survives restarts — prevents re-entry on same candle
# ═══════════════════════════════════════════════════════════
_last_processed_candle_ts = 0  # loaded from DB in run_options_loop()

# ═══════════════════════════════════════════════════════════
# SUPERTREND CALCULATOR (pure math — same as proven futures engine)
# ═══════════════════════════════════════════════════════════
def calculate_supertrend(df, period=10, multiplier=1.0):
    """
    Pure SuperTrend calculation on OHLC DataFrame.
    Returns df with columns: supertrend, direction
      direction =  1 → Bullish (price above ST → BUY CALL)
      direction = -1 → Bearish (price below ST → BUY PUT)
    """
    df = df.copy()
    df["hl2"]        = (df["high"] + df["low"]) / 2
    df["prev_close"] = df["close"].shift(1)
    df["tr"]         = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["prev_close"]),
            abs(df["low"]  - df["prev_close"])
        )
    )
    df["atr"]         = df["tr"].rolling(window=period, min_periods=1).mean()
    df["basic_upper"] = df["hl2"] + (multiplier * df["atr"])
    df["basic_lower"] = df["hl2"] - (multiplier * df["atr"])

    final_upper = [0.0] * len(df)
    final_lower = [0.0] * len(df)
    supertrend  = [0.0] * len(df)
    direction   = [1]   * len(df)

    for i in range(1, len(df)):
        if df["basic_upper"].iloc[i] < final_upper[i-1] or df["close"].iloc[i-1] > final_upper[i-1]:
            final_upper[i] = df["basic_upper"].iloc[i]
        else:
            final_upper[i] = final_upper[i-1]

        if df["basic_lower"].iloc[i] > final_lower[i-1] or df["close"].iloc[i-1] < final_lower[i-1]:
            final_lower[i] = df["basic_lower"].iloc[i]
        else:
            final_lower[i] = final_lower[i-1]

        if supertrend[i-1] == final_upper[i-1]:
            if df["close"].iloc[i] <= final_upper[i]:
                supertrend[i] = final_upper[i];  direction[i] = -1
            else:
                supertrend[i] = final_lower[i];  direction[i] =  1
        else:
            if df["close"].iloc[i] >= final_lower[i]:
                supertrend[i] = final_lower[i];  direction[i] =  1
            else:
                supertrend[i] = final_upper[i];  direction[i] = -1

    df["final_upper"] = final_upper
    df["final_lower"] = final_lower
    df["supertrend"]  = supertrend
    df["direction"]   = direction
    return df

# ═══════════════════════════════════════════════════════════
# CANDLE FETCHER (15m by default)
# ═══════════════════════════════════════════════════════════
def fetch_candles(timeframe="15m", limit=150):
    """
    Fetches BTC OHLC candles from Delta Exchange.
    Returns DataFrame sorted oldest→newest.
    Tries India endpoint first, falls back to global.
    """
    valid_tf = ["5s","1m","3m","5m","15m","30m","1h","2h","4h","6h","12h","1d","1w"]
    resolution = timeframe if timeframe in valid_tf else "15m"

    tf_secs_map = {
        "5s": 5, "1m": 60, "3m": 180, "5m": 300, "15m": 900,
        "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
        "6h": 21600, "12h": 43200, "1d": 86400
    }
    tf_secs  = tf_secs_map.get(resolution, 900)
    end_ts   = int(time.time())
    start_ts = end_ts - (limit * tf_secs)

    for base in ["https://api.india.delta.exchange", "https://api.delta.exchange"]:
        try:
            params = {
                "symbol":     "BTCUSD",
                "resolution": resolution,
                "start":      start_ts,
                "end":        end_ts
            }
            resp = requests.get(f"{base}/v2/history/candles", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("result", [])
                if data:
                    df = pd.DataFrame(data)
                    for col in ["open", "high", "low", "close"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                    if "time" in df.columns:
                        df = df.sort_values("time", ascending=True)
                    df = df.reset_index(drop=True)
                    print(f"[CANDLE] {len(df)} candles | {resolution} | last_close={df['close'].iloc[-1]:.0f}")
                    return df
        except Exception as e:
            print(f"[CANDLE ERR] {base}: {e}")

    print("[CANDLE] ALL ENDPOINTS FAILED")
    return pd.DataFrame()

# ═══════════════════════════════════════════════════════════
# SUPERTREND SIGNAL (15m closed candle — zero repaint)
# ═══════════════════════════════════════════════════════════
def get_supertrend_signal():
    """
    Fetches 15m candles and computes SuperTrend on the CONFIRMED candle.

    Candle selection:
      Raw feed  : [..., C-2, C-1, C0(forming)]
      After drop: [..., C-2, C-1]   ← iloc[:-1] removes forming candle
      We use    : C-1 (iloc[-1])    ← last CLOSED candle (confirmed)
      We also store C-2 (iloc[-2])  ← doubly confirmed, for guard check

    Returns: (signal, st_value, confirmed_close, latest_closed_ts)
      signal = "CALL" | "PUT" | None
    """
    timeframe  = db.get_param("timeframe",    "15m")
    period     = int(db.get_param("st_period",     "10") or "10")
    multiplier = float(db.get_param("st_multiplier", "1.0") or "1.0")

    df = fetch_candles(timeframe=timeframe, limit=max(period * 3, 80))
    if df.empty or len(df) < period + 3:
        log_terminal(f"⚠️ Not enough candles ({len(df)}). Need {period+3}+", "WARN")
        return None, 0.0, 0.0, None

    # Remove forming candle (rightmost) — it's still open
    df_closed = df.iloc[:-1].copy()

    # Run SuperTrend on all closed candles
    df_st = calculate_supertrend(df_closed, period=period, multiplier=multiplier)

    # Use the LAST CLOSED candle (iloc[-1]) — this is the confirmed candle
    # whose data has settled and won't repaint
    confirmed        = df_st.iloc[-1]
    latest_closed_ts = int(df_closed.iloc[-1].get("time", 0))

    direction   = int(confirmed["direction"])
    st_value    = float(confirmed["supertrend"])
    last_close  = float(confirmed["close"])
    last_time   = confirmed.get("time", 0)

    # CALL = Bullish (close above SuperTrend), PUT = Bearish (close below)
    signal = "CALL" if direction == 1 else "PUT"

    # Store for dashboard display
    db.set_param("st_value",      f"{st_value:.2f}")
    db.set_param("st_direction",  "UP" if direction == 1 else "DOWN")
    db.set_param("current_15m_close", f"{last_close:.2f}")
    db.set_param("last_signal",   signal)
    db.set_param("last_candle_ts", str(latest_closed_ts))

    log_terminal(
        f"📌 15m Candle ts={last_time} | close={last_close:.0f} "
        f"| ST={st_value:.0f} | Signal={signal}",
        "INFO"
    )
    return signal, st_value, last_close, latest_closed_ts

# ═══════════════════════════════════════════════════════════
# FORCE-CLOSE CHECK (3:20 PM IST)
# ═══════════════════════════════════════════════════════════
def is_force_close_time():
    """
    Returns True after 3:20 PM IST — force-close everything.
    Options lose value fast near 3:30 close — exit by 3:20.
    """
    now = datetime.datetime.now()
    return now.hour > 15 or (now.hour == 15 and now.minute >= 20)

# ═══════════════════════════════════════════════════════════
# SELF-HEALING GUARDIAN v2 — qty-aware, dashboard-safe
# Runs every new candle — BEFORE any trade logic
# ═══════════════════════════════════════════════════════════
def _run_guardian():
    """
    Smart Guardian v2 — qty-aware, dashboard-safe.

    Logic:
      expected_qty  = DB active_option_qty  (set from dashboard — 1/5/10 etc)
      exchange_qty  = actual size on exchange for DB symbol
      extra_lots    = exchange_qty - expected_qty

      If extra_lots > 0  → sell ONLY the extra lots (not all)
      If extra_lots == 0 → All good, nothing to do
      If extra_lots < 0  → Warning only (partial close happened externally)
      If exchange = 0    → NEVER clear DB (options sync unreliable)

    Example: Dashboard=10 lots, exchange=12 → sells 2 extra only.
    Example: Dashboard=5 lots, exchange=5  → does nothing.
    """
    import hmac as _hmac, hashlib as _hash, json as _json
    import requests as _req

    api_key    = db.get_param("delta_api_key",    "")
    api_secret = db.get_param("delta_api_secret", "")
    db_active  = db.get_param("option_trade_active", "NO")
    db_symbol  = db.get_param("active_option_symbol", "NONE")
    db_pid     = db.get_param("active_option_product_id", "0")

    if not api_key or db_active != "YES" or db_symbol == "NONE":
        return  # Nothing active — skip

    expected_qty = int(db.get_param("active_option_qty", "1") or "1")
    BASE = "https://api.india.delta.exchange"

    def signed_get(path, query=""):
        ts  = str(int(time.time()))
        sig = _hmac.new(api_secret.encode(),
                        ("GET" + ts + path + query).encode(),
                        _hash.sha256).hexdigest()
        h = {"api-key": api_key, "signature": sig,
             "timestamp": ts, "Content-Type": "application/json"}
        try:
            return _req.get(BASE + path + query, headers=h, timeout=8)
        except Exception:
            return None

    def signed_post(path, payload_dict):
        payload = _json.dumps(payload_dict)
        ts  = str(int(time.time()))
        sig = _hmac.new(api_secret.encode(),
                        ("POST" + ts + path + payload).encode(),
                        _hash.sha256).hexdigest()
        h = {"api-key": api_key, "signature": sig,
             "timestamp": ts, "Content-Type": "application/json"}
        try:
            return _req.post(BASE + path, headers=h, data=payload, timeout=8)
        except Exception:
            return None

    # Fetch exchange position for current symbol
    resp = signed_get("/v2/positions", "?underlying_asset_symbol=BTC")
    if not resp or resp.status_code != 200:
        log_terminal("Guardian: API call failed — skipping", "WARN")
        return

    exchange_qty = 0
    exchange_pid = 0
    for p in resp.json().get("result", []):
        sym = (p.get("product", {}) or {}).get("symbol", "")
        sz  = float(p.get("size", 0))
        pid = (p.get("product", {}) or {}).get("id", 0)
        if sym == db_symbol and sz > 0:
            exchange_qty = int(sz)
            exchange_pid = int(pid or db_pid)
            break

    extra_lots = exchange_qty - expected_qty

    log_terminal(
        f"🛡 Guardian: {db_symbol} | Expected={expected_qty} | "
        f"Exchange={exchange_qty} | Extra={extra_lots}",
        "INFO"
    )

    if extra_lots > 0:
        # Close ONLY the extra lots
        log_terminal(f"Guardian: Closing {extra_lots} extra lot(s)...", "ALERT")
        _audit_log(
            "GUARDIAN",
            f"EXTRA_LOTS: exchange={exchange_qty}, expected={expected_qty}",
            f"Selling {extra_lots} extra lot(s) of {db_symbol}"
        )
        send_telegram_msg(
            f"🛡 GUARDIAN ALERT\n"
            f"Symbol: {db_symbol}\n"
            f"Exchange: {exchange_qty} lots | Expected: {expected_qty} lots\n"
            f"Closing {extra_lots} extra lot(s)..."
        )
        pid_to_use = exchange_pid or int(db_pid or 0)
        r = signed_post("/v2/orders", {
            "product_id":  pid_to_use,
            "size":        extra_lots,
            "side":        "sell",
            "order_type":  "market_order",
            "reduce_only": True
        })
        if r and r.status_code in [200, 201]:
            _audit_log("GUARDIAN", f"Extra lots closed: {db_symbol}",
                       f"Sold {extra_lots} | Remaining: {expected_qty}")
            send_telegram_msg(
                f"✅ GUARDIAN REPAIRED\n"
                f"Closed {extra_lots} extra lot(s) of {db_symbol}\n"
                f"Remaining: {expected_qty} lot(s) as intended"
            )
        else:
            err = r.text[:100] if r else "no response"
            _audit_log("GUARDIAN", f"Close FAILED: {db_symbol}", err)

    elif extra_lots < 0:
        # Partial close happened externally — just warn
        log_terminal(
            f"Guardian: Exchange has LESS ({exchange_qty}) than expected ({expected_qty}) — "
            f"partial close externally?", "WARN"
        )
        _audit_log("GUARDIAN", f"PARTIAL_CLOSE detected: {db_symbol}",
                   f"Exchange={exchange_qty}, Expected={expected_qty} — no action taken")

    else:
        log_terminal(f"Guardian: All OK — {exchange_qty} lot(s) as expected", "INFO")

def is_market_open():
    """
    Returns True during BTC 24x7 trading.
    For options, Delta Exchange runs nearly 24/7.
    The only time we pause is when we've force-closed for the day
    and are waiting for the next signal window.
    """
    # BTC options on Delta Exchange trade 24x7
    # We always return True — force-close is handled separately
    return True

# ═══════════════════════════════════════════════════════════
# AUDIT LOG SYSTEM
# ═══════════════════════════════════════════════════════════
AUDIT_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.log")

def _audit_log(event, reason, action):
    """
    Writes a structured entry to audit.log.
    Format: [YYYY-MM-DD HH:MM:SS] EVENT | REASON | ACTION
    """
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {event} | {reason} | {action}\n"
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[AUDIT LOG ERR] {e}")
    log_terminal(f"[AUDIT] {event} — {action}", "ALERT")

# ═══════════════════════════════════════════════════════════
# SELF-HEALING GUARDIAN
# Runs every 5 min loop — BEFORE any trade logic
# ═══════════════════════════════════════════════════════════
def _run_guardian():
    """
    Self-healing guardian — checks for ghost/extra positions.

    Rules:
    1. Exchange has 0 positions BUT DB says ACTIVE
       → DB stuck — reset to FLAT, audit log entry
    2. Exchange has 2+ positions (ghost trade)
       → Keep the one matching DB symbol, close all others
       → Audit log + Telegram alert
    3. Exchange has exactly 1 position matching DB → All OK
    """
    log_terminal("🛡 Guardian check starting...", "INFO")

    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return  # No credentials — skip silently

    # Fetch live positions from exchange
    try:
        positions = oe.sync_option_position()  # returns bool
        # Re-read DB state after sync
        db_active = db.get_param("option_trade_active", "NO")
        db_symbol = db.get_param("active_option_symbol", "NONE")
    except Exception as e:
        log_terminal(f"Guardian: sync failed — {e}", "WARN")
        return

    # Fetch raw positions for multi-position check
    import hmac, hashlib, requests as req_mod
    try:
        api_secret = db.get_param("delta_api_secret", "")
        ts_str     = str(int(time.time()))
        path       = "/v2/positions"
        query      = "?underlying_asset_symbol=BTC"
        sig_data   = "GET" + ts_str + path + query
        signature  = hmac.new(
            api_secret.encode("utf-8"),
            sig_data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        headers = {
            "api-key":      api_key,
            "signature":    signature,
            "timestamp":    ts_str,
            "Content-Type": "application/json"
        }
        resp = req_mod.get(
            f"https://api.india.delta.exchange{path}{query}",
            headers=headers, timeout=8
        )
        if resp.status_code != 200:
            return
        raw = resp.json().get("result", [])
    except Exception as e:
        log_terminal(f"Guardian: raw fetch failed — {e}", "WARN")
        return

    # Filter only open BTC option positions
    open_opts = [
        p for p in raw
        if float(p.get("size", 0)) > 0
        and (
            (p.get("product", {}).get("symbol") or "").startswith(("C-BTC", "P-BTC"))
            or (p.get("symbol", "")).startswith(("C-BTC", "P-BTC"))
        )
    ]

    count = len(open_opts)
    log_terminal(f"Guardian: Exchange has {count} open BTC option position(s)", "INFO")

    # Case 1: More than 1 position — GHOST TRADE detected
    if count > 1:
        msg = (
            f"🛡 GUARDIAN ALERT\n"
            f"Exchange: {count} positions found\n"
            f"Expected: 1 (max)\n"
            f"Action: Closing extras now..."
        )
        send_telegram_msg(msg)
        _audit_log(
            "GUARDIAN",
            f"GHOST_TRADE — {count} positions on exchange, expected 1",
            f"Closing {count - 1} extra position(s)"
        )

        # Keep the one matching DB symbol, close the rest
        for p in open_opts:
            sym = p.get("product", {}).get("symbol") or p.get("symbol", "")
            if sym == db_symbol:
                continue  # keep this one
            # Close the extra
            pid  = p.get("product_id") or p.get("product", {}).get("id")
            size = int(float(p.get("size", 0)))
            try:
                import json
                payload = json.dumps({
                    "product_id": int(pid),
                    "size":       size,
                    "side":       "sell",
                    "order_type": "market_order",
                    "reduce_only": True
                })
                ts2 = str(int(time.time()))
                p2  = "/v2/orders"
                sd2 = "POST" + ts2 + p2 + "" + payload
                sig2 = hmac.new(
                    api_secret.encode("utf-8"),
                    sd2.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()
                hdr2 = {
                    "api-key":      api_key,
                    "signature":    sig2,
                    "timestamp":    ts2,
                    "Content-Type": "application/json"
                }
                r2 = req_mod.post(
                    f"https://api.india.delta.exchange{p2}",
                    headers=hdr2, data=payload, timeout=8
                )
                if r2.status_code in [200, 201]:
                    _audit_log(
                        "GUARDIAN",
                        f"GHOST closed: {sym}",
                        f"Market sell order placed — size={size}"
                    )
                    send_telegram_msg(
                        f"🛡 GUARDIAN REPAIRED\n"
                        f"Ghost position closed: {sym}\n"
                        f"Size: {size}"
                    )
                else:
                    _audit_log("GUARDIAN", f"Close FAILED for {sym}", r2.text[:100])
            except Exception as ce:
                _audit_log("GUARDIAN", f"Exception closing {sym}", str(ce)[:100])

    # Case 2: DB says ACTIVE but exchange shows nothing — DB stuck
    elif count == 0 and db_active == "YES":
        _audit_log(
            "GUARDIAN",
            "DB_MISMATCH — DB=ACTIVE, Exchange=FLAT (expired or closed externally)",
            "Reset DB to FLAT"
        )
        send_telegram_msg(
            "🛡 GUARDIAN SYNC FIX\n"
            "DB showed ACTIVE but exchange is FLAT\n"
            "→ DB reset to FLAT state"
        )
        db.clear_option_position()

    else:
        log_terminal(f"Guardian: All OK — {count} position(s), DB={db_active}", "INFO")

# ═══════════════════════════════════════════════════════════
# MAIN SIGNAL LOOP

# ═══════════════════════════════════════════════════════════
def run_options_loop():
    """
    Core state machine — called every 5 minutes.

    States:
      FLAT    → Wait for signal → Enter CALL or PUT
      HOLDING → Check 2x target every cycle → Check flip on new candle
      BOOKING → (handled by check_profit_target inside options_executor)
    """
    global _last_processed_candle_ts

    # Load candle TS from DB on first call (survives restarts)
    if _last_processed_candle_ts == 0:
        saved_ts = db.get_param("last_processed_candle_ts", "0")
        try:
            _last_processed_candle_ts = int(float(saved_ts or "0"))
        except Exception:
            _last_processed_candle_ts = 0
        if _last_processed_candle_ts > 0:
            log_terminal(f"[GUARD] Loaded candle TS from DB: {_last_processed_candle_ts}", "INFO")

    if db.get_param("algo_running", "OFF") == "OFF":
        log_terminal("Engine is OFF — skipping loop.", "INFO")
        return

    # ── VPN GUARD: Delta Exchange only accepts 46.224.133.16 ──
    if not _check_vpn_guard():
        log_terminal(f"VPN not connected — trading paused. Need: {ALLOWED_TRADING_IP}", "WARN")
        return

    # ── FORCE-CLOSE CHECK ─────────────────────────────────
    force_closed_today = db.get_param("force_closed_today", "NO")
    if is_force_close_time():
        active = db.get_param("option_trade_active", "NO")
        if active == "YES" and force_closed_today == "NO":
            log_terminal("⏰ 3:20 PM IST — FORCE CLOSING ALL OPTIONS!", "ALERT")
            send_telegram_msg(
                "⏰ 3:20 PM FORCE CLOSE\n"
                "Closing all options to avoid theta decay overnight.\n"
                "Engine will re-evaluate next candle."
            )
            oe.close_option(reason="FORCE_CLOSE")
            db.set_param("force_closed_today", "YES")
        elif active == "NO":
            db.set_param("force_closed_today", "YES")
        return

    # Reset force-close flag at midnight
    now = datetime.datetime.now()
    if now.hour == 0 and now.minute < 10:
        db.set_param("force_closed_today", "NO")

    # ── PROFIT TARGET CHECK (every cycle — not just on new candle) ────
    # This runs BEFORE the candle check — 2x can happen anytime
    target_hit = oe.check_profit_target()
    if target_hit:
        log_terminal("🎯 2x booked! Re-evaluating signal...", "INFO")
        # Fall through — will re-enter below if signal still valid

    # ── FETCH SIGNAL ──────────────────────────────────────
    signal, st_value, last_close, latest_closed_ts = get_supertrend_signal()
    if signal is None:
        log_terminal("⏳ SuperTrend signal unavailable. Retrying next cycle.", "INFO")
        return

    # ── CANDLE-CHANGE GUARD ───────────────────────────────
    # Only process entry/flip logic when a NEW 15m candle has closed
    new_candle = (latest_closed_ts != 0 and latest_closed_ts > _last_processed_candle_ts)

    if not new_candle:
        log_terminal(
            f"⏸ Same 15m candle (ts={latest_closed_ts}) — only monitoring premium.",
            "INFO"
        )
        # Even on same candle — update dashboard with latest premium
        _update_premium_display()
        return

    # New candle detected — save TS to DB immediately (restart-safe)
    log_terminal(
        f"🕯 NEW 15m CANDLE CLOSED (ts={latest_closed_ts}) "
        f"| Close={last_close:.0f} | ST={st_value:.0f} | Signal={signal}",
        "INFO"
    )
    _last_processed_candle_ts = latest_closed_ts
    db.set_param("last_processed_candle_ts", str(latest_closed_ts))  # persist to DB

    # ── SELF-HEALING GUARDIAN v2 (qty-aware — runs on every new candle) ──
    _run_guardian()

    # ── READ CURRENT STATE ────────────────────────────────
    option_active  = db.get_param("option_trade_active", "NO")
    active_side    = db.get_param("active_option_side",  "NONE")  # CALL or PUT

    # ── SYNC with exchange (read-only — never clears DB here) ─────
    # Sync only updates entry_px/upnl if position found on exchange.
    # DB is ground truth — sync does NOT clear DB in this call.
    oe.sync_option_position()
    option_active = db.get_param("option_trade_active", "NO")  # re-read after sync

    # ── COLLECT ENTRY PARAMS ──────────────────────────────────
    distance_type  = db.get_param("distance_type",  "OTM2")
    # expiry_mode = key used by dashboard (app.py saves this key)
    expiry_pref    = db.get_param("expiry_mode",    "1DTE")
    qty            = int(db.get_param("trade_size", "1") or "1")

    def _enter_position(side):
        """Helper: fetch chain, find strike, buy option with smart expiry fallback."""
        chain = oe.get_option_chain()
        if not chain:
            log_terminal("Chain fetch failed — cannot enter.", "ERROR")
            return False
        expiry = oe.resolve_expiry(chain, expiry_pref)
        if expiry:
            test = [p for p in chain if p["type"] == side.upper() and p["expiry"] == expiry]
            if not test:
                log_terminal(f"No {side} options for {expiry_pref} ({expiry}) — trying fallback", "WARN")
                expiry = None
        if not expiry:
            for fb in ["1DTE", "2DTE", "0DTE", "3DTE", "NEAREST_WEEKLY"]:
                if fb == expiry_pref:
                    continue
                candidate = oe.resolve_expiry(chain, fb)
                if candidate:
                    test2 = [p for p in chain if p["type"] == side.upper() and p["expiry"] == candidate]
                    if test2:
                        log_terminal(f"Expiry fallback: {expiry_pref} not found, using {fb} ({candidate})", "INFO")
                        _audit_log("ENGINE", f"Expiry fallback: {expiry_pref} unavailable", f"Using {fb} ({candidate})")
                        expiry = candidate
                        break
        if not expiry:
            log_terminal("No valid expiry found in any fallback — cannot enter.", "ERROR")
            return False
        product = oe.find_strike(side, distance_type, last_close, chain, expiry)
        if not product:
            log_terminal(f"Strike not found for {side} {distance_type} — skipping.", "WARN")
            return False
        success, entry_px, trade_id = oe.buy_option(product, qty, side, distance_type)
        return success

    # ── STATE MACHINE ─────────────────────────────────────

    # [A] FLAT → Fresh entry
    if option_active == "NO":
        log_terminal(f"📭 FLAT → Entering {signal} position.", "TRADE")
        _enter_position(signal)
        return

    # [B] HOLDING SAME SIDE → Hold, no action needed
    if option_active == "YES" and active_side == signal:
        log_terminal(
            f"✋ HOLD: Already in {signal} position — trend unchanged.",
            "INFO"
        )
        _update_premium_display()
        return

    # [C] HOLDING OPPOSITE SIDE → TREND FLIP
    if option_active == "YES" and active_side != signal and active_side != "NONE":
        log_terminal(
            f"🔄 TREND FLIP! {active_side} → {signal} | "
            f"Close={last_close:.0f} ST={st_value:.0f}",
            "ALERT"
        )
        send_telegram_msg(
            f"🔄 TREND FLIP DETECTED\n"
            f"ST Value  : {st_value:,.0f}\n"
            f"15m Close : {last_close:,.0f}\n"
            f"Old Side  : {active_side}\n"
            f"New Side  : {signal}\n"
            f"→ Closing {active_side} options now..."
        )
        # Close current options
        success, exit_px, pnl = oe.close_option(reason="FLIP")
        if not success:
            log_terminal("Close failed on flip — NOT entering new position!", "ERROR")
            return
        time.sleep(2)  # Give exchange time to settle
        # Enter new direction
        log_terminal(f"🎯 Entering {signal} after flip.", "TRADE")
        _enter_position(signal)
        return

# ═══════════════════════════════════════════════════════════
# DASHBOARD PREMIUM DISPLAY HELPER
# ═══════════════════════════════════════════════════════════
def _update_premium_display():
    """Updates live premium data in DB for dashboard display."""
    symbol   = db.get_param("active_option_symbol",  "NONE")
    entry_px = float(db.get_param("active_option_entry_px", "0") or "0")
    if symbol == "NONE" or entry_px <= 0:
        return
    current_px = oe.get_option_ltp(symbol)
    if current_px > 0:
        pct = ((current_px - entry_px) / entry_px * 100)
        db.set_param("option_current_px", f"{current_px:.4f}")
        db.set_param("option_pct_gain",   f"{pct:.2f}")
        db.set_param("option_target_px",  f"{entry_px * 2:.4f}")

# ═══════════════════════════════════════════════════════════
# HEARTBEAT PULSE (every 15 min → Telegram)
# ═══════════════════════════════════════════════════════════
def send_pulse():
    """Sends a status update to Telegram every 15 minutes."""
    btc_close  = db.get_param("current_15m_close",  "0")
    st_val     = db.get_param("st_value",           "0")
    st_dir     = db.get_param("st_direction",       "?")
    signal     = db.get_param("last_signal",        "?")
    active     = db.get_param("option_trade_active","NO")
    side       = db.get_param("active_option_side", "NONE")
    symbol     = db.get_param("active_option_symbol","NONE")
    entry_px   = db.get_param("active_option_entry_px","0")
    curr_px    = db.get_param("option_current_px",  "0")
    pct_gain   = db.get_param("option_pct_gain",    "0")
    target_px  = db.get_param("option_target_px",   "0")
    mode       = db.get_param("trade_mode",         "PAPER")
    tf         = db.get_param("timeframe",          "15m")
    period     = db.get_param("st_period",          "10")
    mult       = db.get_param("st_multiplier",      "1.0")
    dist       = db.get_param("distance_type",      "OTM")

    pos_str = (
        f"HOLDING {side} ({dist})\n"
        f"  Option    : {symbol}\n"
        f"  Entry Px  : {entry_px}\n"
        f"  Current   : {curr_px}\n"
        f"  Gain      : {pct_gain}%\n"
        f"  2x Target : {target_px}"
    ) if active == "YES" else "FLAT — No position"

    send_telegram_msg(
        f"💓 OPTIONS ENGINE PULSE\n"
        f"Mode     : {mode}\n"
        f"TF       : {tf} | P={period} M={mult}\n"
        f"15m Close: {float(btc_close or 0):,.0f}\n"
        f"ST       : {float(st_val or 0):,.0f} ({st_dir})\n"
        f"Signal   : {signal}\n"
        f"Position : {pos_str}"
    )

# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════
def main():
    # ── Single-instance lock (prevents double-run) ────────
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(("127.0.0.1", 47301))  # Port 47301 = options engine
    except socket.error:
        print("BITCOIN OPTIONS ENGINE ALREADY RUNNING. EXITING.")
        sys.exit(1)

    print("=" * 62)
    print("  ⚡ BITCOIN OPTIONS ENGINE v1.0 — SUPERTREND")
    print("=" * 62)
    print("  Indicator : SuperTrend (Period=10, Mult=1)")
    print("  Timeframe : 15m closed candle — zero repaint")
    print("  Signal    : CALL (bullish) | PUT (bearish)")
    print("  Exit      : 2x premium auto-book | Trend flip | 3:20PM")
    print("=" * 62)

    if not db.load_secrets():
        sys.exit(1)

    # ── Set engine defaults (only if not already set by user) ─
    defaults = {
        "trade_size":         "1",
        "trade_mode":         "PAPER",
        "timeframe":          "15m",
        "st_period":          "10",
        "st_multiplier":      "1.0",
        "distance_type":      "OTM2",     # 2 strikes OTM
        "expiry_mode":        "1DTE",     # 1 day to expiry (dashboard key)
        "force_closed_today": "NO",
    }
    for k, v in defaults.items():
        if not db.get_param(k):
            db.set_param(k, v)

    # AUTO-START
    db.set_param("algo_running", "ON")

    mode   = db.get_param("trade_mode",    "PAPER")
    tf     = db.get_param("timeframe",     "15m")
    period = db.get_param("st_period",     "10")
    mult   = db.get_param("st_multiplier", "1.0")
    dist   = db.get_param("distance_type", "OTM")

    log_terminal("Bitcoin Options Engine v1.0 Started.", "START")

    # ── Startup signal check ──────────────────────────────
    log_terminal("Computing initial SuperTrend signal...", "INFO")
    init_sig, init_st, init_close, _ = get_supertrend_signal()
    btc_spot = oe.get_btc_spot_price()

    send_telegram_msg(
        f"⚡ BITCOIN OPTIONS ENGINE v1.0\n"
        f"Mode      : {mode}\n"
        f"TF        : {tf} | P={period} M={mult}\n"
        f"Distance  : {dist}\n"
        f"BTC Spot  : {btc_spot:,.0f}\n"
        f"15m Close : {init_close:,.0f}\n"
        f"ST Value  : {init_st:,.0f}\n"
        f"Signal    : {init_sig or 'Calculating...'} "
        f"{'📈 CALL' if init_sig == 'CALL' else ('📉 PUT' if init_sig == 'PUT' else '')}\n"
        f"Status    : AUTO-STARTED ✅"
    )

    last_pulse = 0

    # ── MAIN LOOP ─────────────────────────────────────────
    while True:
        try:
            # ── Core engine logic ─────────────────────────
            run_options_loop()

            # ── Settings watcher (dashboard → engine) ─────
            try:
                saved_at      = db.get_param("settings_updated_at", "0") or "0"
                last_notified = db.get_param("settings_notified_at", "0") or "0"
                if saved_at != "0" and saved_at != last_notified:
                    send_telegram_msg(
                        f"⚙️ SETTINGS UPDATED\n"
                        f"TF        : {db.get_param('timeframe','15m')}\n"
                        f"ST Period : {db.get_param('st_period','10')}\n"
                        f"ST Mult   : {db.get_param('st_multiplier','1.0')}\n"
                        f"Distance  : {db.get_param('distance_type','OTM')}\n"
                        f"OTM Offset: {db.get_param('otm_offset','2000')}\n"
                        f"ITM Offset: {db.get_param('itm_offset','5000')}\n"
                        f"Lots      : {db.get_param('trade_size','1')}\n"
                        f"Mode      : {db.get_param('trade_mode','PAPER')}"
                    )
                    db.set_param("settings_notified_at", saved_at)
            except Exception as se:
                print(f"[SETTINGS WATCH] {se}")

            # ── 15-min Telegram pulse ─────────────────────
            if time.time() - last_pulse > 900:  # 15 min
                send_pulse()
                last_pulse = time.time()

            # ── Sleep 5 minutes before next cycle ─────────
            log_terminal("💤 Sleeping 5 minutes until next candle check...", "INFO")
            time.sleep(300)

        except KeyboardInterrupt:
            log_terminal("Engine stopped by user (Ctrl+C).", "INFO")
            send_telegram_msg("⏹️ OPTIONS ENGINE STOPPED (Ctrl+C)")
            break
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            traceback.print_exc()
            send_telegram_msg(f"⚠️ ENGINE LOOP ERROR:\n{str(e)[:200]}")
            time.sleep(30)   # Short sleep on error — recover quickly


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("CRASH:")
        traceback.print_exc()
        sys.exit(1)
