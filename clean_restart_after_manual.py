# -*- coding: utf-8 -*-
"""
CLEAN RESTART after manual position close
- Clears DB state
- Uploads fixed main.py (Guardian reverted - no more auto-clear)
- Restarts engine fresh
Run this AFTER you have closed all positions on Delta Exchange manually.
"""
import paramiko, os, time

VPS_HOST = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"
VPS_DIR  = "/root/OPTION-BUYING"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def run(cmd, label=""):
    if label: print(f"\n[{label}]")
    _, o, _ = ssh.exec_command(cmd)
    out = o.read().decode(errors="replace").strip()
    if out: print(" ", out[:400])
    return out

print("=" * 55)
print("  CLEAN RESTART (post manual close)")
print("=" * 55)

ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
print("Connected OK")

# 1. Make sure engine is stopped
run("pkill -9 -f 'python3 main.py' 2>/dev/null; sleep 1; echo done", "STOP ENGINE")

# 2. Upload fixed main.py
print("\n[UPLOAD main.py]")
sftp = ssh.open_sftp()
sftp.put(os.path.join(LOCAL_DIR, "main.py"), f"{VPS_DIR}/main.py")
sftp.close()
print("  main.py uploaded OK")

# 3. Clear DB position state
run(f"""cd {VPS_DIR} && python3 -c "
import db
db.load_secrets()
db.clear_option_position()
db.set_param('algo_running', 'ON')
db.set_param('force_closed_today', 'NO')
print('DB cleared - engine is FLAT and ready')
print('algo_running =', db.get_param('algo_running','OFF'))
print('option_trade_active =', db.get_param('option_trade_active','NO'))
" """, "CLEAR DB")

# 4. Start engine
run(f"cd {VPS_DIR} && nohup python3 main.py >> /root/ob_engine.log 2>&1 &"
    " sleep 3 && pgrep -f 'python3 main.py' && echo Engine started",
    "START ENGINE")

print("\n" + "=" * 55)
print("  DONE - Engine restarted cleanly")
print("  Guardian fix: REVERTED (no more auto-clear)")
print("  DB: FLAT (no position)")
print("  Engine will enter next signal on next candle")
print("=" * 55)

ssh.close()
