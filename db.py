"""
BITCOIN OPTIONS ENGINE — DATABASE MODULE
=========================================
LEGO Block 1 of 4 — db.py
Maintains ALL state for the Options Engine.
Fully backward-compatible: existing settings/trades tables untouched.
New: options_trades table + option position state keys.
"""
import os
import sqlite3
from datetime import datetime

# ── DB FILE ──────────────────────────────────────────────────
# Renamed to reflect the new options engine purpose
DB_NAME = "options_engine.db"

# ── INIT — CREATE ALL TABLES ─────────────────────────────────
def init_db():
    """
    Creates all required tables if they don't exist.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ── SETTINGS TABLE (key-value store for all engine params)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings
        (key TEXT PRIMARY KEY, value TEXT)
    """)

    # ── OPTIONS TRADES TABLE (new — options-specific)
    # Tracks every option BUY → EXIT cycle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS options_trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT,       -- Entry time
            exit_timestamp  TEXT,       -- Exit time
            signal_side     TEXT,       -- CALL or PUT
            option_symbol   TEXT,       -- e.g. BTC-27JUN-100000-C
            strike          REAL,       -- Strike price in USD
            expiry          TEXT,       -- Expiry date string
            distance_type   TEXT,       -- OTM / ATM / ITM
            entry_premium   REAL,       -- Premium paid per contract
            exit_premium    REAL,       -- Premium received at exit
            qty             INTEGER,    -- Number of contracts
            pnl             REAL,       -- Net PnL in USD
            exit_reason     TEXT,       -- 2X_TARGET / FLIP / FORCE_CLOSE / MANUAL
            status          TEXT        -- OPEN / CLOSED / BOOKED
        )
    """)

    # ── LEGACY FUTURES TRADES TABLE (keep for history — do not delete)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            symbol      TEXT,
            direction   TEXT,
            entry_price REAL,
            exit_price  REAL,
            status      TEXT,
            pnl         REAL,
            qty         INTEGER
        )
    """)

    # ── DAILY STATS TABLE (keep for history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats
        (date TEXT PRIMARY KEY, total_pnl REAL, status TEXT)
    """)

    conn.commit()
    conn.close()

# ── SECRETS LOADER ───────────────────────────────────────────
def load_secrets():
    """
    Loads API keys from secrets.txt into DB.
    RULE: trade_mode is NEVER loaded from secrets — dashboard controls it.
    """
    secrets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.txt")
    if not os.path.exists(secrets_file):
        print("\n" + "!" * 60)
        print(f"CRITICAL ERROR: secrets.txt NOT FOUND at {secrets_file}")
        print("Format required:")
        print("  DELTA_API_KEY=your_key")
        print("  DELTA_API_SECRET=your_secret")
        print("  TELEGRAM_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("!" * 60 + "\n")
        return False

    _key_map = {
        'telegram_token':   'telegram_bot_token',
        'delta_api_key':    'delta_api_key',
        'delta_api_secret': 'delta_api_secret',
        'trade_mode':       'trade_mode',        # will be skipped below
        'telegram_chat_id': 'telegram_chat_id',
    }

    loaded = []
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            parts = line.split('=', 1)
            if len(parts) != 2:
                continue
            k      = parts[0].strip().lower()
            v      = parts[1].strip()
            db_key = _key_map.get(k, k)
            # NEVER override trade_mode from secrets — dashboard only
            if k == 'trade_mode':
                continue
            set_param(db_key, v)
            loaded.append(db_key)

    print(f"[secrets] Loaded {len(loaded)} keys: {loaded}")
    return True

# ── SETTINGS GET / SET ───────────────────────────────────────
def set_param(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()

def get_param(key, default=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

# ── OPTION TRADE LOGGING ─────────────────────────────────────
def log_option_trade(signal_side, option_symbol, strike, expiry,
                     distance_type, entry_premium, qty,
                     exit_premium=0.0, pnl=0.0,
                     exit_reason="", status="OPEN"):
    """
    Logs a new option trade to options_trades table.
    Call with status='OPEN' on entry, then update with close_option_trade() on exit.
    Returns the new trade ID.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO options_trades
        (timestamp, signal_side, option_symbol, strike, expiry,
         distance_type, entry_premium, exit_premium, qty, pnl,
         exit_reason, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, signal_side, option_symbol, strike, expiry,
          distance_type, entry_premium, exit_premium, qty, pnl,
          exit_reason, status))
    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()
    return trade_id

