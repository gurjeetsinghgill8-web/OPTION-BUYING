"""Close 1 extra lot of P-BTC-76400-190526 (reduce from size=2 to size=1)"""
import paramiko, sys
from scp import SCPClient
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

def run(cmd, wait=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if err and 'Warning' not in err: print("[ERR]", err[:200])
    return out

helper = """\
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
"""

with open('_close1lot.py', 'w', encoding='utf-8') as f:
    f.write(helper)
with SCPClient(ssh.get_transport()) as scp:
    scp.put('_close1lot.py', '/tmp/_close1lot.py')
print("Uploaded. Running...")

out = run("cd /root/OPTION-BUYING && python3 /tmp/_close1lot.py", wait=30)
print(out)
ssh.close()
