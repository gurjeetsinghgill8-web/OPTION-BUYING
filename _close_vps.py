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

def hdrs(method, path, query='', payload=''):
    ts  = str(int(time.time()))
    sig = hmac.new(api_secret.encode(),
                   (method+ts+path+query+payload).encode(),
                   hashlib.sha256).hexdigest()
    return {'api-key': api_key, 'signature': sig,
            'timestamp': ts, 'Content-Type': 'application/json'}

db_sym = db.get_param('active_option_symbol', 'NONE')
print('DB active symbol:', db_sym)

# Try both endpoints
positions = []
for path, query in [('/v2/positions', '?underlying_asset_symbol=BTC'),
                    ('/v2/positions/margined', '')]:
    r = requests.get(BASE + path + query,
                     headers=hdrs('GET', path, query), timeout=10)
    print(f'{path} -> HTTP {r.status_code}')
    if r.status_code == 200:
        for p in r.json().get('result', []):
            sym = (p.get('product', {}) or {}).get('symbol') or p.get('symbol', '')
            sz  = float(p.get('size', 0))
            pid = (p.get('product', {}) or {}).get('id') or p.get('product_id', 0)
            if sz > 0 and (sym.startswith('C-BTC') or sym.startswith('P-BTC')):
                positions.append({'symbol': sym, 'size': int(sz), 'pid': int(pid or 0)})
                print(f'  OPEN: {sym}  size={sz}  pid={pid}')

print(f'Total open options: {len(positions)}')

# Close all except DB symbol
for pos in positions:
    if pos['symbol'] == db_sym:
        print(f'KEEPING: {pos["symbol"]}')
        continue
    print(f'CLOSING: {pos["symbol"]}')
    pl = json.dumps({'product_id': pos['pid'], 'size': pos['size'],
                     'side': 'sell', 'order_type': 'market_order',
                     'reduce_only': True})
    ts = str(int(time.time()))
    sig = hmac.new(api_secret.encode(),
                   ('POST' + ts + '/v2/orders' + '' + pl).encode(),
                   hashlib.sha256).hexdigest()
    h = {'api-key': api_key, 'signature': sig,
         'timestamp': ts, 'Content-Type': 'application/json'}
    resp = requests.post(BASE + '/v2/orders', headers=h, data=pl, timeout=10)
    print(f'  Result: {resp.status_code}', resp.text[:200])
print('Done.')
