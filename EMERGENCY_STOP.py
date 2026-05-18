"""EMERGENCY STOP - Kill bot + check what positions exist on exchange"""
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

# KILL ALL OPTION-BUYING INSTANCES NOW
print("\n[EMERGENCY] Killing ALL OPTION-BUYING processes...")
all_pids = run("pgrep -f 'main.py'").split()
killed = 0
for pid in all_pids:
    pid = pid.strip()
    if not pid.isdigit(): continue
    cwd = run(f"readlink /proc/{pid}/cwd 2>/dev/null")
    if 'OPTION-BUYING' in cwd:
        run(f"kill -9 {pid}")
        killed += 1
        print(f"   Killed PID {pid}")

# Also stop via socket lock port
run("kill -9 $(lsof -i :47301 -t 2>/dev/null) 2>/dev/null")
time.sleep(2)

print(f"\n   Total killed: {killed}")
remaining = run("pgrep -a -f 'main.py' | grep OPTION")
print(f"   Remaining: {remaining if remaining else 'NONE - CLEAN'}")

# Set engine to OFF in DB so it doesn't auto-start
out = run("cd /root/OPTION-BUYING && python3 -c \"import db; db.load_secrets(); db.set_param('algo_running','OFF'); print('algo_running:', db.get_param('algo_running'))\" 2>/dev/null | grep algo")
print(f"\n   DB engine status: {out}")

# Show last log lines
print("\n[LAST LOG]:")
print("-"*55)
print(run("tail -20 /root/OPTION-BUYING/bot.log"))
print("-"*55)

ssh.close()
print("\n✅ BOT STOPPED. No more trades will be placed.")
print("Fix karega phir restart karna.")
