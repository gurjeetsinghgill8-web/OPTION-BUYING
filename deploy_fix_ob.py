"""
Upload fixed options_executor.py to VPS and restart OPTION-BUYING bot.
"""
import paramiko, sys, time, os
sys.stdout.reconfigure(encoding='utf-8')
from scp import SCPClient

secrets = {}
for line in open(r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

VPS_IP   = '46.224.133.16'
VPS_USER = 'root'
VPS_PASS = secrets.get('vps_password', '')
BOT_DIR  = '/root/OPTION-BUYING'
LOCAL    = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING'

print("=" * 55)
print("  OPTION-BUYING Fix Deploy + Restart")
print(f"  VPS: {VPS_USER}@{VPS_IP}")
print("=" * 55)

if not VPS_PASS:
    print("[ERROR] VPS_PASSWORD not found in secrets.txt")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("[OK] Connected to VPS")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    return out

# Step 1: Upload fixed files
print("\n[1] Uploading fixed options_executor.py...")
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'options_executor.py'),
            BOT_DIR + '/options_executor.py')
    # Also upload main.py in case there's an updated version
    scp.put(os.path.join(LOCAL, 'main.py'),
            BOT_DIR + '/main.py')
print("    Uploaded!")

# Step 2: Kill old bot
print("\n[2] Killing old OPTION-BUYING processes...")
out = run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null; sleep 2; echo KILLED")
print(f"    {out}")
time.sleep(3)

# Step 3: Check if anything remains
print("\n[3] Checking for survivors...")
out = run("ps aux | grep 'OPTION-BUYING' | grep -v grep")
if out:
    print(f"    Still running: {out[:100]}")
    # Force kill by PID
    pids = run("pgrep -f 'OPTION-BUYING'")
    for pid in pids.split('\n'):
        if pid.strip().isdigit():
            run(f"kill -9 {pid.strip()}")
            print(f"    Force killed PID {pid.strip()}")
    time.sleep(2)
else:
    print("    All clear!")

# Step 4: Write and run starter script (avoids SSH session issues)
print("\n[4] Starting fresh bot...")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run(f"echo 'cd {BOT_DIR}' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py >> bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"    Bot started! PID: {pid}")
time.sleep(8)

# Step 5: Verify running
print("\n[5] Verification:")
ps_out = run("ps aux | grep 'OPTION-BUYING' | grep -v grep")
if ps_out:
    for line in ps_out.split('\n'):
        print(f"    RUNNING: {line[:90]}")
else:
    # Check by process name
    ps_out2 = run(f"pgrep -fa main.py | grep -i option")
    if ps_out2:
        print(f"    RUNNING: {ps_out2[:90]}")
    else:
        print("    WARNING: No OPTION-BUYING process found!")

# Step 6: Show log
print("\n[6] Last 25 lines of bot.log:")
print("-" * 55)
log = run(f"tail -25 {BOT_DIR}/bot.log", wait=10)
print(log if log else "(log empty)")
print("-" * 55)

ssh.close()
print("\nDone! Dashboard: http://46.224.133.16:8503")
