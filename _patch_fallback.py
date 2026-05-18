content = open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\main.py', encoding='utf-8').read()

old = '''    def _enter_position(side):
        """Helper: fetch chain, find strike, buy option."""
        chain  = oe.get_option_chain()
        if not chain:
            log_terminal("Chain fetch failed — cannot enter.", "ERROR")
            return False
        if expiry_pref == "AUTO":
            expiry = oe.get_nearest_expiry(chain)
        else:
            expiry = expiry_pref
        if not expiry:
            log_terminal("No valid expiry found — cannot enter.", "ERROR")
            return False
        product = oe.find_strike(side, distance_type, last_close, chain, expiry)
        if not product:
            log_terminal(f"Strike not found for {side} {distance_type} — skipping.", "WARN")
            return False
        success, entry_px, trade_id = oe.buy_option(product, qty, side, distance_type)
        return success'''

new = '''    def _enter_position(side):
        """Helper: fetch chain, find strike, buy option with smart expiry fallback."""
        chain = oe.get_option_chain()
        if not chain:
            log_terminal("Chain fetch failed — cannot enter.", "ERROR")
            return False
        expiry = oe.resolve_expiry(chain, expiry_pref)
        if expiry:
            test = [p for p in chain if p["type"] == side.upper() and p["expiry"] == expiry]
            if not test:
                log_terminal(f"No {side} options for {expiry_pref} ({expiry}) — trying fallback", "WARN")
                expiry = None
        if not expiry:
            for fb in ["1DTE", "2DTE", "0DTE", "3DTE", "NEAREST_WEEKLY"]:
                if fb == expiry_pref:
                    continue
                candidate = oe.resolve_expiry(chain, fb)
                if candidate:
                    test2 = [p for p in chain if p["type"] == side.upper() and p["expiry"] == candidate]
                    if test2:
                        log_terminal(f"Expiry fallback: {expiry_pref} not found, using {fb} ({candidate})", "INFO")
                        _audit_log("ENGINE", f"Expiry fallback: {expiry_pref} unavailable", f"Using {fb} ({candidate})")
                        expiry = candidate
                        break
        if not expiry:
            log_terminal("No valid expiry found in any fallback — cannot enter.", "ERROR")
            return False
        product = oe.find_strike(side, distance_type, last_close, chain, expiry)
        if not product:
            log_terminal(f"Strike not found for {side} {distance_type} — skipping.", "WARN")
            return False
        success, entry_px, trade_id = oe.buy_option(product, qty, side, distance_type)
        return success'''

if old in content:
    content = content.replace(old, new, 1)
    open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\main.py', 'w', encoding='utf-8').write(content)
    print('REPLACED OK')
else:
    print('NOT FOUND')
    idx = content.find('def _enter_position')
    print('Found at index:', idx)
    print(repr(content[idx:idx+300]))