def close_option_trade(trade_id, exit_premium, pnl, exit_reason="2X_TARGET"):
    """
    Marks an open option trade as CLOSED/BOOKED.
    Called when 2x target hit, flip, or force-close.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    exit_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status  = "BOOKED" if exit_reason == "2X_TARGET" else "CLOSED"
    cursor.execute("""
        UPDATE options_trades
        SET exit_timestamp=?, exit_premium=?, pnl=?, exit_reason=?, status=?
        WHERE id=?
    """, (exit_ts, exit_premium, pnl, exit_reason, status, trade_id))
    conn.commit()
    conn.close()

# ── OPTION POSITION STATE ────────────────────────────────────
# These keys live in the 'settings' table — simple key-value state machine

OPTION_STATE_KEYS = [
    "option_trade_active",      # YES / NO
    "active_option_symbol",     # e.g. "BTC-27JUN25-100000-C"
    "active_option_strike",     # e.g. "100000"
    "active_option_side",       # CALL / PUT
    "active_option_expiry",     # e.g. "27JUN25"
    "active_option_entry_px",   # Premium paid at entry
    "active_option_qty",        # Number of contracts
    "active_option_trade_id",   # DB row ID for closing
    "active_option_distance",   # OTM / ATM / ITM
    "active_option_product_id", # Delta product_id for the option
]

def set_option_position(symbol, strike, side, expiry, entry_px,
                        qty, trade_id, distance, product_id):
    """Sets all option position state keys atomically."""
    set_param("option_trade_active",      "YES")
    set_param("active_option_symbol",     symbol)
    set_param("active_option_strike",     str(strike))
    set_param("active_option_side",       side)
    set_param("active_option_expiry",     expiry)
    set_param("active_option_entry_px",   str(entry_px))
    set_param("active_option_qty",        str(qty))
    set_param("active_option_trade_id",   str(trade_id))
    set_param("active_option_distance",   distance)
    set_param("active_option_product_id", str(product_id))

def clear_option_position():
    """Resets all option position state to FLAT."""
    set_param("option_trade_active",      "NO")
    set_param("active_option_symbol",     "NONE")
    set_param("active_option_strike",     "0")
    set_param("active_option_side",       "NONE")
    set_param("active_option_expiry",     "NONE")
    set_param("active_option_entry_px",   "0")
    set_param("active_option_qty",        "0")
    set_param("active_option_trade_id",   "0")
    set_param("active_option_distance",   "NONE")
    set_param("active_option_product_id", "0")
    print("[DB] Option position cleared — FLAT state.")

# ── OPTION STATS ─────────────────────────────────────────────
def get_option_stats(days=1):
    """
    Returns (total_pnl, trade_count, win_rate, avg_pnl)
    for closed option trades in the last N days.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    since = f'-{days} days'
    cursor.execute(
        "SELECT SUM(pnl) FROM options_trades WHERE timestamp >= datetime('now', ?) AND status != 'OPEN'",
        (since,)
    )
    total_pnl = cursor.fetchone()[0] or 0.0

    cursor.execute(
        "SELECT COUNT(*) FROM options_trades WHERE timestamp >= datetime('now', ?) AND status != 'OPEN'",
        (since,)
    )
    count = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT COUNT(*) FROM options_trades WHERE pnl > 0 AND timestamp >= datetime('now', ?) AND status != 'OPEN'",
        (since,)
    )
    wins = cursor.fetchone()[0] or 0

    win_rate = (wins / count * 100) if count > 0 else 0.0
    avg_pnl  = (total_pnl / count)  if count > 0 else 0.0
    conn.close()
    return total_pnl, count, win_rate, avg_pnl

def get_recent_option_trades(limit=20):
    """
    Returns last N option trades for dashboard display.
    Columns: timestamp, signal_side, option_symbol, strike,
             distance_type, entry_premium, exit_premium, pnl, exit_reason, status
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, signal_side, option_symbol, strike,
               distance_type, entry_premium, exit_premium, pnl, exit_reason, status
        FROM options_trades
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ── LEGACY: Futures stats (keep for backward compat) ─────────
def get_stats(days=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pnl) FROM trades WHERE timestamp >= datetime('now', ?)", (f'-{days} days',))
    total_pnl = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(*) FROM trades WHERE timestamp >= datetime('now', ?)", (f'-{days} days',))
    count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0 AND timestamp >= datetime('now', ?)", (f'-{days} days',))
    wins = cursor.fetchone()[0] or 0
    win_rate = (wins / count * 100) if count > 0 else 0.0
    avg_pnl  = (total_pnl / count)  if count > 0 else 0.0
    conn.close()
    return total_pnl, count, win_rate, avg_pnl

def get_recent_trades(limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, symbol, direction, entry_price, exit_price, pnl, status FROM trades ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def log_trade(symbol, direction, entry_price, exit_price, pnl, qty=1, status="CLOSED"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO trades (timestamp, symbol, direction, entry_price, exit_price, status, pnl, qty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, symbol, direction, entry_price, exit_price, status, pnl, qty))
    conn.commit()
    conn.close()

# ── HARD RESET ───────────────────────────────────────────────
def hard_reset_db():
    """
    Nuclear reset — clears ALL trading state (both futures and options).
    Called from dashboard emergency button.
    """
    # Options state
    clear_option_position()

    # Legacy futures state
    futures_keys = [
        "algo_running", "active_symbol", "active_pid", "active_direction",
        "active_entry_price", "active_qty", "local_trade_active",
        "unrealized_pnl", "last_signal", "signal_target",
        "order_pending", "crypto_active_symbol",
    ]
    for k in futures_keys:
        set_param(k, "NONE" if ("symbol" in k or "direction" in k or "signal" in k) else "0")

    set_param("algo_running",       "OFF")
    set_param("local_trade_active", "NO")
    set_param("order_pending",      "NO")
    set_param("active_symbol",      "NONE")
    set_param("active_direction",   "NONE")

    print("[HARD RESET] All trading state cleared — Options + Futures.")

# ── AUTO-INIT ON IMPORT ──────────────────────────────────────
init_db()
