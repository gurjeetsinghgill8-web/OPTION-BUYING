"""Check and fix DB state + reset OTM2/1DTE"""
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

# Check current DB state
out = run("""cd /root/OPTION-BUYING && python3 -c "
import db
db.init_db()
keys = ['option_trade_active','active_option_symbol','active_option_entry_px',
        'active_option_qty','active_option_side','distance_type','expiry_mode',
        'trade_mode','algo_running','last_processed_candle_ts']
for k in keys:
    v = db.get_param(k, 'NOT_SET')
    print(f'  {k} = {v}')
" """)
print("[DB STATE]:")
print(out)

# Fix: Restore OTM2 + 1DTE + ensure position shows correctly
fix = run("""cd /root/OPTION-BUYING && python3 -c "
import db
db.init_db()
db.set_param('distance_type', 'OTM2')
db.set_param('expiry_mode', '1DTE')
db.set_param('algo_running', 'ON')
db.set_param('trade_mode', 'LIVE')
print('FIXED: OTM2 + 1DTE + LIVE + ON')
print('distance_type:', db.get_param('distance_type'))
print('expiry_mode:', db.get_param('expiry_mode'))
print('option_trade_active:', db.get_param('option_trade_active'))
" """)
print("\n[FIX RESULT]:")
print(fix)

ssh.close()
