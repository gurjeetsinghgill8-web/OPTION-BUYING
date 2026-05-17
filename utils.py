import sys
import requests
import db
from datetime import datetime

# Force UTF-8 output on Windows (fixes emoji UnicodeEncodeError)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def send_telegram_msg(message):
    token   = db.get_param('telegram_bot_token')
    chat_id = db.get_param('telegram_chat_id')
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        _safe_print(f"Telegram Error: {e}")

def log_terminal(message, typ="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {
        "START":  "[START]",
        "INFO":   "[INFO] ",
        "TRADE":  "[TRADE]",
        "ERROR":  "[ERROR]",
        "ALERT":  "[ALERT]",
        "WARN":   "[WARN] ",
        "DEBUG":  "[DEBUG]",
        "RESET":  "[RESET]",
    }
    prefix = icons.get(typ, "[INFO] ")
    msg = f"[{timestamp}] {prefix} {message}"
    _safe_print(msg)
    if typ in ["TRADE", "ALERT", "ERROR", "RESET"]:
        send_telegram_msg(f"BHARAT FUTURES ENGINE:\n{msg}")

def _safe_print(text):
    """Print that never crashes on Windows encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))
