import sys, hmac, hashlib, time, json, requests, socket
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
sys.path.insert(0, '/root/OPTION-BUYING')
import db
db.init_db()
db.load_secrets()

api_key    = db.get_param('delta_api_key', '')
api_secret = db.get_param('delta_api_secret', '')
BASE       = 'https://api.india.delta.exchange'

# Current: P-BTC-76400-190526  size=2, pid=134819
# Sell 1 lot (reduce_only) — keep 1
product_id = 134819
sell_size   = 1   # close only 1 extra lot
symbol      = 'P-BTC-76400-190526'

payload = json.dumps({
    'product_id': product_id,
    'size':       sell_size,
    'side':       'sell',
    'order_type': 'market_order',
    'reduce_only': True
})
ts  = str(int(time.time()))
sig = hmac.new(api_secret.encode(),
               ('POST' + ts + '/v2/orders' + '' + payload).encode(),
               hashlib.sha256).hexdigest()
hdrs = {'api-key': api_key, 'signature': sig,
        'timestamp': ts, 'Content-Type': 'application/json'}

print(f'Selling 1 lot of {symbol}...')
resp = requests.post(BASE + '/v2/orders', headers=hdrs, data=payload, timeout=10)
print(f'HTTP {resp.status_code}')
print(resp.text[:300])

# Verify remaining
import time as t
t.sleep(2)
r2 = requests.get(BASE + '/v2/positions?underlying_asset_symbol=BTC', headers=hdrs, timeout=10)
if r2.status_code == 200:
    for p in r2.json().get('result', []):
        sym = (p.get('product', {}) or {}).get('symbol', '')
        sz  = p.get('size', 0)
        if sym.startswith(('C-BTC','P-BTC')) and float(sz) > 0:
            print(f'Remaining: {sym}  size={sz}')
print('Done.')
