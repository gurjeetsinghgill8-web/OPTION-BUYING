# -*- coding: utf-8 -*-
"""
EMERGENCY: Stop engine + report all open positions
"""
import paramiko

VPS_HOST = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)

def run(cmd, label=""):
    if label: print(f"\n[{label}]")
    _, o, e = ssh.exec_command(cmd)
    out = o.read().decode(errors="replace").strip()
    if out: print(out)
    return out

print("=" * 55)
print("  EMERGENCY STOP")
print("=" * 55)

# 1. Kill engine
run("pkill -9 -f 'python3 main.py' 2>/dev/null; echo 'Engine killed'", "KILLING ENGINE")
run("sleep 2 && ps aux | grep 'python3 main.py' | grep -v grep || echo 'Engine is DOWN'", "VERIFY STOPPED")

# 2. Show DB state
run("""cd /root/OPTION-BUYING && python3 -c "
import db
db.load_secrets()
print('option_trade_active =', db.get_param('option_trade_active','NO'))
print('active_option_side  =', db.get_param('active_option_side','NONE'))
print('active_option_symbol=', db.get_param('active_option_symbol','NONE'))
print('active_option_qty   =', db.get_param('active_option_qty','0'))
print('active_option_entry =', db.get_param('active_option_entry_px','0'))
print('algo_running        =', db.get_param('algo_running','OFF'))
" """, "DB STATE")

print("\n" + "=" * 55)
print("  ENGINE IS STOPPED")
print("  Check Delta Exchange manually for open positions")
print("=" * 55)

ssh.close()
