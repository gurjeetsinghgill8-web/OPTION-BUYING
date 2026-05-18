"""
BHARAT OPTION BUYING — REPAIR & REDEPLOY
==========================================
1. Kills ALL python bots on VPS (including old BHARAT PULSE / Magic Line)
2. Uploads latest clean files (SuperTrend BUY only — no SELL PUT)
3. Clears DB zombie state
4. Restarts bot + dashboard clean
5. Verifies everything is running
==========================================
Run: python REPAIR_AND_DEPLOY.py
"""
import paramiko, sys, time, os
sys.stdout.reconfigure(encoding='utf-8')
from scp import SCPClient

# ─── Load VPS credentials ──────────────────────────────────
secrets_file = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\secrets.txt'
vps_secrets = {}
try:
    for line in open(secrets_file, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            vps_secrets[k.strip().lower()] = v.strip()
except FileNotFoundError:
    print(f"[ERROR] secrets.txt not found at: {secrets_file}")
    sys.exit(1)

VPS_IP      = '46.224.133.16'
VPS_USER    = 'root'
VPS_PASS    = vps_secrets.get('vps_password', '')
LOCAL_DIR   = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING'
BOT_DIR     = '/root/OPTION-BUYING'
DASH_PORT   = 8503

if not VPS_PASS:
    print("[ERROR] vps_password not found in secrets.txt")
    sys.exit(1)

print("=" * 60)
print("  BHARAT OPTION BUYING — REPAIR & REDEPLOY")
print("=" * 60)

# ─── Connect ───────────────────────────────────────────────
print(f"\n[1] Connecting to VPS {VPS_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print(f"    ✅ Connected!")

def run(cmd, wait=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out

# ─── STEP 1: Kill ALL Python processes on VPS ──────────────
print("\n[2] Killing ALL old bot processes (including BHARAT PULSE)...")

# Kill anything running main.py
all_main_pids = run("pgrep -f 'main.py' 2>/dev/null").split()
for pid in all_main_pids:
    if pid.strip().isdigit():
        run(f"kill -9 {pid} 2>/dev/null")
        print(f"    Killed main.py PID: {pid}")

# Kill any streamlit on port 8503
run(f"pkill -f 'streamlit.*{DASH_PORT}' 2>/dev/null; true")
run(f"fuser -k {DASH_PORT}/tcp 2>/dev/null; true")

# Kill any BHARAT PULSE / old engine scripts
for pattern in ['bharat_pulse', 'magic_line', 'anchor', 'OPTION-BUYING/app.py']:
    run(f"pkill -f '{pattern}' 2>/dev/null; true")

time.sleep(3)

# Verify all killed
remaining = run("pgrep -f 'main.py' 2>/dev/null")
if remaining:
    print(f"    ⚠️ Some PIDs still running: {remaining} — force killing...")
    run("pkill -9 -f 'main.py' 2>/dev/null; true")
    time.sleep(2)
else:
    print("    ✅ All old processes killed.")

# ─── STEP 2: Clear pycache + logs ──────────────────────────
print("\n[3] Cleaning VPS directory...")
run(f"rm -rf {BOT_DIR}/__pycache__/")
run(f"echo '' > {BOT_DIR}/bot.log")
run(f"touch {BOT_DIR}/audit.log")
print("    ✅ Cleaned.")

# ─── STEP 3: Upload latest clean files ─────────────────────
print("\n[4] Uploading latest files...")
files_to_upload = [
    'main.py',
    'app.py',
    'options_executor.py',
    'db.py',
    'utils.py',
    'secrets.txt',
]
with SCPClient(ssh.get_transport()) as scp:
    for fname in files_to_upload:
        local_path = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(local_path):
            scp.put(local_path, f"{BOT_DIR}/{fname}")
            print(f"    ✅ Uploaded: {fname}")
        else:
            print(f"    ⚠️ Skipped (not found): {fname}")

# ─── STEP 4: Reset DB to clean state ───────────────────────
print("\n[5] Resetting DB to clean state...")
db_reset_cmd = (
    f"cd {BOT_DIR} && python3 -c \""
    "import db; db.init_db(); db.load_secrets(); "
    "db.set_param('option_trade_active','NO'); "
    "db.set_param('active_option_symbol','NONE'); "
    "db.set_param('active_option_side','NONE'); "
    "db.set_param('active_option_qty','0'); "
    "db.set_param('active_option_entry_px','0'); "
    "db.set_param('active_option_trade_id','0'); "
    "db.set_param('force_closed_today','NO'); "
    "db.set_param('algo_running','ON'); "
    "db.set_param('trade_mode','LIVE'); "
    "db.set_param('distance_type','OTM2'); "
    "db.set_param('expiry_mode','1DTE'); "
    "db.set_param('trade_size','1'); "
    "print('DB RESET OK'); "
    "print('trade_mode:', db.get_param('trade_mode')); "
    "print('algo_running:', db.get_param('algo_running')); "
    "print('option_trade_active:', db.get_param('option_trade_active'))\""
)
out = run(db_reset_cmd, wait=30)
for line in out.split('\n'):
    if line.strip():
        print(f"    {line}")

# ─── STEP 5: Start bot ─────────────────────────────────────
print("\n[6] Starting Option Buying bot (SuperTrend engine)...")
start_bot = (
    f"cd {BOT_DIR} && "
    f"nohup python3 -u main.py > bot.log 2>&1 & echo $!"
)
bot_pid = run(start_bot)
print(f"    ✅ Bot started. PID: {bot_pid}")

time.sleep(4)

# ─── STEP 6: Start dashboard ───────────────────────────────
print(f"\n[7] Starting dashboard on port {DASH_PORT}...")
start_dash = (
    f"nohup python3 -m streamlit run {BOT_DIR}/app.py "
    f"--server.port {DASH_PORT} "
    f"--server.address 0.0.0.0 "
    f"--server.headless true "
    f"--browser.gatherUsageStats false "
    f"> {BOT_DIR}/dash.log 2>&1 &"
)
run(start_dash)
time.sleep(15)

# ─── STEP 7: Verify ────────────────────────────────────────
print("\n[8] Verification...")

# Check bot process
bot_running = run("pgrep -f 'OPTION-BUYING/main.py' 2>/dev/null")
print(f"    Bot process : {'✅ RUNNING (PID: ' + bot_running + ')' if bot_running else '❌ NOT FOUND'}")

# Check dashboard port
port_check = run(f"ss -tlnp | grep :{DASH_PORT}")
print(f"    Dashboard   : {'✅ Port ' + str(DASH_PORT) + ' OPEN' if port_check else '❌ Port not open'}")

# Show last bot log
print(f"\n[9] Last 20 lines of bot.log:")
print("-" * 60)
log = run(f"tail -20 {BOT_DIR}/bot.log", wait=10)
print(log if log.strip() else "(empty — waiting for first engine cycle)")
print("-" * 60)

ssh.close()

print("\n" + "=" * 60)
print("  REPAIR COMPLETE")
print("=" * 60)
print(f"  Strategy  : SuperTrend 15m — BUY CALL / BUY PUT only")
print(f"  Mode      : LIVE | OTM2 | 1DTE | 1 Lot")
print(f"  Dashboard : http://{VPS_IP}:{DASH_PORT}")
print(f"  Engine    : 24x7 — NO force-close — NO SELL PUT")
print("=" * 60)
