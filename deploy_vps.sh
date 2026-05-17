#!/bin/bash
# ============================================================
#  BHARAT FUTURES ENGINE — VPS DEPLOY SCRIPT
#  Run this on your HostIndia VPS via SSH
# ============================================================

echo "============================================"
echo "  BHARAT FUTURES ENGINE — VPS SETUP"
echo "============================================"

# 1. Install Python dependencies
echo "[1/5] Installing dependencies..."
pip3 install streamlit requests pandas numpy --quiet

# 2. Create folder
echo "[2/5] Creating engine folder..."
mkdir -p ~/bharat-futures-engine
cd ~/bharat-futures-engine

# 3. Kill any existing bot
echo "[3/5] Stopping old bot if running..."
pkill -f "main.py" 2>/dev/null || true
pkill -f "streamlit" 2>/dev/null || true
sleep 1

# 4. Start Dashboard in background (port 8600)
echo "[4/5] Starting Dashboard on port 8600..."
nohup python3 -m streamlit run app.py \
    --server.port 8600 \
    --server.headless true \
    --browser.gatherUsageStats false \
    > dashboard.log 2>&1 &
DASH_PID=$!
echo "Dashboard PID: $DASH_PID"

sleep 2

# 5. Start Trading Bot in background
echo "[5/5] Starting Trading Bot..."
nohup python3 main.py > bot.log 2>&1 &
BOT_PID=$!
echo "Bot PID: $BOT_PID"

echo ""
echo "============================================"
echo "  DEPLOYMENT COMPLETE!"
echo "============================================"
echo "  Dashboard : http://$(curl -s ifconfig.me):8600"
echo "  Bot Log   : tail -f ~/bharat-futures-engine/bot.log"
echo "  Dash Log  : tail -f ~/bharat-futures-engine/dashboard.log"
echo ""
echo "  Stop Bot  : pkill -f main.py"
echo "  Stop Dash : pkill -f streamlit"
echo "============================================"

# Save PIDs
echo $DASH_PID > dashboard.pid
echo $BOT_PID > bot.pid
