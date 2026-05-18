"""
EMERGENCY: Clear stale option position from DB.
The position P-BTC-76600-190526 does NOT exist on Delta Exchange.
(Confirmed: exchange returned no_position_for_reduce_only)
This script clears the DB state so the engine can re-enter fresh.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import subprocess, sys as _sys

try:
    import paramiko
except ImportError:
    subprocess.check_call([_sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

VPS_IP   = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"
REMOTE_DIR = "/root/OPTION-BUYING"
REMOTE_SCRIPT = f"{REMOTE_DIR}/_clear_stale.py"

# Write the clear script to a temp file locally, then upload it
CLEAR_CODE = """\
import sys, os
sys.path.insert(0, "/root/OPTION-BUYING")
import db

print("=== CLEARING STALE OPTION POSITION ===")
print("Before clear:")
print("  trade_active:", db.get_param("option_trade_active"))
print("  symbol      :", db.get_param("active_option_symbol"))

trade_id = int(db.get_param("active_option_trade_id", "0") or "0")
entry_px = float(db.get_param("active_option_entry_px", "0") or "0")
if trade_id > 0:
    curr_px = float(db.get_param("option_current_px", "0") or "0")
    if curr_px <= 0:
        curr_px = entry_px
    pnl = (curr_px - entry_px) * int(db.get_param("active_option_qty","1") or "1")
    db.close_option_trade(trade_id, curr_px, round(pnl, 4), "POSITION_NOT_ON_EXCHANGE")
    print(f"  Closed trade_id={trade_id} | exit_px={curr_px:.2f} | pnl={pnl:+.2f}")

db.clear_option_position()

print("After clear:")
print("  trade_active:", db.get_param("option_trade_active"))
print("  symbol      :", db.get_param("active_option_symbol"))
print("=== DONE - Engine is now FLAT ===")
"""

print("Connecting to VPS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("Connected!")

# Write the clear script remotely via sftp
sftp = ssh.open_sftp()
with sftp.open(REMOTE_SCRIPT, 'w') as f:
    f.write(CLEAR_CODE)
sftp.close()
print("Uploaded _clear_stale.py")

# Execute it
stdin, stdout, stderr = ssh.exec_command(
    f"cd {REMOTE_DIR} && python3 _clear_stale.py 2>&1",
    timeout=30
)
output = stdout.read().decode("utf-8", errors="replace")
error  = stderr.read().decode("utf-8", errors="replace")

print(output)
if error:
    print("STDERR:", error[:300])

ssh.close()
print("Done.")
