"""Final verification - show live log."""
import paramiko, sys, time
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

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Port check - this is definitive
port = run("lsof -i :47301 -t 2>/dev/null || ss -tlnp | grep 47301 | grep -oP 'pid=\\K[0-9]+'")
print(f"Port 47301 held by PID: {port}")

# Process
ps = run("ps aux | grep '468200' | grep -v grep")
print(f"PID 468200: {ps[:80] if ps else 'NOT FOUND'}")

# Log (wait for it to fill up)
print("\nbот.log (30 lines):")
print("-" * 60)
print(run("cat /root/OPTION-BUYING/bot.log", wait=10))
print("-" * 60)

# DB settings verification
print("\nDB settings:")
out = run("cd /root/OPTION-BUYING && python3 -c \"import db; db.load_secrets(); print('trade_mode:', db.get_param('trade_mode')); print('distance_type:', db.get_param('distance_type')); print('algo_running:', db.get_param('algo_running'))\" 2>/dev/null | grep -v secrets")
print(out)

ssh.close()
