"""
Upload and run diagnostic script on VPS via SSH (uses paramiko).
"""
import subprocess
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Install paramiko if not available
try:
    import paramiko
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

import time

VPS_IP   = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"
REMOTE_DIR = "/root/OPTION-BUYING"

print("Connecting to VPS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("Connected!")

# Upload the diagnostic script
sftp = ssh.open_sftp()
sftp.put(r"c:\Users\pc\Desktop\gurjas ai\OPTION BUYING\diag_api.py",
         f"{REMOTE_DIR}/diag_api.py")
sftp.close()
print("Uploaded diag_api.py")

# Run it
stdin, stdout, stderr = ssh.exec_command(
    f"cd {REMOTE_DIR} && python3 diag_api.py 2>&1",
    timeout=60
)
output = stdout.read().decode()
error  = stderr.read().decode()

print("\n" + "=" * 60)
print("OUTPUT FROM VPS:")
print("=" * 60)
print(output)
if error:
    print("STDERR:")
    print(error[:500])

ssh.close()
print("SSH closed.")
