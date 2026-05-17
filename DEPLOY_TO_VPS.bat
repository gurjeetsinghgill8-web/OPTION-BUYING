@echo off
title BHARAT FUTURES - VPS DEPLOY
color 0B

python -c "
import sys, subprocess, os

secrets_file = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'
src_folder   = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'

# Read secrets
cfg = {}
with open(secrets_file, 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        cfg[k.strip()] = v.strip()

vps_ip   = cfg.get('VPS_IP', '')
vps_user = cfg.get('VPS_USER', 'root')
vps_pass = cfg.get('VPS_PASSWORD', '')

print('============================================================')
print('  BHARAT FUTURES ENGINE - VPS DEPLOY')
print('============================================================')
print(f'  VPS: {vps_user}@{vps_ip}')

if not vps_ip:
    print('ERROR: VPS_IP missing in secrets.txt')
    sys.exit(1)
if vps_pass == 'FILL_YOUR_VPS_PASSWORD_HERE' or not vps_pass:
    print('ERROR: Fill VPS_PASSWORD in secrets.txt first!')
    sys.exit(1)

# Download plink + pscp if needed
plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
pscp  = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\pscp.exe'

if not os.path.exists(plink):
    print('Downloading plink.exe...')
    import urllib.request
    urllib.request.urlretrieve('https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe', plink)
    urllib.request.urlretrieve('https://the.earth.li/~sgtatham/putty/latest/w64/pscp.exe',  pscp)
    print('Downloaded!')

def ssh(cmd):
    r = subprocess.run([plink, '-pw', vps_pass, '-batch', '-ssh',
                        f'{vps_user}@{vps_ip}', cmd],
                       capture_output=True, text=True, timeout=60)
    if r.stdout: print(r.stdout.strip())
    if r.stderr and 'WARNING' not in r.stderr: print(r.stderr.strip())
    return r.returncode

def scp():
    r = subprocess.run([pscp, '-pw', vps_pass, '-batch', '-r',
                        src_folder + chr(92) + '*',
                        f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
                       capture_output=True, text=True, timeout=120)
    if r.stdout: print(r.stdout[-500:].strip())
    return r.returncode

print()
print('[1/4] Creating folder on VPS...')
ssh('mkdir -p /root/bharat-futures-engine')

print('[2/4] Uploading files...')
ssh('mkdir -p /root/bharat-futures-engine')
rc = scp()
print(f'  Upload done (code={rc})')

print('[3/4] Installing packages...')
ssh('pip3 install streamlit requests pandas numpy --quiet 2>&1 | tail -3')

print('[4/4] Starting Bot + Dashboard...')
ssh('cd /root/bharat-futures-engine && pkill -f main.py 2>/dev/null; pkill -f streamlit 2>/dev/null; sleep 2; nohup python3 main.py > bot.log 2>&1 & nohup python3 -m streamlit run app.py --server.port 8600 --server.headless true > dash.log 2>&1 & echo STARTED')

print()
print('============================================================')
print('  DEPLOYMENT DONE!')
print(f'  Dashboard : http://{vps_ip}:8600')
print('  Telegram  : Bot startup message coming!')
print()
print('  NEXT: Update Delta Exchange API whitelist')
print(f'  Remove: 157.49.185.100  Add: {vps_ip}')
print('  URL: https://www.delta.exchange/app/account/api-management')
print('============================================================')
"
pause
