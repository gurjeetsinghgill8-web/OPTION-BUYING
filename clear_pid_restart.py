"""
Clear PID lock file, then restart cleanly.
"""
import paramiko, sys, time
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

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Show what's blocking
print("\n[1] bot.pid contents:")
print(run("cat /root/OPTION-BUYING/bot.pid 2>/dev/null || echo '(no pid file)'"))

print("\n[2] All python processes:")
print(run("ps aux | grep python | grep -v grep"))

# Nuclear kill - by PID file + pkill + pgrep
print("\n[3] Nuclear kill...")
pid = run("cat /root/OPTION-BUYING/bot.pid 2>/dev/null")
if pid.strip().isdigit():
    run(f"kill -9 {pid.strip()} 2>/dev/null")
    print(f"   Killed PID from file: {pid.strip()}")
run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null")
run("pkill -9 -f 'options_engine' 2>/dev/null")
# Kill any python main.py not belonging to other bots
run("pgrep -f 'OPTION-BUYING.*main' | xargs kill -9 2>/dev/null")
time.sleep(3)

# Remove PID lock file
print("[4] Removing PID lock file...")
run("rm -f /root/OPTION-BUYING/bot.pid")
run("rm -rf /root/OPTION-BUYING/__pycache__/")
print("   Done!")

# Verify clean
out = run("ps aux | grep 'OPTION-BUYING' | grep -v grep")
print(f"[5] Remaining processes: {out if out else 'NONE - clean!'}")

# Clear log + fresh start
print("[6] Clear log + fresh start...")
run("echo '' > /root/OPTION-BUYING/bot.log")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")

print("   Waiting 18s for startup + Telegram message...")
time.sleep(18)

# Show fresh log
print("\n[7] FRESH bot.log:")
print("-" * 60)
log = run("cat /root/OPTION-BUYING/bot.log", wait=10)
print(log if log else "(empty - ALREADY RUNNING guard hit again)")
print("-" * 60)

ps = run("ps aux | grep 'OPTION-BUYING' | grep python | grep -v grep")
print(f"\n[8] Bot running: {'YES - ' + ps[:80] if ps else 'NO - check log above'}")

ssh.close()
print("\nDone! Dashboard: http://46.224.133.16:8503")
