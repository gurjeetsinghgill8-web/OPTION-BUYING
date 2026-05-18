"""
BITCOIN OPTIONS ENGINE — DASHBOARD
LEGO Block 4 of 4 — app.py
Sky-Blue theme + Black text (as specified)
"""
import streamlit as st
import datetime, time
import db, options_executor as oe
from utils import send_telegram_msg

st.set_page_config(page_title="⚡ BTC Options Engine", page_icon="₿", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.stApp { background: #e8f4f8 !important; }
p,span,div,label,h1,h2,h3,li { color: #0a1628 !important; }
.stSelectbox label,.stNumberInput label,.stSlider label,
.stTextInput label,.stCheckbox label { color: #0a1628 !important; font-weight:600 !important; }
.stTextInput input,.stNumberInput input {
    background:#ffffff !important; color:#0a1628 !important;
    border:2px solid #5ba3c9 !important; border-radius:8px !important; }
.stSelectbox>div>div {
    background:#ffffff !important; color:#0a1628 !important;
    border:2px solid #5ba3c9 !important; border-radius:8px !important; }
[data-baseweb="select"] * { background:#ffffff !important; color:#0a1628 !important; }
.stButton>button {
    background:linear-gradient(135deg,#1565C0,#1976D2) !important;
    color:#ffffff !important; border:none !important; border-radius:8px !important;
    font-weight:700 !important; padding:10px !important; width:100% !important; }
.stButton>button:hover { background:linear-gradient(135deg,#1976D2,#42A5F5) !important; transform:translateY(-1px) !important; }
hr { border-color:#b3d4e8 !important; }
.mcard { background:#ffffff; border:2px solid #5ba3c9; border-radius:14px;
         padding:18px 14px; text-align:center; margin-bottom:8px; box-shadow:0 2px 8px rgba(91,163,201,0.15); }
.mcard .lbl { font-size:10px; color:#5ba3c9; text-transform:uppercase; letter-spacing:2px; margin-bottom:6px; font-weight:700; }
.mcard .val { font-size:26px; font-weight:900; color:#0a1628; }
.mcard .sub { font-size:11px; color:#5ba3c9; margin-top:4px; }
.badge { display:inline-block; padding:5px 16px; border-radius:20px; font-size:12px; font-weight:700; }
.b-on   { background:#1565C0; color:#fff; }
.b-off  { background:#b71c1c; color:#fff; }
.b-live { background:#2e7d32; color:#fff; }
.b-paper{ background:#e65100; color:#fff; }
.b-call { background:#1565C0; color:#fff; }
.b-put  { background:#ad1457; color:#fff; }
.b-flat { background:#78909c; color:#fff; }
.shdr { font-size:11px; color:#1565C0; text-transform:uppercase; letter-spacing:3px;
        font-weight:700; margin:16px 0 8px 0; border-left:3px solid #1565C0; padding-left:10px; }
.ibox { background:#dbeafe; border:1px solid #5ba3c9; border-radius:8px; padding:12px;
        color:#1565C0; font-size:13px; text-align:center; margin:6px 0; }
.sbox { background:#dcfce7; border:1px solid #4caf50; border-radius:8px; padding:12px;
        color:#2e7d32; font-size:13px; text-align:center; margin:6px 0; }
.wbox { background:#fff3e0; border:1px solid #ff9800; border-radius:8px; padding:12px;
        color:#e65100; font-size:13px; text-align:center; margin:6px 0; }
.abox { background:#fce4ec; border:1px solid #e91e63; border-radius:8px; padding:12px;
        color:#ad1457; font-size:13px; text-align:center; margin:6px 0; }
.pcard { background:#ffffff; border:2px solid #1565C0; border-radius:14px; padding:16px;
         margin:8px 0; box-shadow:0 2px 10px rgba(21,101,192,0.15); }
.ttbl { width:100%; border-collapse:collapse; }
.ttbl th { background:#dbeafe; color:#1565C0; font-size:10px; text-transform:uppercase;
           letter-spacing:1px; padding:10px; text-align:left; border-bottom:2px solid #5ba3c9; }
.ttbl td { color:#0a1628; font-size:12px; padding:9px 10px; border-bottom:1px solid #e0f0f8; }
.pp { color:#2e7d32; font-weight:700; }
.pn { color:#b71c1c; font-weight:700; }
</style>
""", unsafe_allow_html=True)

db.init_db()

# ── HEADER ────────────────────────────────────────────────
hc1, hc2 = st.columns([3,1])
with hc1:
    st.markdown("""
    <div style='padding:8px 0 10px 0'>
      <div style='font-size:28px;font-weight:900;color:#1565C0;letter-spacing:-0.5px;'>
        ₿ BITCOIN OPTIONS ENGINE
      </div>
      <div style='color:#5ba3c9;font-size:12px;margin-top:2px;letter-spacing:3px;'>
        SUPERTREND · 15M CANDLE · CALL &amp; PUT BUYING · v1.0
      </div>
    </div>""", unsafe_allow_html=True)
with hc2:
    now = datetime.datetime.now()
    st.markdown(f"""
    <div style='text-align:right;padding-top:12px'>
      <div style='color:#1565C0;font-size:22px;font-weight:700;'>{now.strftime('%H:%M:%S')}</div>
      <div style='color:#5ba3c9;font-size:12px;'>{now.strftime('%d %b %Y')}</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── LIVE DATA ─────────────────────────────────────────────
algo_on      = db.get_param("algo_running",        "OFF")
trade_mode   = db.get_param("trade_mode",          "PAPER")
opt_active   = db.get_param("option_trade_active", "NO")
opt_side     = db.get_param("active_option_side",  "NONE")
opt_symbol   = db.get_param("active_option_symbol","NONE")
opt_strike   = db.get_param("active_option_strike","0")
opt_expiry   = db.get_param("active_option_expiry","NONE")
opt_entry    = float(db.get_param("active_option_entry_px","0") or "0")
opt_curr     = float(db.get_param("option_current_px","0") or "0")
opt_target   = float(db.get_param("option_target_px","0") or "0")
opt_pct      = float(db.get_param("option_pct_gain","0") or "0")
opt_dist     = db.get_param("active_option_distance","NONE")
close_15m    = float(db.get_param("current_15m_close","0") or "0")
st_val       = float(db.get_param("st_value","0") or "0")
st_dir       = db.get_param("st_direction","?")
last_signal  = db.get_param("last_signal","?")
timeframe    = db.get_param("timeframe","15m")
st_period    = db.get_param("st_period","10")
st_mult      = db.get_param("st_multiplier","1.0")
expiry_mode  = db.get_param("expiry_mode","NEAREST_WEEKLY")
distance_sel = db.get_param("distance_type","OTM1")
pnl_1d, cnt_1d, wr_1d, _ = db.get_option_stats(1)
is_up        = (st_dir == "UP")

# ── TOP METRICS ───────────────────────────────────────────
m1,m2,m3,m4,m5 = st.columns(5)

def mc(lbl, val, sub, color="#0a1628"):
    return f"""<div class='mcard'>
      <div class='lbl'>{lbl}</div>
      <div class='val' style='color:{color}'>{val}</div>
      <div class='sub'>{sub}</div></div>"""

with m1:
    lbl15 = "15m Closed Candle" if close_15m > 0 else "Waiting..."
    st.markdown(mc("BTC 15m Close", f"${close_15m:,.0f}" if close_15m>0 else "--", lbl15, "#0a1628"), unsafe_allow_html=True)
with m2:
    vc = "#1565C0" if is_up else "#ad1457"
    bc = "#dbeafe" if is_up else "#fce4ec"
    bc2 = "#5ba3c9" if is_up else "#e91e63"
    ar = "▲ BULLISH" if is_up else "▼ BEARISH"
    st.markdown(f"""<div style='background:{bc};border:2px solid {bc2};border-radius:14px;padding:18px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
      <div class='lbl'>SuperTrend</div>
      <div class='val' style='color:{vc};font-size:26px;font-weight:900;'>${st_val:,.0f}</div>
      <div style='color:{vc};font-size:12px;font-weight:700;margin-top:4px;'>{ar}</div>
    </div>""", unsafe_allow_html=True)
with m3:
    sc = "#1565C0" if last_signal=="CALL" else ("#ad1457" if last_signal=="PUT" else "#78909c")
    st.markdown(mc("Signal", last_signal, f"TF:{timeframe} P={st_period} M={st_mult}", sc), unsafe_allow_html=True)
with m4:
    if opt_active=="YES" and opt_entry>0:
        gain_color = "#2e7d32" if opt_pct>=0 else "#b71c1c"
        st.markdown(mc("Premium Gain", f"{opt_pct:+.1f}%", f"Entry:{opt_entry:.2f} → Now:{opt_curr:.2f}", gain_color), unsafe_allow_html=True)
    else:
        st.markdown(mc("Premium Gain", "--", "No position", "#78909c"), unsafe_allow_html=True)
with m5:
    pc = "#2e7d32" if pnl_1d>=0 else "#b71c1c"
    st.markdown(mc("Today PnL", f"${pnl_1d:+.2f}", f"{cnt_1d} trades · WR:{wr_1d:.0f}%", pc), unsafe_allow_html=True)

st.divider()

# ── STATUS BADGES ─────────────────────────────────────────
sb1,sb2,sb3,sb4 = st.columns(4)
with sb1:
    bc = "b-on" if algo_on=="ON" else "b-off"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>ENGINE {'ON ▶' if algo_on=='ON' else 'OFF ■'}</span></div>", unsafe_allow_html=True)
with sb2:
    bc = "b-live" if trade_mode=="LIVE" else "b-paper"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>{trade_mode} MODE</span></div>", unsafe_allow_html=True)
with sb3:
    if opt_active=="YES":
        bc = "b-call" if opt_side=="CALL" else "b-put"
        lb = f"{opt_side} {opt_dist}"
    else:
        bc,lb = "b-flat","FLAT"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>{lb}</span></div>", unsafe_allow_html=True)
with sb4:
    if opt_active=="YES" and opt_target>0 and opt_curr>0:
        pct_to_target = min((opt_curr/opt_target)*100, 100)
        bar_color = "#2e7d32" if opt_pct>=50 else ("#ff9800" if opt_pct>=20 else "#1565C0")
        st.markdown(f"""<div style='text-align:center;'>
          <div style='font-size:11px;color:#5ba3c9;font-weight:700;'>2x TARGET PROGRESS</div>
          <div style='background:#e0f0f8;border-radius:8px;height:12px;margin-top:4px;overflow:hidden;'>
            <div style='background:{bar_color};height:100%;width:{pct_to_target:.0f}%;border-radius:8px;'></div>
          </div>
          <div style='font-size:11px;color:#0a1628;margin-top:2px;'>{opt_curr:.2f} / {opt_target:.2f}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;color:#5ba3c9;font-size:12px;'>No active position</div>", unsafe_allow_html=True)

st.divider()

# ── ACTIVE POSITION CARD ──────────────────────────────────
if opt_active == "YES":
    gain_emoji = "🟢" if opt_pct >= 0 else "🔴"
    side_color = "#1565C0" if opt_side=="CALL" else "#ad1457"
    st.markdown(f"""<div class='pcard'>
      <div style='font-size:14px;font-weight:700;color:{side_color};margin-bottom:10px;'>
        {gain_emoji} ACTIVE POSITION — {opt_side} ({opt_dist})
      </div>
      <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:10px;'>
        <div><div style='font-size:9px;color:#5ba3c9;text-transform:uppercase;'>Symbol</div><div style='font-weight:700;font-size:13px;color:#0a1628;'>{opt_symbol}</div></div>
        <div><div style='font-size:9px;color:#5ba3c9;text-transform:uppercase;'>Strike</div><div style='font-weight:700;font-size:13px;'>${float(opt_strike or 0):,.0f}</div></div>
        <div><div style='font-size:9px;color:#5ba3c9;text-transform:uppercase;'>Entry Premium</div><div style='font-weight:700;font-size:13px;'>{opt_entry:.4f}</div></div>
        <div><div style='font-size:9px;color:#5ba3c9;text-transform:uppercase;'>Current Premium</div><div style='font-weight:700;font-size:13px;color:{side_color};'>{opt_curr:.4f}</div></div>
        <div><div style='font-size:9px;color:#5ba3c9;text-transform:uppercase;'>2x Target</div><div style='font-weight:700;font-size:13px;color:#2e7d32;'>{opt_target:.4f}</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── LEFT / RIGHT PANELS ───────────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown("<div class='shdr'>🎮 Engine Control</div>", unsafe_allow_html=True)
    b1,b2 = st.columns(2)
    with b1:
        if st.button("▶ START ENGINE", key="btn_start"):
            db.set_param("algo_running","ON")
            send_telegram_msg("▶ OPTIONS ENGINE STARTED from Dashboard")
            st.success("Engine started!"); st.rerun()
    with b2:
        if st.button("■ STOP ENGINE", key="btn_stop"):
            db.set_param("algo_running","OFF")
            send_telegram_msg("■ OPTIONS ENGINE STOPPED from Dashboard")
            st.warning("Engine stopped."); st.rerun()

    st.markdown("<div class='shdr'>🚨 Emergency</div>", unsafe_allow_html=True)
    if st.button("🔴 SQUARE OFF ALL OPTIONS", key="btn_sq"):
        oe.close_option(reason="MANUAL")
        send_telegram_msg("🔴 MANUAL SQUARE OFF from Dashboard")
        st.error("Square off executed!"); st.rerun()

    st.divider()
    st.markdown("<div class='shdr'>🔄 System Reset</div>", unsafe_allow_html=True)
    st.markdown("<div class='wbox'>⚠️ Use only when engine is stuck</div>", unsafe_allow_html=True)
    b3,b4 = st.columns(2)
    with b3:
        if st.button("🔄 HARD RESET", key="btn_reset"):
            db.hard_reset_db()
            send_telegram_msg("🔄 HARD RESET executed")
            st.success("Reset done!"); st.rerun()
    with b4:
        if st.button("🧹 CLEAR POSITION", key="btn_clr"):
            db.clear_option_position()
            st.success("Position cleared."); st.rerun()

    st.divider()
    st.markdown("<div class='shdr'>🔑 API Keys</div>", unsafe_allow_html=True)
    if st.button("📂 LOAD FROM secrets.txt", key="btn_sec"):
        if db.load_secrets():
            st.success("Keys loaded!"); st.rerun()
        else:
            st.error("secrets.txt not found!")
    if st.button("📱 SEND TEST TELEGRAM", key="btn_tg"):
        tok = db.get_param("telegram_bot_token","")
        cid = db.get_param("telegram_chat_id","")
        if not tok or not cid:
            st.error("Load API keys first!")
        else:
            send_telegram_msg(f"✅ OPTIONS ENGINE TEST\nTime:{now.strftime('%H:%M')}\n15m Close:${close_15m:,.0f}\nST:{st_val:,.0f} ({st_dir})\nSignal:{last_signal}")
            st.success("Test sent! Check Telegram.")

    with st.expander("➕ Enter Keys Manually"):
        nk = st.text_input("Delta API Key",    value=db.get_param("delta_api_key",""),    type="password", key="k1")
        ns = st.text_input("Delta API Secret", value=db.get_param("delta_api_secret",""), type="password", key="k2")
        nt = st.text_input("Telegram Token",   value=db.get_param("telegram_bot_token",""),type="password",key="k3")
        nc = st.text_input("Telegram Chat ID", value=db.get_param("telegram_chat_id",""),               key="k4")
        if st.button("💾 SAVE KEYS", key="btn_keys"):
            if nk: db.set_param("delta_api_key", nk)
            if ns: db.set_param("delta_api_secret", ns)
            if nt: db.set_param("telegram_bot_token", nt)
            if nc: db.set_param("telegram_chat_id", nc)
            st.success("Keys saved!")

with right:
    st.markdown("<div class='shdr'>📊 SuperTrend Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='ibox'>⚡ Signal = 15m CLOSED candle close — zero repaint</div>", unsafe_allow_html=True)

    r1,r2 = st.columns(2)
    with r1:
        tf_opts = ["15m","5m","1h","30m","1m"]
        tf_sel  = st.selectbox("Candle Timeframe", tf_opts,
                               index=tf_opts.index(timeframe) if timeframe in tf_opts else 0, key="tf")
        per_sel = st.number_input("ST Period", 2, 50, int(st_period or 10), 1, key="per")
    with r2:
        mul_sel = st.number_input("ST Multiplier", 0.1, 10.0, float(st_mult or 1.0), 0.1, key="mul", format="%.1f")
        mode_sel = st.selectbox("Trade Mode", ["PAPER","LIVE"],
                                index=0 if trade_mode=="PAPER" else 1, key="mode")

    st.divider()
    st.markdown("<div class='shdr'>🎯 Strike & Expiry Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='ibox'>OTM1=nearest OTM · OTM2=2nd OTM · ATM=at money · ITM1=1st ITM etc.</div>", unsafe_allow_html=True)

    s1,s2 = st.columns(2)
    with s1:
        DISTANCE_OPTS = ["OTM4","OTM3","OTM2","OTM1","ATM","ITM1","ITM2","ITM3","ITM4"]
        dist_sel = st.selectbox("Strike Distance", DISTANCE_OPTS,
                                index=DISTANCE_OPTS.index(distance_sel) if distance_sel in DISTANCE_OPTS else 3,
                                key="dist")
    with s2:
        EXPIRY_OPTS = {
            "0DTE (Today)":       "0DTE",
            "1DTE (Tomorrow)":    "1DTE",
            "2DTE":               "2DTE",
            "3DTE":               "3DTE",
            "Nearest Weekly":     "NEAREST_WEEKLY",
            "Nearer Monthly":     "NEARER_MONTHLY",
            "This Monthly":       "THIS_MONTHLY",
            "Next Monthly":       "NEXT_MONTHLY",
        }
        exp_labels = list(EXPIRY_OPTS.keys())
        exp_values = list(EXPIRY_OPTS.values())
        cur_exp_idx = exp_values.index(expiry_mode) if expiry_mode in exp_values else 4
        exp_sel_lbl = st.selectbox("Expiry", exp_labels, index=cur_exp_idx, key="exp")
        exp_sel = EXPIRY_OPTS[exp_sel_lbl]

    st.divider()
    st.markdown("<div class='shdr'>⚙️ Trade Size</div>", unsafe_allow_html=True)
    st.markdown("<div class='ibox'>Multi-leg: engine buys each selected strike separately per signal</div>", unsafe_allow_html=True)
    t1,t2 = st.columns(2)
    with t1:
        qty_sel = st.number_input("Contracts per Strike", 1, 100,
                                  int(db.get_param("trade_size","1") or 1), 1, key="qty")
    with t2:
        multi_opts = ["Single (1 strike)","Double (OTM1+OTM2)","Triple (OTM1+OTM2+OTM3)"]
        cur_multi  = db.get_param("multi_leg","Single (1 strike)")
        ml_idx     = multi_opts.index(cur_multi) if cur_multi in multi_opts else 0
        multi_sel  = st.selectbox("Multi-Leg", multi_opts, index=ml_idx, key="ml")

    if st.button("💾 SAVE ALL SETTINGS", key="btn_save"):
        db.set_param("timeframe",       tf_sel)
        db.set_param("st_period",       str(per_sel))
        db.set_param("st_multiplier",   str(mul_sel))
        db.set_param("trade_mode",      mode_sel)
        db.set_param("distance_type",   dist_sel)
        db.set_param("expiry_mode",     exp_sel)
        db.set_param("trade_size",      str(qty_sel))
        db.set_param("multi_leg",       multi_sel)
        db.set_param("settings_updated_at", str(int(time.time())))
        st.success(f"✅ Saved! TF={tf_sel} ST={per_sel}/{mul_sel} {dist_sel} {exp_sel_lbl} Qty={qty_sel} Mode={mode_sel}")

    st.divider()
    st.markdown("<div class='shdr'>📡 Live Chain Preview</div>", unsafe_allow_html=True)
    if st.button("🔍 Preview Selected Strike", key="btn_prev"):
        with st.spinner("Fetching chain..."):
            try:
                chain   = oe.get_option_chain()
                btc_px  = oe.get_btc_spot_price()
                expiry  = oe.resolve_expiry(chain, exp_sel)
                sig     = last_signal if last_signal in ["CALL","PUT"] else "CALL"
                product = oe.find_strike(sig, dist_sel, btc_px, chain, expiry)
                if product:
                    ltp = oe.get_option_ltp(product["symbol"])
                    st.markdown(f"""<div class='sbox'>
                      ✅ <b>{product['symbol']}</b><br>
                      Strike: ${product['strike']:,.0f} | Expiry: {expiry}<br>
                      Current Premium: <b>{ltp:.4f}</b> | 2x Target: <b>{ltp*2:.4f}</b>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.warning("Strike not found for selected settings.")
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()

# ── TRADE HISTORY ─────────────────────────────────────────
st.markdown("<div class='shdr'>📋 Recent Option Trades</div>", unsafe_allow_html=True)
trades = db.get_recent_option_trades(20)
if trades:
    rows = ""
    for t in trades:
        ts, sig, sym, strike, dist, entry, exit_p, pnl, reason, status = t
        pc    = "pp" if (pnl or 0) >= 0 else "pn"
        emoji = "📈" if sig=="CALL" else "📉"
        s_color = "#1565C0" if sig=="CALL" else "#ad1457"
        rows += (f"<tr>"
                 f"<td>{ts}</td>"
                 f"<td style='color:{s_color};font-weight:700;'>{emoji} {sig}</td>"
                 f"<td>{sym}</td>"
                 f"<td>${float(strike or 0):,.0f}</td>"
                 f"<td>{dist}</td>"
                 f"<td>{float(entry or 0):.4f}</td>"
                 f"<td>{float(exit_p or 0):.4f}</td>"
                 f"<td class='{pc}'>${float(pnl or 0):+.2f}</td>"
                 f"<td>{reason}</td>"
                 f"<td>{status}</td>"
                 f"</tr>")
    st.markdown(f"""<table class='ttbl'><thead><tr>
        <th>Time</th><th>Side</th><th>Symbol</th><th>Strike</th>
        <th>Distance</th><th>Entry Px</th><th>Exit Px</th>
        <th>PnL</th><th>Reason</th><th>Status</th>
    </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)
else:
    st.markdown("<div class='ibox'>No trades yet. Start the engine to begin trading.</div>", unsafe_allow_html=True)

st.divider()
st.markdown("""
<div style='text-align:center;color:#5ba3c9;font-size:11px;'>
  ₿ BITCOIN OPTIONS ENGINE v2.0 · SuperTrend 15m · Delta Exchange India · Dashboard: http://157.49.182.222:8503
</div>""", unsafe_allow_html=True)

# Auto-refresh every 30s
st.markdown("<script>setTimeout(()=>window.location.reload(),30000)</script>", unsafe_allow_html=True)
