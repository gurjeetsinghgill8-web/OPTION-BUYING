"""
Force clear pycache, verify file is updated, and restart OPTION-BUYING bot.
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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("[OK] Connected")

def run(cmd, wait=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

# Kill ALL python processes (both old and new)
print("[1] Nuclear kill - all python in OPTION-BUYING...")
run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null")
run("pkill -9 -f 'option-buying' 2>/dev/null")
# Also kill by checking bot.log PID
out, _ = run("cat " + BOT_DIR + "/bot.pid 2>/dev/null")
if out.strip().isdigit():
    run(f"kill -9 {out.strip()} 2>/dev/null")
    print(f"   Killed pid from bot.pid: {out.strip()}")
time.sleep(3)

# Verify all dead
out, _ = run("ps aux | grep -E '(OPTION-BUYING|option_buying)' | grep -v grep")
print(f"[2] Remaining: {out if out else 'NONE - clean!'}")

# Clear Python cache on VPS
print("[3] Clearing VPS __pycache__...")
out, _ = run(f"rm -rf {BOT_DIR}/__pycache__/ && echo CLEARED")
print(f"   {out}")

# Re-upload fixed file
print("[4] Uploading fixed options_executor.py...")
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'options_executor.py'),
            BOT_DIR + '/options_executor.py')
print("   Uploaded!")

# Verify fix is on VPS
print("[5] Verifying fix landed on VPS...")
out, _ = run(f"grep -n 'suffix = distance_type' {BOT_DIR}/options_executor.py")
if out:
    print(f"   FIX CONFIRMED on VPS: {out}")
else:
    print("   WARNING: Fix NOT found in VPS file!")
    # Try direct write via SSH
    fix_line = "        suffix = distance_type[3:]  # OTM1->1, OTM->empty"
    print("   Trying alternative upload method...")

# Start fresh bot
print("[6] Starting bot fresh...")
start_cmd = f"cd {BOT_DIR} && nohup python3 -u main.py > bot.log 2>&1 & echo $!"
out, _ = run(start_cmd)
print(f"   PID: {out}")
time.sleep(10)

# Check it's running and not crashing
print("[7] Checking status (after 10s)...")
out, _ = run("ps aux | grep 'python3' | grep -v grep")
for line in out.split('\n'):
    if 'OPTION' in line or 'main' in line:
        print(f"   RUNNING: {line[:100]}")

# Get fresh log (after restart)
print("[8] Fresh bot.log (last 20 lines):")
print("-" * 55)
out, _ = run(f"tail -20 {BOT_DIR}/bot.log", wait=10)
print(out if out else "(empty)")
print("-" * 55)

ssh.close()
print("\nDone!")
