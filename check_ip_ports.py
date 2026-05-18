"""Check actual public IP of VPS + status of all dashboards"""
import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

vps_secrets = {}
for line in open(r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        vps_secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=vps_secrets['vps_password'], timeout=20)
print("[OK] Connected via SSH to 46.224.133.16")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("\n[1] ALL network interfaces:")
print(run("ip addr show | grep 'inet ' | grep -v '127.0.0'"))

print("\n[2] Public IP (what internet sees):")
print(run("curl -s ifconfig.me 2>/dev/null || curl -s api.ipify.org 2>/dev/null"))

print("\n[3] All LISTENING ports:")
print(run("ss -tlnp | grep LISTEN | grep -E '850[0-9]|860[0-9]'"))

print("\n[4] All streamlit processes:")
print(run("ps aux | grep streamlit | grep -v grep"))

print("\n[5] NSL dashboard 8502 specifically:")
print(run("ss -tlnp | grep 8502"))
print(run("ps aux | grep 8502 | grep -v grep"))

ssh.close()
