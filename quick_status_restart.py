# -*- coding: utf-8 -*-
"""Quick check and restart if engine not running"""
import paramiko, os

VPS_HOST = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"
VPS_DIR  = "/root/OPTION-BUYING"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)

def run(cmd):
    _, o, _ = ssh.exec_command(cmd, timeout=10)
    return o.read().decode(errors="replace").strip()

# Check if running
pid = run("pgrep -f 'python3 main.py' | head -1")
print("Engine PID:", pid if pid else "NOT RUNNING")

if not pid:
    print("Starting engine...")
    run(f"cd {VPS_DIR} && nohup python3 main.py >> /root/ob_engine.log 2>&1 &")
    import time; time.sleep(3)
    pid = run("pgrep -f 'python3 main.py' | head -1")
    print("New PID:", pid if pid else "FAILED TO START")

# Check DB state
state = run(f"""cd {VPS_DIR} && python3 -c "
import db; db.load_secrets()
print('running =', db.get_param('algo_running','OFF'))
print('active  =', db.get_param('option_trade_active','NO'))
print('side    =', db.get_param('active_option_side','NONE'))
print('symbol  =', db.get_param('active_option_symbol','NONE'))
" """)
print(state)

# Show last 10 log lines
logs = run("tail -15 /root/ob_engine.log 2>/dev/null || echo 'no log yet'")
print("\nLast log lines:")
print(logs)

ssh.close()
