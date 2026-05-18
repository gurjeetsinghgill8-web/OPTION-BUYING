"""
Set LIVE mode in DB, kill socket-locked old process, restart clean.
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

# [1] Set LIVE mode in DB via python one-liner on VPS
print("\n[1] Setting trade_mode=LIVE in VPS DB...")
out = run(
    "cd /root/OPTION-BUYING && python3 -c \""
    "import db; db.load_secrets(); db.set_param('trade_mode','LIVE'); "
    "print('trade_mode =', db.get_param('trade_mode','?'))\""
)
print("   " + out)

# [2] Also set distance_type to OTM1 (not bare OTM)
print("\n[2] Setting distance_type=OTM1...")
out = run(
    "cd /root/OPTION-BUYING && python3 -c \""
    "import db; db.load_secrets(); db.set_param('distance_type','OTM1'); "
    "print('distance_type =', db.get_param('distance_type','?'))\""
)
print("   " + out)

# [3] Kill ALL python on port 47301 (socket lock)
print("\n[3] Finding and killing socket-locked process on port 47301...")
out = run("fuser 47301/tcp 2>/dev/null || echo 'none'")
print("   Port 47301 held by PID: " + out)
if out and out != 'none':
    for pid in out.split():
        if pid.strip().isdigit():
            run(f"kill -9 {pid.strip()} 2>/dev/null")
            print(f"   Killed PID: {pid.strip()}")

run("pkill -9 -f 'OPTION-BUYING' 2>/dev/null")
time.sleep(3)

# Confirm port is free
out = run("fuser 47301/tcp 2>/dev/null || echo 'FREE'")
print("   Port 47301 now: " + out)

# [4] Clear log + restart
print("\n[4] Clearing log + fresh start...")
run("rm -rf /root/OPTION-BUYING/__pycache__/")
run("echo '' > /root/OPTION-BUYING/bot.log")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")

print("   Waiting 18s for startup...")
time.sleep(18)

# [5] Fresh log
print("\n[5] FRESH bot.log:")
print("-" * 60)
log = run("cat /root/OPTION-BUYING/bot.log", wait=10)
print(log if log else "(empty)")
print("-" * 60)

ps = run("fuser 47301/tcp 2>/dev/null || echo 'none'")
print(f"\n[6] Port 47301 bound by: {ps} ({'RUNNING OK' if ps != 'none' else 'NOT RUNNING'})")

ssh.close()
print("\nDone! LIVE mode set. Dashboard: http://46.224.133.16:8503")
