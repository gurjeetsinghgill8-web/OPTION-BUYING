# -*- coding: utf-8 -*-
"""Find correct VPS directory for option-buying engine"""
import paramiko

VPS_HOST = "46.224.133.16"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)

def run(cmd):
    _, o, e = ssh.exec_command(cmd)
    out = o.read().decode(errors="replace").strip()
    if out:
        print(out)

print("=== Searching for main.py (option engine) ===")
run("find /root -name 'main.py' 2>/dev/null | head -20")

print("\n=== Root directories ===")
run("ls /root/")

print("\n=== Running python processes ===")
run("ps aux | grep python | grep -v grep")

ssh.close()
