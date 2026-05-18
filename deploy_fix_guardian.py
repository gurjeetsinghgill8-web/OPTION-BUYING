# -*- coding: utf-8 -*-
"""
Deploy Guardian Fix to VPS
- Uploads fixed main.py
- Clears stale PUT position from DB
- Restarts engine
"""
import paramiko
import os, time, sys

VPS_HOST  = "46.224.133.16"
VPS_USER  = "root"
VPS_PASS  = "U4CJs4HKbMMJ"
VPS_DIR   = "/root/OPTION-BUYING"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

def ssh_run(client, cmd, label=""):
    print(f"  >> {label or cmd[:70]}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    if out:
        print(f"     {out[:300]}")
    if err and "warning" not in err.lower() and "deprecated" not in err.lower():
        print(f"     ERR: {err[:200]}")
    return out

print("=" * 55)
print("  GUARDIAN FIX + STALE PUT CLEAR + DEPLOY")
print("=" * 55)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("\n[1] Connecting to VPS...")
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    print("    Connected OK")

    # -- Upload main.py --
    print("\n[2] Uploading fixed main.py...")
    sftp = ssh.open_sftp()
    sftp.put(os.path.join(LOCAL_DIR, "main.py"), f"{VPS_DIR}/main.py")
    sftp.close()
    print("    main.py uploaded OK")

    # -- Clear stale PUT + check state --
    print("\n[3] Clearing stale PUT position from DB...")
    py_clear = (
        f"cd {VPS_DIR} && python3 -c \""
        "import db; "
        "db.load_secrets(); "
        "active = db.get_param('option_trade_active','NO'); "
        "side   = db.get_param('active_option_side','NONE'); "
        "sym    = db.get_param('active_option_symbol','NONE'); "
        "print('BEFORE: active=' + active + ' side=' + side + ' sym=' + sym); "
        "db.clear_option_position(); "
        "active2 = db.get_param('option_trade_active','NO'); "
        "print('AFTER:  active=' + active2); "
        "print('DB cleared - engine is now FLAT'); "
        "\""
    )
    ssh_run(ssh, py_clear, "Clear DB position")

    # -- Stop old engine process --
    print("\n[4] Stopping old engine process...")
    ssh_run(ssh,
        "pkill -f 'python3 main.py' 2>/dev/null || true; sleep 2; "
        "echo 'Old process stopped'",
        "Kill old engine")

    # -- Start fresh engine --
    print("\n[5] Starting fresh engine...")
    ssh_run(ssh,
        f"cd {VPS_DIR} && nohup python3 main.py >> /root/ob_engine.log 2>&1 & "
        "sleep 3 && echo 'Engine started, PID:' $(pgrep -f 'python3 main.py')",
        "Start engine")

    # -- Verify state --
    print("\n[6] Verifying final state...")
    py_verify = (
        f"cd {VPS_DIR} && python3 -c \""
        "import db; "
        "db.load_secrets(); "
        "print('option_trade_active = ' + db.get_param('option_trade_active','NO')); "
        "print('active_option_side  = ' + db.get_param('active_option_side','NONE')); "
        "print('algo_running        = ' + db.get_param('algo_running','OFF')); "
        "\""
    )
    ssh_run(ssh, py_verify, "Verify DB state")

    print("\n" + "=" * 55)
    print("  DONE!")
    print("  - Stale PUT cleared from DB")
    print("  - Guardian fix deployed (main.py)")
    print("  - Engine restarted fresh")
    print("  - Next candle will enter correct side")
    print("=" * 55)

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
