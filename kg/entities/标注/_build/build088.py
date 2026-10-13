#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, importlib.util, difflib, re

BASE, OUT = sys.argv[1], sys.argv[2]
PARTS = sys.argv[3:]
R = []
for p in PARTS:
    ns = {}
    exec(open(p, encoding="utf-8").read(), ns)
    R.extend(ns["R"])

lines = open(BASE, encoding="utf-8").read().split("\n")

# 1) 书名号预标：〖{《X》〗（X 非空）
for i, ln in enumerate(lines):
    lines[i] = re.sub(r"《[^《》]+》", lambda m: "〖{" + m.group(0) + "〗", ln)

miss, warn = [], []
for ln, old, new in R:
    i = ln - 1
    if old not in lines[i]:
        miss.append((ln, old))
        continue
    if lines[i].count(old) > 1:
        warn.append((ln, old, lines[i].count(old)))
    lines[i] = lines[i].replace(old, new, 1)
text = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(text)

for w in warn:
    print(f"WARN 多重 L{w[0]} x{w[2]}: {w[1][:40]}")
for ln, old in miss:
    print(f"MISS L{ln}: {old}")
if miss:
    sys.exit(2)

spec = importlib.util.spec_from_file_location("v", "scripts/verify_annotation.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
base = open(BASE, encoding="utf-8").read()
stripped = v.strip_marks(text)
if stripped != base:
    sm = difflib.SequenceMatcher(None, base, stripped, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            print(f"{tag} 底本«{base[i1:i2]}»[..{base[max(0,i1-12):i1]}|{base[i2:i2+12]}..] 标注«{stripped[j1:j2]}»")
    sys.exit(1)
print("BUILD OK strip == base")
