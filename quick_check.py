"""Quick check - is bot alive? Show log."""
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

print("[1] All python processes:")
print(run("pgrep -a -f main.py"))

print("\n[2] bot.log content:")
print(run("cat /root/OPTION-BUYING/bot.log 2>&1 | head -50"))

print("\n[3] Run bot directly (capture error):")
out = run("cd /root/OPTION-BUYING && timeout 5 python3 main.py 2>&1 | head -20")
print(out)

ssh.close()
