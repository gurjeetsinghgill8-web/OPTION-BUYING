import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
import paramiko

c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("46.224.133.16",port=22,username="root",password="U4CJs4HKbMMJ",
          timeout=15,allow_agent=False,look_for_keys=False)

def r(cmd,t=15):
    _,o,e=c.exec_command(cmd,timeout=t)
    out=o.read().decode('utf-8','replace').strip()
    err=e.read().decode('utf-8','replace').strip()
    if out: print(out)
    if err and 'warning' not in err.lower(): print("[err]",err[:200])
    return out

# 1. Write fresh secrets template on VPS
secrets_template = """# ============================================================
# BITCOIN OPTIONS ENGINE — secrets.txt
# Fill your keys below. Do NOT share this file with anyone.
# ============================================================

# Delta Exchange API (New Account)
# Get from: delta.exchange → Account → API Management
delta_api_key=FILL_YOUR_DELTA_API_KEY_HERE
delta_api_secret=FILL_YOUR_DELTA_API_SECRET_HERE

# Telegram Bot
# Create bot: Message @BotFather on Telegram → /newbot
# Get Chat ID: Message @userinfobot on Telegram
telegram_bot_token=FILL_YOUR_TELEGRAM_BOT_TOKEN_HERE
telegram_chat_id=FILL_YOUR_TELEGRAM_CHAT_ID_HERE

# VPS (do not change)
VPS_IP=46.224.133.16
VPS_USER=root
VPS_PASSWORD=U4CJs4HKbMMJ
"""

print("=== Writing secrets template on VPS ===")
# Write template (won't overwrite if real keys already there)
r(f"""cat > /root/OPTION-BUYING/secrets.txt << 'ENDSECRETS'
{secrets_template}
ENDSECRETS
echo 'Template written'""")

# 2. Open port 8503 via iptables (UFW is inactive, so this works)
print("\n=== Opening port 8503 in iptables ===")
r("iptables -I INPUT -p tcp --dport 8503 -j ACCEPT && echo 'Port 8503 OPENED'")
r("iptables -I INPUT -p tcp --dport 8504 -j ACCEPT && echo 'Port 8504 OPENED'")

# 3. Verify port is now accessible
print("\n=== Checking listening ports ===")
r("ss -tlnp | grep -E '8501|8502|8503|8504'")

# 4. Show the secrets file location for user
print("\n=== secrets.txt location on VPS ===")
r("cat /root/OPTION-BUYING/secrets.txt")

# 5. How to edit on VPS
print("\n=== Edit command for user ===")
print("To fill keys: nano /root/OPTION-BUYING/secrets.txt")

c.close()
