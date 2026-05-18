"""
OB v2.0 Full Deploy — Guardian + Expiry Fix + OTM2 + Audit Log + Dashboard restart
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

LOCAL   = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING'
BOT_DIR = '/root/OPTION-BUYING'
VPS_IP  = '46.224.133.16'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username='root', password=vps_secrets['vps_password'], timeout=20)
print("[OK] Connected: " + VPS_IP)

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# [1] Kill bot + dashboard on 8503
print("\n[1] Killing old processes...")
all_pids = run("pgrep -f 'main.py'").split()
for pid in all_pids:
    pid = pid.strip()
    if not pid.isdigit(): continue
    cwd = run(f"readlink /proc/{pid}/cwd 2>/dev/null")
    if 'OPTION-BUYING' in cwd:
        run(f"kill -9 {pid}")
        print(f"   Bot killed: PID {pid}")
run("pkill -f 'streamlit.*8503' 2>/dev/null; echo done")
time.sleep(3)

# [2] Upload all updated files
print("\n[2] Uploading files...")
files = ['main.py', 'app.py', 'options_executor.py', 'secrets.txt']
with SCPClient(ssh.get_transport()) as scp:
    for f in files:
        fp = os.path.join(LOCAL, f)
        if os.path.exists(fp):
            scp.put(fp, BOT_DIR + '/' + f)
            print(f"   Uploaded: {f}")

# [3] Set correct DB values
print("\n[3] Setting DB defaults...")
out = run(
    f"cd {BOT_DIR} && python3 -c \""
    "import db; db.load_secrets(); "
    "db.set_param('trade_mode','LIVE'); "
    "db.set_param('distance_type','OTM2'); "
    "db.set_param('expiry_mode','1DTE'); "
    "db.set_param('algo_running','ON'); "
    "print('trade_mode:', db.get_param('trade_mode')); "
    "print('distance_type:', db.get_param('distance_type')); "
    "print('expiry_mode:', db.get_param('expiry_mode'))\""
)
for line in out.split('\n'):
    if ':' in line: print("   " + line)

# [4] Clear pycache + log
run(f"rm -rf {BOT_DIR}/__pycache__/")
run(f"echo '' > {BOT_DIR}/bot.log")
run(f"touch {BOT_DIR}/audit.log")
print("   Cleared pycache + log")

# [5] Start bot with python3 -u (unbuffered)
print("\n[4] Starting bot...")
run("echo '#!/bin/bash' > /tmp/start_ob.sh")
run(f"echo 'cd {BOT_DIR}' >> /tmp/start_ob.sh")
run("echo 'PYTHONUNBUFFERED=1 nohup python3 -u main.py > bot.log 2>&1 &' >> /tmp/start_ob.sh")
run("echo 'echo $!' >> /tmp/start_ob.sh")
run("chmod +x /tmp/start_ob.sh")
pid = run("bash /tmp/start_ob.sh")
print(f"   Bot PID: {pid}")

# [6] Start dashboard on 8503
print("\n[5] Starting dashboard on 8503...")
run(f"nohup python3 -m streamlit run {BOT_DIR}/app.py "
    f"--server.port 8503 --server.address 0.0.0.0 "
    f"--server.headless true --browser.gatherUsageStats false "
    f"> {BOT_DIR}/dash.log 2>&1 &")
time.sleep(20)

# [7] Verify
print("\n[6] Verification:")
print("   Port 8503:", run("ss -tlnp | grep 8503 | head -1"))
log = run(f"tail -15 {BOT_DIR}/bot.log", wait=10)
print("\n[7] bot.log:")
print("-" * 55)
print(log if log.strip() else "(empty — waiting for first candle)")
print("-" * 55)

ssh.close()
print("\nDone!")
print("Bot   : LIVE | OTM2 | 1DTE | Guardian ON")
print("Dashboard: http://157.49.182.222:8503")
