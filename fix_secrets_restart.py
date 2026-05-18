"""
Upload secrets.txt + restart bot + send Telegram test message
"""
import paramiko, sys, time, os, requests
sys.stdout.reconfigure(encoding='utf-8')
from scp import SCPClient

# Read VPS password from BHARAT-FUTURES-ENGINE secrets
vps_secrets = {}
for line in open(r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        vps_secrets[k.strip().lower()] = v.strip()

# Read OPTION-BUYING secrets (the new ones)
ob_secrets = {}
for line in open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        ob_secrets[k.strip().lower()] = v.strip()

VPS_IP   = '46.224.133.16'
VPS_USER = 'root'
VPS_PASS = vps_secrets.get('vps_password', '')
BOT_DIR  = '/root/OPTION-BUYING'
LOCAL    = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING'

print("=" * 55)
print("  OPTION-BUYING: Secrets Fix + Telegram Test")
print("=" * 55)

# --- Step 1: Test Telegram FIRST (from laptop) ---
TOKEN   = ob_secrets.get('telegram_bot_token', '')
CHAT_ID = ob_secrets.get('telegram_chat_id', '')
print(f"\n[1] Testing Telegram from LAPTOP...")
print(f"   Token: {TOKEN[:20]}...")
print(f"   ChatID: {CHAT_ID}")
try:
    url  = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": "✅ OPTION BUYING BOT — Test message\nSecrets update ho gayi!\nBot restart ho raha hai..."
    }, timeout=10)
    if resp.status_code == 200:
        print("   TELEGRAM OK! Message sent.")
    else:
        print(f"   TELEGRAM ERROR: {resp.text[:200]}")
except Exception as e:
    print(f"   TELEGRAM EXCEPTION: {e}")

# --- Step 2: Upload secrets to VPS ---
print(f"\n[2] Connecting to VPS {VPS_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("   Connected!")

def run(cmd, wait=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("\n[3] Uploading secrets.txt to VPS...")
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'secrets.txt'), BOT_DIR + '/secrets.txt')
print("   Uploaded!")

# Verify keys on VPS
out = run(f"grep -c 'FILL_YOUR' {BOT_DIR}/secrets.txt")
if out == '0':
    print("   No placeholders — secrets are REAL!")
else:
    print(f"   WARNING: {out} placeholder lines still present!")

# --- Step 3: Kill + restart ---
print("\n[4] Killing old bot...")
run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null; sleep 1; echo done")
run("rm -rf /root/OPTION-BUYING/__pycache__/")
time.sleep(3)

print("[5] Starting fresh bot (lego pattern)...")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py >> bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   PID: {pid}")
time.sleep(12)

# --- Step 4: Show log ---
print("\n[6] Bot log (last 20 lines):")
print("-" * 55)
log = run("tail -20 /root/OPTION-BUYING/bot.log", wait=15)
print(log)
print("-" * 55)

ssh.close()
print("\nDone! Dashboard: http://46.224.133.16:8503")
