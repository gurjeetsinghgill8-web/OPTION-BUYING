"""
Close the EXTRA BTC option position on Delta Exchange.
Keeps the position matching current DB (P-BTC-76400-190526).
Closes the extra one (P-BTC-76600-190526).
"""
import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

vps_secrets = {}
for line in open(r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        vps_secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=vps_secrets['vps_password'], timeout=20)
print("[OK] Connected")

def run(cmd, wait=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Run on VPS — fetch all open BTC option positions, close extras
vps_code = r"""
import sys, os
sys.path.insert(0, '/root/OPTION-BUYING')
import hmac, hashlib, time, json, requests, socket
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

import db
db.init_db()
db.load_secrets()

api_key    = db.get_param('delta_api_key', '')
api_secret = db.get_param('delta_api_secret', '')
BASE       = 'https://api.india.delta.exchange'

def signed_headers(method, path, query='', payload=''):
    ts  = str(int(time.time()))
    sig = hmac.new(api_secret.encode(), (method+ts+path+query+payload).encode(), hashlib.sha256).hexdigest()
    return {'api-key': api_key, 'signature': sig, 'timestamp': ts, 'Content-Type': 'application/json'}

# Fetch all positions
resp = requests.get(BASE + '/v2/positions/margined', headers=signed_headers('GET', '/v2/positions/margined'), timeout=10)
print('[MARGINED STATUS]', resp.status_code)
if resp.status_code == 200:
    for p in resp.json().get('result', []):
        sym = (p.get('product', {}).get('symbol') or p.get('symbol', ''))
        sz  = float(p.get('size', 0))
        if sz > 0 and ('BTC' in sym):
            print('  POSITION:', sym, 'size=', sz)

# Try main positions endpoint
resp2 = requests.get(BASE + '/v2/positions?underlying_asset_symbol=BTC',
    headers=signed_headers('GET', '/v2/positions', '?underlying_asset_symbol=BTC'), timeout=10)
print('[POSITIONS STATUS]', resp2.status_code)
positions = []
if resp2.status_code == 200:
    for p in resp2.json().get('result', []):
        sym = (p.get('product', {}).get('symbol') or p.get('symbol', ''))
        sz  = float(p.get('size', 0))
        pid = p.get('product_id') or (p.get('product', {}) or {}).get('id', 0)
        if sz > 0 and (sym.startswith('C-BTC') or sym.startswith('P-BTC')):
            positions.append({'symbol': sym, 'size': int(sz), 'product_id': int(pid or 0)})
            print('  OPTION:', sym, 'size=', sz, 'pid=', pid)

print('Total BTC options found:', len(positions))
db_symbol = db.get_param('active_option_symbol', 'NONE')
print('DB active symbol:', db_symbol)

# Close all except DB symbol
for pos in positions:
    if pos['symbol'] == db_symbol:
        print('KEEPING:', pos['symbol'])
        continue
    print('CLOSING extra:', pos['symbol'], 'size=', pos['size'])
    payload = json.dumps({'product_id': pos['product_id'], 'size': pos['size'], 'side': 'sell', 'order_type': 'market_order', 'reduce_only': True})
    ts = str(int(time.time()))
    sig = hmac.new(api_secret.encode(), ('POST'+ts+'/v2/orders'+''+payload).encode(), hashlib.sha256).hexdigest()
    hdrs = {'api-key': api_key, 'signature': sig, 'timestamp': ts, 'Content-Type': 'application/json'}
    r = requests.post(BASE + '/v2/orders', headers=hdrs, data=payload, timeout=10)
    print('  Close result:', r.status_code, r.text[:150])
"""

print("\n[VPS] Running close script...")
out = run(f"cd /root/OPTION-BUYING && python3 -c {repr(vps_code)}", wait=30)
print(out)

ssh.close()
print("\nDone. Check Telegram for confirmation.")
