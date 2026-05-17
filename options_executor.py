"""
BITCOIN OPTIONS EXECUTOR — Delta Exchange BTC Options
======================================================
LEGO Block 2 of 4 — options_executor.py  (v2 — updated)

Strike selection : OTM1/OTM2/OTM3/OTM4 · ATM · ITM1/ITM2/ITM3/ITM4
                   (Nth step away from ATM, not dollar offset)
Expiry selector  : 0DTE · 1DTE · 2DTE · 3DTE · Nearest Weekly
                   Nearer Monthly · This Monthly · Next Monthly
Contract size    : Auto-fetched from Delta Exchange product API
Multi-leg        : Dashboard controls how many legs to buy
======================================================
"""
import time
import hmac
import hashlib
import json
import socket
import requests
import db
from utils import log_terminal, send_telegram_msg

# ── Force IPv4 (prevents Delta Exchange auth failures) ───────
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

# ── API ENDPOINTS ────────────────────────────────────────────
BASE_URL     = "https://api.india.delta.exchange"
FALLBACK_URL = "https://api.delta.exchange"

# ── AUTH HEADER BUILDER ──────────────────────────────────────
def _auth_headers(method, path, payload="", query_string=""):
    """
    Builds HMAC-SHA256 signed headers for Delta Exchange.
    Same pattern as the working futures executor — proven.
    """
    api_key    = db.get_param("delta_api_key",    "")
    api_secret = db.get_param("delta_api_secret", "")
    timestamp  = str(int(time.time()))
    sig_data   = method + timestamp + path + query_string + payload
    signature  = hmac.new(
        api_secret.encode("utf-8"),
        sig_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return {
        "api-key":      api_key,
        "signature":    signature,
        "timestamp":    timestamp,
        "Content-Type": "application/json",
        "User-Agent":   "BHARAT-OPTIONS-ENGINE-V1"
    }

# ── SAFE REQUEST HELPER ───────────────────────────────────────
def _get(path, query_string="", auth=False):
    """
    GET request with India → Global fallback.
    Returns parsed JSON 'result' or None on failure.
    """
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            url     = f"{base}{path}{query_string}"
            headers = _auth_headers("GET", path, query_string=query_string) if auth else {}
            resp    = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("result", [])
            else:
                print(f"[GET] {base}{path} → HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            print(f"[GET ERR] {base}{path}: {e}")
    return None

def _post(path, payload_dict):
    """
    POST request (authenticated). India endpoint only — no fallback for orders.
    Returns full response JSON or None.
    """
    try:
        payload = json.dumps(payload_dict)
        headers = _auth_headers("POST", path, payload=payload)
        resp    = requests.post(f"{BASE_URL}{path}", headers=headers,
                                data=payload, timeout=10)
        return resp
    except Exception as e:
        log_terminal(f"[POST ERR] {path}: {e}", "ERROR")
        return None

# ═══════════════════════════════════════════════════════════
# SECTION 1 — BTC SPOT PRICE
# ═══════════════════════════════════════════════════════════

def get_btc_spot_price():
    """
    Returns the current BTC spot price from Delta Exchange.
    Used only to select strike prices — NOT for signals.
    Signal price comes from 15m closed candle (main.py).
    """
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/tickers?underlying_asset_symbols=BTC",
                timeout=5
            )
            if resp.status_code == 200:
                for t in resp.json().get("result", []):
                    sp = float(t.get("spot_price") or t.get("underlying_price") or 0)
                    if sp > 0:
                        return sp
        except Exception as e:
            print(f"[SPOT ERR] {e}")
    return 0.0

# ═══════════════════════════════════════════════════════════
# SECTION 2 — OPTION CHAIN FETCH + EXPIRY RESOLVER
# ═══════════════════════════════════════════════════════════

def get_option_chain(expiry_hint=None):
    """
    Fetches all BTC options (CALL + PUT) from Delta Exchange.

    expiry_hint: optional string like "27JUN25" to filter by expiry.
                 If None → returns ALL available BTC options.

    Returns list of product dicts:
      { id, symbol, strike_price, option_type, expiry_date, ... }
    """
    results = _get(
        "/v2/products",
        "?contract_types=call_options,put_options&underlying_asset_symbol=BTC&state=live"
    )
    if not results:
        log_terminal("Option chain fetch FAILED — no products returned", "ERROR")
        return []

    chain = []
    for p in results:
        try:
            # Delta Exchange uses 'contract_type' not 'option_type'
            # contract_type values: 'call_options' | 'put_options'
            ct = p.get("contract_type", "")
            if ct == "call_options":
                opt_type = "CALL"
            elif ct == "put_options":
                opt_type = "PUT"
            else:
                continue  # skip non-option products

            # Only include BTC options (skip ETH, etc.)
            symbol = p.get("symbol", "")
            if not (symbol.startswith("C-BTC") or symbol.startswith("P-BTC")):
                continue

            chain.append({
                "id":          p.get("id"),
                "symbol":      symbol,
                "strike":      float(p.get("strike_price") or 0),
                "type":        opt_type,               # "CALL" or "PUT"
                "expiry":      p.get("settlement_time", "")[:10],  # "2026-05-20"
                "expiry_raw":  p.get("settlement_time", ""),
                "description": p.get("description", ""),
            })
        except Exception:
            continue

    print(f"[CHAIN] Fetched {len(chain)} BTC option products")
    return chain

def resolve_expiry(chain, expiry_mode="NEAREST_WEEKLY"):
    """
    Returns the target expiry date string based on mode.

    Modes:
      0DTE          → Expires today (if available)
      1DTE          → Expires tomorrow
      2DTE          → Expires in 2 days
      3DTE          → Expires in 3 days
      NEAREST_WEEKLY  → Nearest Friday (weekly expiry)
      NEARER_MONTHLY  → Monthly expiry closest to now
      THIS_MONTHLY    → This calendar month's last Friday
      NEXT_MONTHLY    → Next calendar month's last Friday

    Returns: expiry date string "YYYY-MM-DD" or None
    """
    import datetime
    today = datetime.date.today()

    # Collect all available expiry dates from chain
    expiries = sorted(set(
        p["expiry"] for p in chain
        if p["expiry"] and p["expiry"] >= str(today)
    ))
    if not expiries:
        return None

    def to_date(s):
        try:
            return datetime.date.fromisoformat(s)
        except Exception:
            return None

    exp_dates = [(s, to_date(s)) for s in expiries if to_date(s)]

    # ── 0DTE / 1DTE / 2DTE / 3DTE ─────────────────────────
    if expiry_mode in ("0DTE", "1DTE", "2DTE", "3DTE"):
        offset = int(expiry_mode[0])  # 0,1,2,3
        target = today + datetime.timedelta(days=offset)
        for s, d in exp_dates:
            if d == target:
                return s
        # If exact day not available, return nearest day within range
        for s, d in exp_dates:
            if d >= target:
                return s
        return exp_dates[0][0] if exp_dates else None

    # ── NEAREST_WEEKLY ─────────────────────────────────────
    # Weekly options expire on Fridays
    if expiry_mode == "NEAREST_WEEKLY":
        for s, d in exp_dates:
            if d > today and d.weekday() == 4:  # Friday=4
                return s
        # Fallback: nearest available
        return exp_dates[0][0] if exp_dates else None

    # ── THIS_MONTHLY ───────────────────────────────────────
    # Last Friday of current month
    if expiry_mode == "THIS_MONTHLY":
        month_end = datetime.date(today.year, today.month,
                                  _last_day_of_month(today.year, today.month))
        last_fri  = month_end - datetime.timedelta(days=(month_end.weekday() - 4) % 7)
        target_str = str(last_fri)
        for s, d in exp_dates:
            if d == last_fri:
                return s
        # Return nearest available in this month
        this_month = [s for s, d in exp_dates
                      if d.year == today.year and d.month == today.month and d > today]
        return this_month[-1] if this_month else exp_dates[0][0]

    # ── NEXT_MONTHLY ───────────────────────────────────────
    if expiry_mode == "NEXT_MONTHLY":
        next_m = today.month % 12 + 1
        next_y = today.year if today.month < 12 else today.year + 1
        next_month_dates = [s for s, d in exp_dates
                            if d.year == next_y and d.month == next_m]
        return next_month_dates[-1] if next_month_dates else exp_dates[-1][0]

    # ── NEARER_MONTHLY ─────────────────────────────────────
    # Between this monthly and next monthly — pick nearer
    if expiry_mode == "NEARER_MONTHLY":
        monthly = [s for s, d in exp_dates
                   if d.day >= 25 or d.weekday() == 4]
        return monthly[0] if monthly else exp_dates[0][0]

    # Default fallback
    return exp_dates[0][0] if exp_dates else None


def _last_day_of_month(year, month):
    import calendar
    return calendar.monthrange(year, month)[1]


def get_nearest_expiry(chain):
    """Convenience wrapper — returns nearest available expiry."""
    return resolve_expiry(chain, "NEAREST_WEEKLY")


# ═══════════════════════════════════════════════════════════
# SECTION 2b — CONTRACT SIZE AUTO-FETCH
# ═══════════════════════════════════════════════════════════

def get_contract_size(product_id):
    """
    Fetches the contract size (lot size) for a given product from Delta Exchange.
    e.g. BTC options = 0.001 BTC per contract.
    Returns float contract_value, or 0.001 as safe default.
    """
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(f"{base}/v2/products/{product_id}", timeout=5)
            if resp.status_code == 200:
                p = resp.json().get("result", {})
                cv = float(p.get("contract_value") or p.get("contract_size") or 0)
                if cv > 0:
                    return cv
        except Exception as e:
            print(f"[CONTRACT SIZE ERR] {e}")
    return 0.001  # safe BTC options default


# ═══════════════════════════════════════════════════════════
# SECTION 3 — STRIKE SELECTION (OTM1-4 / ATM / ITM1-4)
# ═══════════════════════════════════════════════════════════

def find_strike(side, distance_type, btc_price, chain, expiry):
    """
    Finds the option contract by Nth step distance from ATM.

    distance_type values:
      "ATM"   → Strike nearest to current BTC price
      "OTM1"  → 1st strike away from ATM (out of the money direction)
      "OTM2"  → 2nd strike away from ATM
      "OTM3"  → 3rd strike away from ATM
      "OTM4"  → 4th strike away from ATM
      "ITM1"  → 1st strike into the money from ATM
      "ITM2"  → 2nd strike into the money
      "ITM3"  → 3rd strike into the money
      "ITM4"  → 4th strike into the money

    CALL direction: OTM = higher strikes, ITM = lower strikes
    PUT  direction: OTM = lower strikes,  ITM = higher strikes

    Returns: best matching product dict or None
    """
    # Filter: correct option type + correct expiry
    filtered = sorted(
        [p for p in chain if p["type"] == side.upper() and p["expiry"] == expiry],
        key=lambda p: p["strike"]
    )

    if not filtered:
        log_terminal(f"No {side} options found for expiry {expiry}", "WARN")
        return None

    # Find ATM index (strike nearest to BTC price)
    atm_idx = min(range(len(filtered)), key=lambda i: abs(filtered[i]["strike"] - btc_price))

    # Parse distance type → step count and direction
    if distance_type == "ATM":
        idx = atm_idx
    elif distance_type.startswith("OTM"):
        step = int(distance_type[3:])  # OTM1→1, OTM2→2 etc.
        if side.upper() == "CALL":
            idx = min(atm_idx + step, len(filtered) - 1)  # CALL OTM = higher strikes
        else:
            idx = max(atm_idx - step, 0)                  # PUT OTM = lower strikes
    elif distance_type.startswith("ITM"):
        step = int(distance_type[3:])  # ITM1→1, ITM2→2 etc.
        if side.upper() == "CALL":
            idx = max(atm_idx - step, 0)                  # CALL ITM = lower strikes
        else:
            idx = min(atm_idx + step, len(filtered) - 1)  # PUT ITM = higher strikes
    else:
        idx = atm_idx  # fallback to ATM

    best = filtered[idx]
    log_terminal(
        f"[STRIKE] {side} {distance_type} | BTC={btc_price:,.0f} "
        f"| ATM={filtered[atm_idx]['strike']:,.0f} "
        f"| Selected={best['strike']:,.0f} | {best['symbol']}",
        "INFO"
    )
    return best


def find_multiple_strikes(side, distance_types, btc_price, chain, expiry):
    """
    Finds multiple option contracts for simultaneous multi-leg entry.

    distance_types: list e.g. ["OTM1", "OTM2"] → returns 2 products
    Returns: list of product dicts (may be shorter if some not found)
    """
    results = []
    for dt in distance_types:
        p = find_strike(side, dt, btc_price, chain, expiry)
        if p:
            results.append((dt, p))
    return results

# ═══════════════════════════════════════════════════════════
# SECTION 4 — OPTION LTP (PREMIUM PRICE)
# ═══════════════════════════════════════════════════════════

def get_option_ltp(option_symbol):
    """
    Returns the current market price (LTP/mark price) of an option.
    Used to check if 2x target is reached.

    Returns float premium, or 0.0 on failure.
    """
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/tickers/{option_symbol}",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                # Try mark_price first (more stable), then last_price
                mark  = float(data.get("mark_price")  or 0)
                last  = float(data.get("last_price")   or 0)
                price = mark if mark > 0 else last
                if price > 0:
                    return price
        except Exception as e:
            print(f"[LTP ERR] {option_symbol}: {e}")
    return 0.0

# ═══════════════════════════════════════════════════════════
# SECTION 5 — BUY OPTION
# ═══════════════════════════════════════════════════════════

def buy_option(product, qty, signal_side, distance_type):
    """
    Places a market BUY order for the given option contract.

    Args:
        product       : Product dict from find_strike()
        qty           : Number of contracts
        signal_side   : "CALL" or "PUT" (for logging)
        distance_type : "OTM" / "ATM" / "ITM"

    Returns: (success: bool, entry_premium: float, trade_id: int)
    """
    mode       = db.get_param("trade_mode", "PAPER")
    product_id = product["id"]
    symbol     = product["symbol"]
    strike     = product["strike"]
    expiry     = product["expiry"]

    log_terminal(
        f"OPTION BUY: {signal_side} {distance_type} | {symbol} "
        f"| Strike={strike:,.0f} | Qty={qty} | Mode={mode}",
        "TRADE"
    )

    # ── Get current premium (entry price reference) ───────────
    entry_premium = get_option_ltp(symbol)
    if entry_premium <= 0:
        log_terminal(f"Cannot get premium for {symbol} — aborting entry", "ERROR")
        return False, 0.0, 0

    # ── PAPER MODE ────────────────────────────────────────────
    if mode == "PAPER":
        log_terminal(
            f"PAPER BUY: {symbol} @ premium={entry_premium:.2f} x {qty}",
            "TRADE"
        )
        # Log to DB
        trade_id = db.log_option_trade(
            signal_side   = signal_side,
            option_symbol = symbol,
            strike        = strike,
            expiry        = expiry,
            distance_type = distance_type,
            entry_premium = entry_premium,
            qty           = qty,
            status        = "OPEN"
        )
        # Set active position state
        db.set_option_position(
            symbol      = symbol,
            strike      = strike,
            side        = signal_side,
            expiry      = expiry,
            entry_px    = entry_premium,
            qty         = qty,
            trade_id    = trade_id,
            distance    = distance_type,
            product_id  = product_id
        )
        send_telegram_msg(
            f"📝 PAPER OPTION BUY\n"
            f"Side      : {signal_side} {distance_type}\n"
            f"Symbol    : {symbol}\n"
            f"Strike    : {strike:,.0f}\n"
            f"Expiry    : {expiry}\n"
            f"Premium   : {entry_premium:.2f}\n"
            f"Qty       : {qty}\n"
            f"2x Target : {entry_premium * 2:.2f}"
        )
        return True, entry_premium, trade_id

    # ── LIVE MODE ─────────────────────────────────────────────
    payload_dict = {
        "product_id": int(product_id),
        "size":       int(qty),
        "side":       "buy",
        "order_type": "market_order"
    }
    resp = _post("/v2/orders", payload_dict)

    if resp and resp.status_code in [200, 201]:
        # Fetch actual fill price after a short delay
        time.sleep(1.5)
        filled_premium = get_option_ltp(symbol)
        if filled_premium <= 0:
            filled_premium = entry_premium  # fallback to pre-order price

        log_terminal(
            f"✅ OPTION BUY SUCCESS: {symbol} @ {filled_premium:.2f} x {qty}",
            "TRADE"
        )
        # Log to DB
        trade_id = db.log_option_trade(
            signal_side   = signal_side,
            option_symbol = symbol,
            strike        = strike,
            expiry        = expiry,
            distance_type = distance_type,
            entry_premium = filled_premium,
            qty           = qty,
            status        = "OPEN"
        )
        # Set active position state
        db.set_option_position(
            symbol      = symbol,
            strike      = strike,
            side        = signal_side,
            expiry      = expiry,
            entry_px    = filled_premium,
            qty         = qty,
            trade_id    = trade_id,
            distance    = distance_type,
            product_id  = product_id
        )
        send_telegram_msg(
            f"🚀 LIVE OPTION BOUGHT\n"
            f"Side      : {signal_side} {distance_type}\n"
            f"Symbol    : {symbol}\n"
            f"Strike    : {strike:,.0f}\n"
            f"Expiry    : {expiry}\n"
            f"Premium   : {filled_premium:.2f}\n"
            f"Qty       : {qty}\n"
            f"2x Target : {filled_premium * 2:.2f}"
        )
        return True, filled_premium, trade_id
    else:
        err = resp.text[:200] if resp else "No response"
        log_terminal(f"OPTION BUY FAILED: {err}", "ERROR")
        send_telegram_msg(f"❌ OPTION BUY FAILED\n{symbol}\nError: {err[:100]}")
        return False, 0.0, 0

# ═══════════════════════════════════════════════════════════
# SECTION 6 — CLOSE OPTION (SQUARE OFF)
# ═══════════════════════════════════════════════════════════

def close_option(reason="MANUAL"):
    """
    Squares off the currently held option position.
    Reads state from DB — no arguments needed.

    reason: "2X_TARGET" | "FLIP" | "FORCE_CLOSE" | "MANUAL"

    Returns: (success: bool, exit_premium: float, pnl: float)
    """
    mode       = db.get_param("trade_mode",             "PAPER")
    symbol     = db.get_param("active_option_symbol",   "NONE")
    product_id = db.get_param("active_option_product_id", "0")
    entry_px   = float(db.get_param("active_option_entry_px", "0") or "0")
    qty        = int(db.get_param("active_option_qty",   "0") or "0")
    trade_id   = int(db.get_param("active_option_trade_id", "0") or "0")
    side       = db.get_param("active_option_side",     "NONE")

    if symbol == "NONE" or qty == 0:
        log_terminal("close_option: No active option position to close.", "WARN")
        return False, 0.0, 0.0

    log_terminal(
        f"CLOSING OPTION: {symbol} | Reason={reason} | Mode={mode}",
        "TRADE"
    )

    # Get current premium for PnL calc
    exit_premium = get_option_ltp(symbol)
    if exit_premium <= 0:
        exit_premium = entry_px  # safe fallback

    # PnL = (exit - entry) * qty  (BUY options — we always buy)
    pnl = (exit_premium - entry_px) * qty

    # ── PAPER MODE ────────────────────────────────────────────
    if mode == "PAPER":
        log_terminal(
            f"PAPER CLOSE: {symbol} | Entry={entry_px:.2f} "
            f"Exit={exit_premium:.2f} | PnL={pnl:+.2f}",
            "TRADE"
        )
        if trade_id > 0:
            db.close_option_trade(trade_id, exit_premium, round(pnl, 4), reason)
        db.clear_option_position()

        emoji = "✅" if pnl >= 0 else "🔴"
        send_telegram_msg(
            f"{emoji} PAPER OPTION CLOSED\n"
            f"Symbol    : {symbol}\n"
            f"Entry Px  : {entry_px:.2f}\n"
            f"Exit Px   : {exit_premium:.2f}\n"
            f"PnL       : {pnl:+.2f} USD\n"
            f"Reason    : {reason}"
        )
        return True, exit_premium, pnl

    # ── LIVE MODE ─────────────────────────────────────────────
    payload_dict = {
        "product_id":  int(product_id),
        "size":        int(qty),
        "side":        "sell",   # We bought — to close we sell
        "order_type":  "market_order",
        "reduce_only": True
    }
    resp = _post("/v2/orders", payload_dict)

    if resp and resp.status_code in [200, 201]:
        # Wait for fill then get actual exit price
        time.sleep(1.5)
        actual_exit = get_option_ltp(symbol)
        if actual_exit <= 0:
            actual_exit = exit_premium

        pnl = (actual_exit - entry_px) * qty

        log_terminal(
            f"✅ OPTION CLOSED: {symbol} | Entry={entry_px:.2f} "
            f"Exit={actual_exit:.2f} | PnL={pnl:+.2f}",
            "TRADE"
        )
        if trade_id > 0:
            db.close_option_trade(trade_id, actual_exit, round(pnl, 4), reason)
        db.clear_option_position()

        emoji = "✅" if pnl >= 0 else "🔴"
        send_telegram_msg(
            f"{emoji} LIVE OPTION CLOSED\n"
            f"Symbol    : {symbol}\n"
            f"Side      : {side}\n"
            f"Entry Px  : {entry_px:.2f}\n"
            f"Exit Px   : {actual_exit:.2f}\n"
            f"PnL       : {pnl:+.2f} USD\n"
            f"Reason    : {reason}"
        )
        return True, actual_exit, pnl
    else:
        err = resp.text[:200] if resp else "No response"
        log_terminal(f"OPTION CLOSE FAILED: {err}", "ERROR")
        send_telegram_msg(
            f"❌ OPTION CLOSE FAILED\n"
            f"Symbol : {symbol}\n"
            f"Error  : {err[:100]}\n"
            f"⚠️ MANUAL ACTION NEEDED on Delta Exchange!"
        )
        return False, 0.0, 0.0

# ═══════════════════════════════════════════════════════════
# SECTION 7 — SYNC POSITION FROM EXCHANGE
# ═══════════════════════════════════════════════════════════

def sync_option_position():
    """
    Reads live option positions from Delta Exchange.
    Updates DB if the exchange shows a position we don't know about,
    OR clears DB if exchange shows no position but DB says YES.

    Returns: True if position found on exchange, False if flat.
    """
    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return False

    path  = "/v2/positions"
    query = "?underlying_asset_symbol=BTC"
    result = _get(path, query, auth=True)

    if result is None:
        log_terminal("sync_option_position: API call failed", "WARN")
        return False

    # Find any open option position (not perpetual futures)
    option_found = False
    for p in result:
        sz = float(p.get("size", 0))
        if sz == 0:
            continue
        symbol = p.get("product", {}).get("symbol") or p.get("symbol", "")
        # BTC options use format C-BTC-XXXXX-DDMMYY or P-BTC-XXXXX-DDMMYY
        if symbol.startswith("C-BTC") or symbol.startswith("P-BTC"):
            option_found = True
            # Update DB with live position data
            entry_px = float(p.get("avg_entry_price", 0))
            upnl     = float(p.get("unrealized_pnl",  0))
            db.set_param("active_option_entry_px", str(entry_px))
            db.set_param("option_unrealized_pnl",  str(round(upnl, 4)))
            log_terminal(
                f"[SYNC] Exchange option: {symbol} | Size={sz} | Entry={entry_px:.2f} | uPnL={upnl:+.4f}",
                "INFO"
            )
            break

    if not option_found:
        local_active = db.get_param("option_trade_active", "NO")
        if local_active == "YES":
            log_terminal(
                "[SYNC] Exchange shows NO option position but DB says YES — clearing DB.",
                "ALERT"
            )
            db.clear_option_position()
            send_telegram_msg(
                "⚠️ SYNC ALERT\n"
                "Exchange: 0 option positions\n"
                "DB was showing ACTIVE — cleared automatically."
            )

    return option_found

# ═══════════════════════════════════════════════════════════
# SECTION 8 — CHECK 2X PROFIT TARGET
# ═══════════════════════════════════════════════════════════

def check_profit_target():
    """
    Checks if the current held option has reached the 2x premium target.
    Called every loop cycle in main.py.

    Returns: True if 2x hit (and position closed), False otherwise.
    """
    active = db.get_param("option_trade_active", "NO")
    if active != "YES":
        return False

    symbol   = db.get_param("active_option_symbol",   "NONE")
    entry_px = float(db.get_param("active_option_entry_px", "0") or "0")

    if symbol == "NONE" or entry_px <= 0:
        return False

    current_px = get_option_ltp(symbol)
    if current_px <= 0:
        log_terminal(f"2x check: Cannot get LTP for {symbol}", "WARN")
        return False

    target_px = entry_px * 2.0
    pct_gain  = ((current_px - entry_px) / entry_px * 100)

    db.set_param("option_current_px",  str(current_px))
    db.set_param("option_pct_gain",    f"{pct_gain:.2f}")
    db.set_param("option_target_px",   str(target_px))

    log_terminal(
        f"💰 Premium Check: Entry={entry_px:.2f} | Now={current_px:.2f} "
        f"| Target={target_px:.2f} | Gain={pct_gain:+.1f}%",
        "INFO"
    )

    if current_px >= target_px:
        log_terminal(
            f"🎯 2X TARGET HIT! Entry={entry_px:.2f} → Now={current_px:.2f}",
            "TRADE"
        )
        send_telegram_msg(
            f"🎯 2X PROFIT TARGET HIT!\n"
            f"Symbol : {symbol}\n"
            f"Entry  : {entry_px:.2f}\n"
            f"Current: {current_px:.2f}\n"
            f"Gain   : {pct_gain:+.1f}%\n"
            f"→ Auto square-off triggered..."
        )
        close_option(reason="2X_TARGET")
        return True

    return False
