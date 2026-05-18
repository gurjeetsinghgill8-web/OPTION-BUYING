"""
Check fresh bot status - kill, clear log, restart, show fresh log
"""
import paramiko, sys, time, os
sys.stdout.reconfigure(encoding='utf-8')
from scp import SCPClient

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

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Kill all, clear log, restart fresh
print("[1] Kill all OPTION-BUYING...")
run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null; sleep 2; echo done")
time.sleep(3)

# Confirm secrets on VPS
print("\n[2] VPS secrets check:")
out = run("cat /root/OPTION-BUYING/secrets.txt | grep -v PASSWORD | grep -v '#'")
print(out)

# Clear old log so we get FRESH output
print("\n[3] Clearing old bot.log...")
run("echo '' > /root/OPTION-BUYING/bot.log")

# Fresh start
print("[4] Starting fresh...")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   PID: {pid}")

# Wait for bot to initialize and send startup Telegram msg
print("   Waiting 15s for bot to initialize...")
time.sleep(15)

# Show FRESH log
print("\n[5] FRESH bot.log:")
print("-" * 55)
log = run("cat /root/OPTION-BUYING/bot.log", wait=10)
print(log if log else "(empty - bot may have crashed)")
print("-" * 55)

# Check if process is still alive
ps = run("ps aux | grep 'OPTION-BUYING' | grep python | grep -v grep")
print(f"\n[6] Process alive: {ps[:80] if ps else 'NO - crashed!'}")

ssh.close()
