"""Open all dashboard ports via iptables on VPS"""
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

# Open all dashboard ports
ports = [8501, 8502, 8503, 8600]
for port in ports:
    run(f"iptables -I INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null")
    run(f"iptables -I OUTPUT -p tcp --sport {port} -j ACCEPT 2>/dev/null")
    print(f"   Port {port}: OPEN")

# Also allow established connections
run("iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null")

# Show full INPUT chain
print("\n[IPTABLES INPUT]:")
print(run("iptables -L INPUT -n --line-numbers | head -20"))

# Test connectivity from inside
print("\nAll ports listening:")
print(run("ss -tlnp | grep -E '850[0-9]|860[0-9]'"))

ssh.close()
print("\nServer-side firewall: ALL PORTS OPEN")
print("If still not accessible → Hostasia panel mein ports allow karo")
print("URL: http://46.224.133.16:8503")
