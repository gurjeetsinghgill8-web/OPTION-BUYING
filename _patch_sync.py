"""Patch sync_option_position to NEVER clear DB"""
content = open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\options_executor.py', encoding='utf-8').read()

# Find the function start
start_marker = "def sync_option_position():"
end_marker = "    return option_found"

start_idx = content.find(start_marker)
end_idx   = content.find(end_marker, start_idx) + len(end_marker)

if start_idx == -1:
    print("ERROR: sync_option_position not found")
    exit(1)

new_func = '''def sync_option_position():
    """
    READ-ONLY sync — updates premium/upnl from exchange if position found.
    NEVER clears DB. DB is ground truth for option state.

    Position exits only via:
      - 2x target hit (check_profit_target)
      - Signal flip (run_options_loop state machine)
      - End-of-day 3:20 PM IST close
      - Manual: Dashboard "Square Off" button

    NOTE: Delta Exchange /v2/positions does NOT reliably return bought BTC
    options. Do NOT use it to determine if we are flat.

    Returns: True if position confirmed on exchange, False otherwise.
    """
    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return False

    path  = "/v2/positions"
    query = "?underlying_asset_symbol=BTC"
    result = _get(path, query, auth=True)

    if result is None:
        log_terminal("sync: API call failed — DB unchanged", "WARN")
        return False

    option_found = False
    for p in result:
        sz = float(p.get("size", 0))
        if sz == 0:
            continue
        symbol = p.get("product", {}).get("symbol") or p.get("symbol", "")
        if symbol.startswith("C-BTC") or symbol.startswith("P-BTC"):
            option_found = True
            entry_px = float(p.get("avg_entry_price", 0))
            upnl     = float(p.get("unrealized_pnl",  0))
            if entry_px > 0:
                db.set_param("active_option_entry_px", str(entry_px))
            db.set_param("option_unrealized_pnl", str(round(upnl, 4)))
            log_terminal(
                f"[SYNC] Found: {symbol} | Size={sz} | Entry={entry_px:.2f} | uPnL={upnl:+.4f}",
                "INFO"
            )
            break

    # SYNC NEVER CLEARS DB — exchange endpoint unreliable for bought options
    if not option_found:
        log_terminal("sync: 0 options on endpoint — DB unchanged (by design)", "INFO")

    return option_found'''

new_content = content[:start_idx] + new_func + content[end_idx:]
open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\options_executor.py', 'w', encoding='utf-8').write(new_content)
print("PATCHED OK")
print(f"Old length: {len(content)} | New length: {len(new_content)}")
