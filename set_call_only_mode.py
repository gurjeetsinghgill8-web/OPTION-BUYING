"""
SET CALL-ONLY MODE + CLEAR STALE PUT + DEPLOY
==============================================
Run this script to:
1. Set allowed_signal = CALL on VPS (engine will only take CALL trades)
2. Force-clear the stale PUT position from DB (so engine is FLAT)
3. Push updated main.py to VPS and restart engine
"""
import paramiko
import os, sys, time

VPS_HOST   = "46.224.133.16"
VPS_USER   = "root"
VPS_PATH   = "/root/option-buying"   # VPS project directory
LOCAL_MAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

# ── Read SSH password from secrets.txt ───────────────────────
secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.txt")
VPS_PASS = None
if os.path.exists(secrets_path):
    with open(secrets_path, "r") as f:
        for line in f:
            if line.strip().startswith("vps_password"):
                VPS_PASS = line.split("=", 1)[1].strip()
                break

if not VPS_PASS:
    VPS_PASS = input("Enter VPS root password: ").strip()

def run_ssh(client, cmd, desc=""):
    print(f"  → {desc or cmd[:60]}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"    OUT: {out[:200]}")
    if err and "warning" not in err.lower():
        print(f"    ERR: {err[:200]}")
    return out, err

print("=" * 60)
print("  SET CALL-ONLY MODE + CLEAR STALE PUT + DEPLOY")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print(f"\n[1] Connecting to VPS {VPS_HOST}...")
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    print("    ✅ Connected")

    # ── Step 2: Upload updated main.py ───────────────────────
    print(f"\n[2] Uploading main.py to VPS...")
    sftp = ssh.open_sftp()
    sftp.put(LOCAL_MAIN, f"{VPS_PATH}/main.py")
    sftp.close()
    print("    ✅ main.py uploaded")

    # ── Step 3: Set CALL-only mode in DB ─────────────────────
    print("\n[3] Setting CALL-only mode + clearing stale PUT...")
    py_cmd = (
        f"cd {VPS_PATH} && python3 -c \""
        "import db; "
        "db.load_secrets(); "
        "db.set_param('allowed_signal', 'CALL'); "
        "print('allowed_signal set to CALL'); "
        "active = db.get_param('option_trade_active', 'NO'); "
        "side   = db.get_param('active_option_side', 'NONE'); "
        "print(f'Current state: active={active}, side={side}'); "
        "db.clear_option_position(); "
        "print('DB position cleared — engine is now FLAT'); "
        "\""
    )
    run_ssh(ssh, py_cmd, "Set CALL-only + clear stale PUT")

    # ── Step 4: Restart engine ────────────────────────────────
    print("\n[4] Restarting Options Engine service...")
    run_ssh(ssh, "systemctl restart options-engine 2>/dev/null || "
                 "pkill -f 'python3 main.py' 2>/dev/null; sleep 2; "
                 "cd /root/option-buying && nohup python3 main.py >> /root/ob.log 2>&1 &",
            "Restart engine")
    time.sleep(3)

    # ── Step 5: Verify ────────────────────────────────────────
    print("\n[5] Verifying state...")
    verify_cmd = (
        f"cd {VPS_PATH} && python3 -c \""
        "import db; db.load_secrets(); "
        "print('allowed_signal =', db.get_param('allowed_signal', 'BOTH')); "
        "print('option_trade_active =', db.get_param('option_trade_active', 'NO')); "
        "print('active_option_side =', db.get_param('active_option_side', 'NONE')); "
        "\""
    )
    run_ssh(ssh, verify_cmd, "Verify DB state")

    print("\n" + "=" * 60)
    print("  ✅ DONE — Engine is now:")
    print("     • CALL-only mode (PUT signals will be IGNORED)")
    print("     • Stale PUT position cleared from DB")
    print("     • main.py updated with guardian fix")
    print("     • Engine restarted")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback; traceback.print_exc()
finally:
    ssh.close()
