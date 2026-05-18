"""Open port 8503 in VPS firewall (ufw/iptables)."""
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
print("[OK] Connected")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("\n[1] Current firewall status:")
print(run("ufw status 2>/dev/null | head -20 || echo 'ufw not active'"))

print("\n[2] Current iptables (port 8503):")
print(run("iptables -L INPUT -n | grep 8503 || echo 'no iptables rule for 8503'"))

print("\n[3] Opening port 8503...")
# Try ufw first
out1 = run("ufw allow 8503/tcp 2>/dev/null && echo 'UFW: 8503 opened' || echo 'UFW: not active'")
print("   UFW:", out1)

# Also open via iptables directly
out2 = run("iptables -I INPUT -p tcp --dport 8503 -j ACCEPT 2>/dev/null && echo 'iptables: 8503 opened' || echo 'iptables failed'")
print("   iptables:", out2)

print("\n[4] Verify all open ports:")
print(run("ss -tlnp | grep -E '8501|8502|8503|8600'"))

print("\n[5] Verify process on 8503:")
print(run("ss -tlnp | grep 8503"))

ssh.close()
print("\nDone! Try: http://46.224.133.16:8503")
