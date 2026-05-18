"""
DIAGNOSTIC SCRIPT — Run on VPS to identify why OPTION CLOSE fails.
Usage: python3 diag_api.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import time
import hmac
import hashlib
import json
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn

urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

BASE = "https://api.india.delta.exchange"
FALLBACK = "https://api.delta.exchange"

print("=" * 60)
print("  OPTION ENGINE — API DIAGNOSTIC")
print("=" * 60)

# === 1. DB STATE ===
print("\n[1] DB STATE:")
trade_active = db.get_param("option_trade_active", "NO")
symbol       = db.get_param("active_option_symbol", "NONE")
product_id   = db.get_param("active_option_product_id", "0")
qty          = db.get_param("active_option_qty", "0")
side         = db.get_param("active_option_side", "NONE")
entry_px     = db.get_param("active_option_entry_px", "0")
trade_mode   = db.get_param("trade_mode", "PAPER")
api_key      = db.get_param("delta_api_key", "")
api_secret   = db.get_param("delta_api_secret", "")

print(f"  trade_active : {trade_active}")
print(f"  symbol       : {symbol}")
print(f"  product_id   : {product_id}")
print(f"  qty          : {qty}")
print(f"  side         : {side}")
print(f"  entry_px     : {entry_px}")
print(f"  trade_mode   : {trade_mode}")
print(f"  api_key      : {api_key[:12]}...")
print(f"  api_secret   : {api_secret[:12]}...")

# === 2. TEST GET POSITIONS ===
print("\n[2] TEST GET /v2/positions:")
ts  = str(int(time.time()))
path = "/v2/positions"
query = "?underlying_asset_symbol=BTC"
sig_data = "GET" + ts + path + query
sig = hmac.new(api_secret.encode("utf-8"), sig_data.encode("utf-8"), hashlib.sha256).hexdigest()
headers = {
    "api-key": api_key,
    "signature": sig,
    "timestamp": ts,
    "Content-Type": "application/json",
    "User-Agent": "BHARAT-OPTIONS-ENGINE-V1"
}
for base in [BASE, FALLBACK]:
    try:
        resp = requests.get(base + path + query, headers=headers, timeout=10)
        print(f"  {base} → HTTP {resp.status_code}")
        print(f"  Body: {resp.text[:400]}")
        break
    except Exception as e:
        print(f"  {base} → EXCEPTION: {e}")

# === 3. TEST POST /v2/orders (DRY-RUN — CLOSE 0 SIZE TO SEE AUTH ERROR) ===
print("\n[3] TEST POST /v2/orders (auth check — will fail with 'insufficient qty', that's OK):")
pid_int = int(product_id or 0)
if pid_int == 0:
    print("  SKIP — product_id is 0, can't test order endpoint")
else:
    payload_dict = {
        "product_id":  pid_int,
        "size":        int(qty or 0),
        "side":        "sell",
        "order_type":  "market_order",
        "reduce_only": True
    }
    payload = json.dumps(payload_dict)
    ts2 = str(int(time.time()))
    sig_data2 = "POST" + ts2 + "/v2/orders" + "" + payload
    sig2 = hmac.new(api_secret.encode("utf-8"), sig_data2.encode("utf-8"), hashlib.sha256).hexdigest()
    headers2 = {
        "api-key": api_key,
        "signature": sig2,
        "timestamp": ts2,
        "Content-Type": "application/json",
        "User-Agent": "BHARAT-OPTIONS-ENGINE-V1"
    }
    print(f"  Payload: {payload_dict}")
    try:
        resp2 = requests.post(BASE + "/v2/orders", headers=headers2, data=payload, timeout=10)
        print(f"  HTTP Status: {resp2.status_code}")
        print(f"  Response: {resp2.text[:500]}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")

# === 4. CHECK CURRENT PUBLIC IP ===
print("\n[4] CURRENT PUBLIC IP:")
try:
    ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    print(f"  IP = {ip}")
    if ip == "46.224.133.16":
        print("  ✅ VPN IP CORRECT — Delta Exchange will accept orders")
    else:
        print(f"  ❌ WRONG IP! Delta Exchange needs 46.224.133.16 — got {ip}")
        print("  THIS IS WHY ORDERS FAIL — VPN is disconnected!")
except Exception as e:
    print(f"  IP check failed: {e}")

# === 5. TEST OPTION LTP ===
print(f"\n[5] TEST LTP for {symbol}:")
if symbol != "NONE":
    for base in [BASE, FALLBACK]:
        try:
            r = requests.get(f"{base}/v2/tickers/{symbol}", timeout=5)
            print(f"  {base} → HTTP {r.status_code}")
            print(f"  Body: {r.text[:300]}")
            break
        except Exception as e:
            print(f"  {base} → EXCEPTION: {e}")
else:
    print("  SKIP — no active symbol in DB")

print("\n" + "=" * 60)
print("  DIAGNOSTIC COMPLETE")
print("=" * 60)
