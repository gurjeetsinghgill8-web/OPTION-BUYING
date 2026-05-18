"""
OPTION-BUYING: Verify fix + restart using EXACT same pattern as lego0_restart.py
"""
import paramiko, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')
from scp import SCPClient

# --- Read secrets (same as all other lego scripts) ---
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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("[OK] Connected to VPS: " + VPS_IP)

# --- Exact same run() as lego0_restart.py ---
def run(cmd, wait=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    return out

# [1] Kill all old OPTION-BUYING processes
print("\n[1] All python processes on VPS:")
out = run("ps aux | grep python | grep -v grep")
print(out if out else "   (none)")

print("\n[2] Killing OPTION-BUYING processes...")
run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null; echo DONE")
time.sleep(3)
out = run("ps aux | grep 'OPTION-BUYING' | grep -v grep")
print("   Remaining: " + (out if out else "NONE - clean!"))

# [2b] Upload fixed file
print("\n[3] Uploading fixed options_executor.py to VPS...")
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'options_executor.py'), BOT_DIR + '/options_executor.py')
print("   Uploaded!")

# Confirm fix is present
out = run("grep -c 'suffix = distance_type' /root/OPTION-BUYING/options_executor.py")
print("   Fix lines found: " + out + " (should be 2)")

# Clear pycache
run("rm -rf /root/OPTION-BUYING/__pycache__/")
print("   pycache cleared")

# [3] Start using /tmp/startbot.sh — EXACT lego0 pattern
print("\n[4] Starting fresh bot (lego pattern)...")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py >> bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print("   Bot started, PID: " + pid)
time.sleep(12)

# [4] Final verification — exact lego0 pattern
print("\n[5] FINAL VERIFICATION:")
out = run("ps aux | grep python | grep -v grep")
if out:
    lines = [l for l in out.strip().split('\n') if 'main' in l or 'OPTION' in l or 'streamlit' in l]
    print("   Processes running: " + str(len(lines)))
    for l in lines:
        print("   -> " + l[:90])
else:
    print("   ERROR: No python processes found!")

# [5] Show log — exact lego0 pattern
print("\n[6] Bot startup log:")
print("-" * 55)
out = run("tail -25 " + BOT_DIR + "/bot.log", wait=15)
print(out)
print("-" * 55)

ssh.close()
print("\nLEGO COMPLETE")
print("Dashboard: http://46.224.133.16:8503")
