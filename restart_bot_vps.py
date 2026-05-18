"""
OPTION-BUYING Bot — VPS Restart Script
Kills old process and starts fresh.
"""
import paramiko, time, os, sys

# Read secrets from BHARAT-FUTURES-ENGINE (has VPS creds)
secrets = {}
secrets_path = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'
for line in open(secrets_path):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

VPS_IP   = '46.224.133.16'
VPS_USER = 'root'
VPS_PASS = secrets.get('vps_password', '')
BOT_DIR  = '/root/OPTION-BUYING'

print("=" * 55)
print("  OPTION-BUYING Bot — VPS Restart")
print(f"  Target: {VPS_USER}@{VPS_IP}")
print("=" * 55)

if not VPS_PASS:
    print("[ERROR] VPS_PASSWORD missing in secrets.txt!")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("[OK] Connected to VPS!")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

# Step 1: Check what's running
print("\n[1] Current processes on VPS:")
out, _ = run("ps aux | grep main.py | grep -v grep")
print(out if out else "   (none running)")

# Step 2: Kill old OPTION-BUYING process
print("\n[2] Killing old OPTION-BUYING bot...")
out, _ = run("pkill -f 'OPTION-BUYING/main' 2>/dev/null; echo DONE")
print("   Kill signal:", out)
time.sleep(2)

# Step 3: Start fresh
print("\n[3] Starting fresh bot...")
run(f"echo '#!/bin/bash' > /tmp/start_ob.sh")
run(f"echo 'cd {BOT_DIR}' >> /tmp/start_ob.sh")
run(f"echo 'nohup python3 main.py >> bot.log 2>&1 &' >> /tmp/start_ob.sh")
run(f"echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid, _ = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")
time.sleep(5)

# Step 4: Verify
print("\n[4] Verification:")
out, _ = run("ps aux | grep main.py | grep -v grep")
if out:
    print("   ✅ BOT IS RUNNING:")
    for line in out.split('\n'):
        print("      " + line[:90])
else:
    print("   ❌ Bot not running! Checking log...")

# Step 5: Show log
print("\n[5] Last 15 lines of bot.log:")
print("-" * 55)
out, _ = run(f"tail -15 {BOT_DIR}/bot.log", wait=10)
print(out)
print("-" * 55)

ssh.close()
print("\n✅ DONE — Dashboard: http://46.224.133.16:8503")
