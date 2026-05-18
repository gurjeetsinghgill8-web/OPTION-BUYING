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
db_sym     = db.get_param('active_option_symbol', 'NONE')
db_qty     = int(db.get_param('active_option_qty', '1') or '1')
print(f'DB symbol: {db_sym}  qty: {db_qty}')

def signed_get(path, query=''):
    ts = str(int(time.time()))
    sig = hmac.new(api_secret.encode(), ('GET'+ts+path+query).encode(), hashlib.sha256).hexdigest()
    h = {'api-key': api_key, 'signature': sig, 'timestamp': ts, 'Content-Type': 'application/json'}
    return requests.get(BASE+path+query, headers=h, timeout=10)

def signed_post(path, pl):
    payload = json.dumps(pl)
    ts = str(int(time.time()))
    sig = hmac.new(api_secret.encode(), ('POST'+ts+path+payload).encode(), hashlib.sha256).hexdigest()
    h = {'api-key': api_key, 'signature': sig, 'timestamp': ts, 'Content-Type': 'application/json'}
    return requests.post(BASE+path, headers=h, data=payload, timeout=10)

r = signed_get('/v2/positions', '?underlying_asset_symbol=BTC')
print(f'Positions HTTP: {r.status_code}')
positions = []
if r.status_code == 200:
    for p in r.json().get('result', []):
        sym = (p.get('product',{}) or {}).get('symbol','')
        sz  = float(p.get('size', 0))
        pid = (p.get('product',{}) or {}).get('id', 0)
        if sz > 0 and (sym.startswith('C-BTC') or sym.startswith('P-BTC')):
            positions.append({'symbol': sym, 'size': int(sz), 'pid': int(pid or 0)})
            print(f'  OPEN: {sym}  size={sz}  pid={pid}')

print(f'Total open options: {len(positions)}')

# Close anything NOT matching DB symbol, or extra lots of DB symbol
for pos in positions:
    if pos['symbol'] == db_sym:
        extra = pos['size'] - db_qty
        if extra > 0:
            print(f'CLOSING {extra} extra lot(s) of {pos["symbol"]}')
            r2 = signed_post('/v2/orders', {'product_id': pos['pid'], 'size': extra,
                                             'side': 'sell', 'order_type': 'market_order', 'reduce_only': True})
            print(f'  Result: {r2.status_code}', r2.text[:100])
        else:
            print(f'OK: {pos["symbol"]} size={pos["size"]} matches DB')
    else:
        print(f'CLOSING non-DB position: {pos["symbol"]} size={pos["size"]}')
        r2 = signed_post('/v2/orders', {'product_id': pos['pid'], 'size': pos['size'],
                                         'side': 'sell', 'order_type': 'market_order', 'reduce_only': True})
        print(f'  Result: {r2.status_code}', r2.text[:100])

print('Done.')
