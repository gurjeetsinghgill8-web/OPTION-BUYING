"""
DEPLOY — OB Engine Fix
  Step 1: Clear stale DB position (Brick 1)
  Step 2: Upload fixed options_executor.py (Brick 2)
  Step 3: Restart engine on VPS
"""
import sys, io, os, time, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import paramiko
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

VPS_IP     = "46.224.133.16"
VPS_USER   = "root"
VPS_PASS   = "U4CJs4HKbMMJ"
REMOTE_DIR = "/root/OPTION-BUYING"
LOCAL_DIR  = r"c:\Users\pc\Desktop\gurjas ai\OPTION BUYING"

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
    return ssh

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

print("=" * 60)
print("  OB ENGINE DEPLOY — BRICK 1 + BRICK 2 + RESTART")
print("=" * 60)

# ── STEP 1: Clear stale DB position ──────────────────────────
print("\n[STEP 1] Connecting to VPS...")
ssh = connect()
print("         Connected!")

CLEAR_CODE = """\
import sys
sys.path.insert(0, "/root/OPTION-BUYING")
import db

print("--- BEFORE ---")
print("trade_active :", db.get_param("option_trade_active"))
print("symbol       :", db.get_param("active_option_symbol"))
print("product_id   :", db.get_param("active_option_product_id"))

trade_id = int(db.get_param("active_option_trade_id", "0") or "0")
entry_px = float(db.get_param("active_option_entry_px", "0") or "0")
curr_px  = float(db.get_param("option_current_px", "0") or "0")
qty      = int(db.get_param("active_option_qty", "1") or "1")

if curr_px <= 0:
    curr_px = entry_px
pnl = (curr_px - entry_px) * qty

if trade_id > 0:
    db.close_option_trade(trade_id, curr_px, round(pnl, 4), "POSITION_NOT_ON_EXCHANGE")
    print(f"Closed trade_id={trade_id} | exit_px={curr_px:.2f} | pnl={pnl:+.2f}")

db.clear_option_position()

print("--- AFTER ---")
print("trade_active :", db.get_param("option_trade_active"))
print("symbol       :", db.get_param("active_option_symbol"))
print("ENGINE IS NOW FLAT")
"""

sftp = ssh.open_sftp()
with sftp.open(f"{REMOTE_DIR}/_clear_stale.py", 'w') as f:
    f.write(CLEAR_CODE)

print("[STEP 1] Running DB clear...")
out, err = run(ssh, f"cd {REMOTE_DIR} && python3 _clear_stale.py 2>&1", timeout=20)
print(out)
if err and "Error" in err:
    print("STDERR:", err[:200])

# ── STEP 2: Upload fixed options_executor.py ─────────────────
print("\n[STEP 2] Uploading fixed options_executor.py...")
sftp.put(
    os.path.join(LOCAL_DIR, "options_executor.py"),
    f"{REMOTE_DIR}/options_executor.py"
)
print("         Uploaded!")

# ── STEP 3: Stop old engine process ──────────────────────────
print("\n[STEP 3] Stopping old engine...")
out, _ = run(ssh, "pkill -f 'python3 main.py' 2>&1 || echo 'no process found'", timeout=10)
print("        ", out.strip())
time.sleep(3)

# Verify it's stopped
out, _ = run(ssh, "pgrep -f 'python3 main.py' | wc -l", timeout=5)
proc_count = out.strip()
print(f"         Remaining engine processes: {proc_count}")

# ── STEP 4: Start fresh engine ────────────────────────────────
print("\n[STEP 4] Starting fresh engine...")
out, err = run(ssh,
    f"cd {REMOTE_DIR} && nohup python3 main.py >> logs/engine.log 2>&1 &"
    f" sleep 4 && pgrep -f 'python3 main.py' | head -3",
    timeout=15
)
print("         New PIDs:", out.strip())

# ── STEP 5: Verify DB state is clean ─────────────────────────
print("\n[STEP 5] Final DB verification...")
VERIFY_CODE = """\
import sys
sys.path.insert(0, "/root/OPTION-BUYING")
import db
print("trade_active :", db.get_param("option_trade_active"))
print("symbol       :", db.get_param("active_option_symbol"))
print("trade_mode   :", db.get_param("trade_mode"))
print("algo_running :", db.get_param("algo_running"))
"""
with sftp.open(f"{REMOTE_DIR}/_verify.py", 'w') as f:
    f.write(VERIFY_CODE)
out, _ = run(ssh, f"cd {REMOTE_DIR} && python3 _verify.py 2>&1", timeout=10)
print(out)

sftp.close()
ssh.close()

print("=" * 60)
print("  DEPLOY COMPLETE")
print("  Engine is FLAT. Next candle = fresh CALL entry.")
print("  Watch Telegram for: LIVE OPTION BOUGHT")
print("=" * 60)
