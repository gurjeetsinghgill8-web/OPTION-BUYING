"""Upload only app.py to VPS + restart dashboard only (NOT the bot)"""
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
print("[OK] Connected — uploading app.py only (NOT restarting bot)")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Upload app.py only
with SCPClient(ssh.get_transport()) as scp:
    scp.put(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\app.py',
            '/root/OPTION-BUYING/app.py')
    print("   Uploaded: app.py")

# Restart ONLY the dashboard (not the bot)
run("pkill -f 'streamlit.*8503' 2>/dev/null; sleep 1")
run("cd /root/OPTION-BUYING && nohup python3 -m streamlit run app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false > /root/OPTION-BUYING/dash.log 2>&1 &")
import time; time.sleep(3)

port = run("ss -tlnp | grep 8503")
print(f"   Dashboard 8503: {'LIVE ✅' if '8503' in port else 'FAILED ❌'}")

# Confirm bot still running
bot = run("pgrep -a -f 'main.py' | grep OPTION")
print(f"   Bot process: {bot if bot else 'NOT RUNNING ⚠️'}")

# Show current DB state
db_check = run("""cd /root/OPTION-BUYING && python3 -c "
import db; db.init_db()
print('option_active:', db.get_param('option_trade_active'))
print('symbol:', db.get_param('active_option_symbol'))
print('entry_px:', db.get_param('active_option_entry_px'))
print('distance_type:', db.get_param('distance_type'))
print('expiry_mode:', db.get_param('expiry_mode'))
" """)
print(f"\n[DB]:\n{db_check}")

ssh.close()
print("\nDone — bot was NOT restarted. Dashboard reloaded only.")
print("Dashboard: http://46.224.133.16:8503")
