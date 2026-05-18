"""Fix: Guardian incorrectly placed inside is_force_close_time(). Move it out."""
content = open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\main.py', encoding='utf-8').read()

# The is_force_close_time function body got corrupted — fix it
bad = '''def is_force_close_time():
    """
    Returns True after 3:20 PM IST — force-close everything.
    Options lose value fast near 3:30 close — exit by 3:20.
    """
    # SELF-HEALING GUARDIAN
# Runs every 5 min loop — BEFORE any trade logic
# ═══════════════════════════════════════════════════════════
def _run_guardian():'''

good = '''def is_force_close_time():
    """
    Returns True after 3:20 PM IST — force-close everything.
    Options lose value fast near 3:30 close — exit by 3:20.
    """
    now = datetime.datetime.now()
    return now.hour > 15 or (now.hour == 15 and now.minute >= 20)

# ═══════════════════════════════════════════════════════════
# SELF-HEALING GUARDIAN v2 — qty-aware, dashboard-safe
# Runs every new candle — BEFORE any trade logic
# ═══════════════════════════════════════════════════════════
def _run_guardian():'''

if bad in content:
    content = content.replace(bad, good, 1)
    # Also remove the duplicate return line at the end of guardian
    content = content.replace(
        '        log_terminal(f"Guardian: All OK — {exchange_qty} lot(s) as expected", "INFO")\n    now = datetime.datetime.now()\n    return now.hour > 15 or (now.hour == 15 and now.minute >= 20)\n',
        '        log_terminal(f"Guardian: All OK — {exchange_qty} lot(s) as expected", "INFO")\n'
    )
    open(r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\main.py', 'w', encoding='utf-8').write(content)
    print("FIXED OK")
else:
    print("Pattern not found — checking...")
    idx = content.find('is_force_close_time')
    print(repr(content[idx:idx+300]))
