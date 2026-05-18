"""
Kill by PORT (not by name) - the real way to stop socket-locked bot.
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

print("\n[1] All python main.py processes:")
out = run("pgrep -a -f 'python' | grep main")
print(out if out else "none")

print("\n[2] What's on port 47301 (socket lock port):")
out = run("ss -tlnp | grep 47301 || lsof -i :47301 -t 2>/dev/null || echo 'none'")
print(out)

# Kill by port
print("\n[3] Kill by port 47301...")
out = run("kill -9 $(lsof -i :47301 -t 2>/dev/null) 2>/dev/null; echo 'port kill done'")
print("   " + out)

# Kill all main.py (except BHARAT-FUTURES-ENGINE ones)
# Get PIDs of all main.py, then exclude the BHARAT-FUTURES-ENGINE one (PID 446302)
print("\n[4] All main.py PIDs:")
all_pids = run("pgrep -f 'main.py'")
print("   PIDs: " + all_pids)

bharat_pid = "446302"  # the known BHARAT-FUTURES-ENGINE pid
for pid in all_pids.split('\n'):
    pid = pid.strip()
    if pid.isdigit() and pid != bharat_pid:
        cwd = run(f"readlink /proc/{pid}/cwd 2>/dev/null || echo 'unknown'")
        print(f"   PID {pid} cwd: {cwd}")
        if 'OPTION-BUYING' in cwd or 'bharat' not in cwd.lower():
            run(f"kill -9 {pid} 2>/dev/null")
            print(f"   KILLED {pid}")

time.sleep(3)

# Verify port is free
out = run("lsof -i :47301 2>/dev/null || ss -tlnp | grep 47301 || echo 'PORT FREE'")
print(f"\n[5] Port 47301 status: {out}")

# Clean restart
print("\n[6] Clean restart...")
run("rm -rf /root/OPTION-BUYING/__pycache__/")
run("echo '' > /root/OPTION-BUYING/bot.log")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_ob.sh")
run("echo 'nohup python3 main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")

print("   Waiting 20s...")
time.sleep(20)

print("\n[7] FRESH log:")
print("-" * 60)
log = run("cat /root/OPTION-BUYING/bot.log", wait=10)
print(log if log else "(empty)")
print("-" * 60)

# Final port check
out = run("lsof -i :47301 2>/dev/null | head -3 || echo 'not found'")
print(f"\n[8] Port 47301 after start: {out}")

ssh.close()
print("\nDone! Dashboard: http://46.224.133.16:8503")
