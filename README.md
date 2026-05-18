# ⚡ BHARAT FUTURES ENGINE v1.0

**Completely NEW, ISOLATED project — No connection to old bot**

---

## 📁 Folder Structure

```
BHARAT-FUTURES-ENGINE/
├── secrets.txt          ← Your API keys (fill this first!)
├── db.py                ← Database layer (futures_engine.db)
├── utils.py             ← Telegram + terminal logging
├── futures_executor.py  ← Delta Exchange Futures API
├── main.py              ← Trading engine (Magic Line logic)
├── app.py               ← Streamlit Dashboard (port 8503)
├── requirements.txt     ← pip install -r requirements.txt
├── SETUP.bat            ← First time setup
├── RUN_DASHBOARD.bat    ← Open dashboard
└── RUN_BOT.bat          ← Start trading engine
```

---

## 🚀 Quick Start

### Step 1 — Fill secrets.txt
```
DELTA_API_KEY=your_new_key
DELTA_API_SECRET=your_new_secret
TELEGRAM_TOKEN=your_new_bot_token   ← Create via @BotFather
TELEGRAM_CHAT_ID=your_chat_id
TRADE_MODE=PAPER
```

### Step 2 — Install dependencies
Double-click `SETUP.bat`

### Step 3 — Run Dashboard
Double-click `RUN_DASHBOARD.bat` → opens at http://46.224.133.16:8503

### Step 4 — Run Bot
Double-click `RUN_BOT.bat` (in a separate window)

---

## 📊 Strategy: Magic Line (BTC Futures)

| Condition | Action |
|---|---|
| LTP > 6PM Anchor | BUY futures (Long) |
| LTP < 6PM Anchor | SELL futures (Short) |
| Signal Flip | Close old → Open new |
| SL Hit | Auto square off |

---

## ⚙️ Dashboard Controls (port 8503)
- **START / STOP ENGINE** — Control the bot
- **SQUARE OFF ALL** — Emergency close all positions
- **HARD RESET DB** — Clear stuck/zombie state
- **Manual Anchor Override** — Set your own price level
- **Trade Mode** — Switch PAPER ↔ LIVE
- **Timeframe** — 5m or 15m
- **SL %** — Stop loss percentage (default 2% for futures)
- **Telegram Test** — Send test message

---

## ⚠️ Key Differences from Old Bot
| Old Bot | New Bot |
|---|---|
| Option Selling (Calls & Puts) | BTC Perpetual Futures |
| Port 8501 | Port 8503 |
| trading_app.db | futures_engine.db |
| Old Telegram Bot | New Telegram Bot |
| Old API Keys | New API Keys |
| Folder: BHARAT ALGO-TRADING | Folder: BHARAT-FUTURES-ENGINE |

---

*Made by Bharat Algo | Gurjeet Singh Gill*
