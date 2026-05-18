"""Delete orphaned old guardian body - no unicode prints"""
import ast, sys, re
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\pc\Desktop\gurjas ai\OPTION BUYING\main.py'
content = open(path, encoding='utf-8').read()
lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# Find the orphaned code:
# It starts right after _audit_log function ends (the blank lines + "    # Fetch live positions")
# It ends before "# MAIN SIGNAL LOOP"
start_marker = '    # Fetch live positions from exchange'
end_marker = '# ═══════════════════════════════════════════════════════════\n# MAIN SIGNAL LOOP'

start_char = content.find(start_marker)
end_char   = content.find(end_marker)

if start_char == -1:
    print("Start marker not found!")
    exit(1)
if end_char == -1:
    print("End marker not found!")
    exit(1)

print(f"Orphaned code: chars {start_char} to {end_char}")
print(f"Start line: {content[:start_char].count(chr(10))+1}")
print(f"End line: {content[:end_char].count(chr(10))+1}")

# Go back a few lines from start to include blank lines before "# Fetch live..."
# Find the previous non-blank content before start_marker
pre = content[:start_char].rstrip()
# Remove trailing blank lines between _audit_log end and orphaned code
new_content = pre + '\n\n' + content[end_char:]

# Validate
try:
    ast.parse(new_content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: line {e.lineno}: {e.msg}")
    exit(1)

open(path, 'w', encoding='utf-8').write(new_content)
print("Written OK")

# Verify
final = open(path, encoding='utf-8').read()
guards = list(re.finditer(r'def _run_guardian\(\)', final))
print(f"Guardians remaining: {len(guards)}")

if 'DB_MISMATCH' in final:
    print("WARNING: DB_MISMATCH still in file!")
elif 'DB reset to FLAT' in final:
    print("WARNING: old message still in file!")
else:
    print("CLEAN: Old guardian fully removed!")

print(f"Final line count: {len(final.splitlines())}")
