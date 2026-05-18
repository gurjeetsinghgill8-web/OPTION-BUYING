import sys,io,time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
import paramiko
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("46.224.133.16",port=22,username="root",password="U4CJs4HKbMMJ",timeout=15,allow_agent=False,look_for_keys=False)
def r(cmd,t=15):
    _,o,e=c.exec_command(cmd,timeout=t)
    out=o.read().decode('utf-8','replace').strip()
    err=e.read().decode('utf-8','replace').strip()
    print(f"OUT: {out}" if out else "OUT: (empty)")
    if err: print(f"ERR: {err[:300]}")
    return out

print("=== PORT CHECK ===")
r("ss -tlnp | grep -E '8501|8502|8503|8504|8505'")

print("\n=== STREAMLIT PROCESSES ===")
r("ps aux | grep streamlit | grep -v grep")

print("\n=== OPTION-BUYING DASH LOG ===")
r("tail -30 /root/OPTION-BUYING/dash.log 2>/dev/null || echo 'no dash.log'")

print("\n=== BOT LOG ===")
r("tail -20 /root/OPTION-BUYING/bot.log 2>/dev/null || echo 'no bot.log'")

print("\n=== FIREWALL CHECK ===")
r("ufw status | head -20 || iptables -L INPUT -n | head -20")

c.close()
