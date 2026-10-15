#!/usr/bin/env python3
"""本地化标注工作台（BASE=/workspace/hanshu-KB，逻辑同 annotate_station.py）"""
import sys, json, re, subprocess, os, fcntl, time
from pathlib import Path

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
CH = BASE / "data/chapter_numbered"
ANN = BASE / "kg/entities/标注"
VERIFY = BASE / "scripts/verify_annotation.py"

def chapter_file(juan):
    for f in sorted(CH.glob(f"{juan}*.txt")):
        return f
    raise SystemExit(f"找不到底本: {juan}")

def parse_paras(text):
    marks = [(m.start(), m.group().strip()) for m in re.finditer(r'\[(?:r\d+|\d+(?:\.\d+)?)\]', text)]
    if not marks:
        return [("[0]", text)]
    out = []
    first = text[:marks[0][0]]
    if first.strip():
        out.append(("[head]", first))
    for i, (pos, tag) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(text)
        out.append((tag, text[pos:end]))
    return out

def ann_file(juan):
    return ANN / f"{juan}_标注.txt"

def load_done(juan):
    f = ann_file(juan)
    if not f.exists():
        return {}
    return dict(parse_paras(f.read_text(encoding="utf-8")))

def cmd_show(juan):
    chf = chapter_file(juan)
    paras = parse_paras(chf.read_text(encoding="utf-8"))
    done = load_done(juan)
    todo = [(t, p) for t, p in paras if t not in done and p.strip()]
    print(f"===== {juan} 待标 {len(todo)}/{len(paras)} 段 =====")
    for t, p in todo:
        print(f"\n### {t} ({len(p)}字)")
        print(p)

def cmd_add(juan, tag, annotated):
    chf = chapter_file(juan)
    src = chf.read_text(encoding="utf-8")
    paras = dict(parse_paras(src))
    if tag not in paras:
        raise SystemExit(f"标号 {tag} 不存在于底本。可用: {list(paras)[:10]}")
    stripped = strip_markers(annotated)
    base_seg = paras[tag]
    tail = base_seg[len(base_seg.rstrip()):]
    core = base_seg.rstrip()
    if stripped.rstrip() != core:
        for i, (a, b) in enumerate(zip(stripped.rstrip(), core)):
            if a != b:
                raise SystemExit(f"段 {tag} 第{i}字不一致:\n  标: ...{stripped.rstrip()[max(0,i-12):i+12]}...\n  底: ...{core[max(0,i-12):i+12]}...")
        raise SystemExit(f"段 {tag} 长度不一致: 标{len(stripped.rstrip())} vs 底{len(core)}")
    annotated = annotated.rstrip() + tail
    af = ann_file(juan)
    lock = af.with_suffix(".lock")
    with open(lock, "w") as lf:
        for _ in range(60):
            try:
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                time.sleep(1)
        else:
            raise SystemExit("获取文件锁超时")
        done = load_done(juan)
        done[tag] = annotated
        allp = parse_paras(src)
        out = [done.get(t, p) for t, p in allp]
        af.write_text("".join(out), encoding="utf-8")
    print(f"段 {tag} 已保存 ({len(annotated)}字)")

TYPE_CHARS = set('@=;&#%^~•!?+◆{:[_$◈◉○◇')

def strip_markers(s):
    out = []; i = 0
    while i < len(s):
        ch = s[i]
        if ch == '〖' or ch == '⟦':
            close = '〗' if ch == '〖' else '⟧'
            j = s.find(close, i)
            if j == -1:
                out.append(ch); i += 1; continue
            inner = s[i+1:j]
            if inner and inner[0] in TYPE_CHARS:
                inner = inner[1:]
            out.append(inner.split('|', 1)[0])
            i = j + 1
        elif ch == '〘':
            j = s.find('〙', i)
            if j == -1:
                out.append(ch); i += 1; continue
            out.append(s[i+1:j]); i = j + 1
        else:
            out.append(ch); i += 1
    return ''.join(out)

def cmd_status(juan):
    chf = chapter_file(juan)
    paras = parse_paras(chf.read_text(encoding="utf-8"))
    done = load_done(juan)
    n = sum(1 for t, p in paras if t in done)
    print(f"{juan}: {n}/{len(paras)} 段已标 ({n*100//len(paras)}%)")

def cmd_verify(juan):
    chf = chapter_file(juan)
    r = subprocess.run(["python3", str(VERIFY), str(chf), str(ann_file(juan))],
                       capture_output=True, text=True)
    print(r.stdout)
    if r.stderr: print(r.stderr)
    return r.returncode

def cmd_remove_lock(juan):
    lock = ann_file(juan).with_suffix(".lock")
    if lock.exists():
        lock.unlink()
        print(f"已删除 {lock}")
    else:
        print("无 lock")

if __name__ == "__main__":
    juan = sys.argv[1]; cmd = sys.argv[2]
    if cmd == "show": cmd_show(juan)
    elif cmd == "status": cmd_status(juan)
    elif cmd == "verify": sys.exit(cmd_verify(juan))
    elif cmd == "add":
        cmd_add(juan, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else sys.stdin.read())
    elif cmd == "rlock": cmd_remove_lock(juan)
    else: print(__doc__); sys.exit(1)
