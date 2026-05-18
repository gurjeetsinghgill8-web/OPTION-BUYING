"""Check dashboard status and restart if needed."""
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
print("[OK] Connected")

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("\n[1] Streamlit processes:")
print(run("ps aux | grep streamlit | grep -v grep"))

print("\n[2] Port 8503 status:")
print(run("ss -tlnp | grep 8503 || echo 'PORT NOT LISTENING'"))

print("\n[3] Port 8600 status:")
print(run("ss -tlnp | grep 8600 || echo 'PORT NOT LISTENING'"))

# If 8503 not running, restart it
port_8503 = run("ss -tlnp | grep 8503")
if not port_8503:
    print("\n[4] Restarting dashboard on port 8503...")
    run("pkill -f 'streamlit.*8503' 2>/dev/null")
    time.sleep(2)
    run("echo '#!/bin/bash' > /tmp/start_dash.sh")
    run("echo 'cd /root/OPTION-BUYING' >> /tmp/start_dash.sh")
    run("echo 'nohup python3 -m streamlit run app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false > dash.log 2>&1 &' >> /tmp/start_dash.sh")
    run("chmod +x /tmp/start_dash.sh")
    run("bash /tmp/start_dash.sh")
    time.sleep(8)
    print("   Started! Checking...")
    print(run("ss -tlnp | grep 8503 || echo 'still not up'"))
else:
    print("\n[4] Dashboard IS running on 8503 — network/firewall issue?")
    print(run("ufw status | grep 8503 || iptables -L | grep 8503 || echo 'no firewall rule found'"))

ssh.close()
