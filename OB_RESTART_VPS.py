"""
OPTION-BUYING Master Restart Script
- Sets LIVE mode
- Kills old instance (by CWD, not name)
- Restarts with python3 -u (unbuffered logs)
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

LOCAL  = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING'
VPS_IP = '46.224.133.16'
BOT_DIR = '/root/OPTION-BUYING'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username='root', password=vps_secrets['vps_password'], timeout=20)
print("[OK] Connected to VPS: " + VPS_IP)

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# [1] Find and kill OPTION-BUYING process by CWD
print("\n[1] Finding OPTION-BUYING process by working directory...")
all_pids = run("pgrep -f 'main.py'").split()
killed = []
for pid in all_pids:
    pid = pid.strip()
    if not pid.isdigit():
        continue
    cwd = run(f"readlink /proc/{pid}/cwd 2>/dev/null")
    if 'OPTION-BUYING' in cwd:
        run(f"kill -9 {pid}")
        killed.append(pid)
        print(f"   Killed PID {pid} (cwd={cwd})")
if not killed:
    print("   No OPTION-BUYING process found")
time.sleep(3)

# [2] Set LIVE mode + OTM1 in DB
print("\n[2] Setting DB params...")
out = run(
    "cd /root/OPTION-BUYING && python3 -c \""
    "import db; db.load_secrets(); "
    "db.set_param('trade_mode','LIVE'); "
    "db.set_param('distance_type','OTM1'); "
    "db.set_param('algo_running','ON'); "
    "print('trade_mode:', db.get_param('trade_mode')); "
    "print('distance_type:', db.get_param('distance_type'))\""
)
for line in out.split('\n'):
    if 'trade_mode' in line or 'distance_type' in line:
        print("   " + line)

# [3] Upload latest files
print("\n[3] Uploading latest files...")
with SCPClient(ssh.get_transport()) as scp:
    for f in ['main.py', 'options_executor.py', 'secrets.txt']:
        fpath = os.path.join(LOCAL, f)
        if os.path.exists(fpath):
            scp.put(fpath, BOT_DIR + '/' + f)
            print(f"   Uploaded: {f}")

# [4] Clear pycache + log, restart with -u flag
print("\n[4] Restarting with python3 -u (unbuffered)...")
run("rm -rf /root/OPTION-BUYING/__pycache__/")
run("echo '' > /root/OPTION-BUYING/bot.log")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'PYTHONUNBUFFERED=1 nohup python3 -u main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")
print("   Waiting 20s for startup + Telegram...")
time.sleep(20)

# [5] Show log
print("\n[5] bot.log:")
print("-" * 60)
log = run("cat /root/OPTION-BUYING/bot.log", wait=10)
print(log if log.strip() else "(empty - check Telegram for startup msg)")
print("-" * 60)

# [6] DB confirmation
out = run(
    "cd /root/OPTION-BUYING && python3 -c \""
    "import db; db.load_secrets(); "
    "print('Mode:', db.get_param('trade_mode')); "
    "print('Distance:', db.get_param('distance_type')); "
    "print('Running:', db.get_param('algo_running'))\"  2>/dev/null | grep -v secrets"
)
print("\n[6] Final DB state:")
for line in out.split('\n'):
    if ':' in line:
        print("   " + line)

ssh.close()
print("\nDone! Dashboard: http://46.224.133.16:8503")
