#!/usr/bin/env python3
"""完整性校验：去标记（保内容、剥符号、剥|规范名后缀）后与底本逐字全等比对。
用法: python3 scripts/verify_annotation.py data/chapter_numbered/卷XXX.txt kg/entities/标注/卷XXX_标注.txt
PUA 差异单独分类报告。
"""
import sys, unicodedata

TYPE_CHARS = set('@=;&#%^~•!?+◆{:[_$◈◉○◇')

def strip_marks(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '〖':
            j = text.find('〗', i)
            if j == -1:
                out.append(ch); i += 1; continue
            inner = text[i+1:j]
            if inner and inner[0] in TYPE_CHARS:
                inner = inner[1:]
            out.append(inner.split('|', 1)[0])
            i = j + 1
        elif ch == '⟦':
            j = text.find('⟧', i)
            if j == -1:
                out.append(ch); i += 1; continue
            inner = text[i+1:j]
            if inner and inner[0] in TYPE_CHARS:
                inner = inner[1:]
            out.append(inner.split('|', 1)[0])
            i = j + 1
        elif ch == '〘':
            j = text.find('〙', i)
            if j == -1:
                out.append(ch); i += 1; continue
            out.append(text[i+1:j])
            i = j + 1
        else:
            out.append(ch); i += 1
    return ''.join(out)

def is_pua(c): return 0xE000 <= ord(c) <= 0xF8FF

def main(base_path, ann_path):
    base = open(base_path, encoding='utf-8').read()
    ann = open(ann_path, encoding='utf-8').read()
    stripped = strip_marks(ann)
    # lint: 括号配对
    issues = []
    if ann.count('〖') != ann.count('〗'): issues.append(f"括号不配对 〖={ann.count('〖')} 〗={ann.count('〗')}")
    if ann.count('⟦') != ann.count('⟧'): issues.append(f"括号不配对 ⟦={ann.count('⟦')} ⟧={ann.count('⟧')}")
    if '⟦' in ann.replace('⟧','') and False: pass
    for k, pair in (('乙1a', ('〖','⟧')), ('乙1b', ('⟦','〗'))):
        pass
    # 空标注
    for pat in ('〖〗', '⟦⟧', '〖|〗'):
        if pat in ann: issues.append(f"空标注: {pat}")
    # 嵌套
    depth_n = depth_v = 0
    for ch in ann:
        if ch == '〖':
            depth_n += 1
            if depth_n > 1: issues.append("嵌套: 〖 内再入 〖"); break
        elif ch == '〗': depth_n -= 1
        elif ch == '⟦':
            depth_v += 1
            if depth_v > 1: issues.append("嵌套: ⟦ 内再入 ⟦"); break
        elif ch == '⟧': depth_v -= 1
    marks_n = ann.count('〖'); marks_v = ann.count('⟦')
    if stripped == base:
        print(f"PASS  名词标记 {marks_n}  动词标记 {marks_v}  长度 {len(base)}")
    else:
        print("FAIL")
        for s in issues: print("LINT:", s)
        # 逐字符定位
        n = min(len(stripped), len(base))
        diffs = []
        i = 0
        while i < n and len(diffs) < 20:
            if stripped[i] != base[i]:
                ctx_b = base[max(0,i-12):i+12]
                ctx_s = stripped[max(0,i-12):i+12]
                diffs.append(f"位置{i}: 底本…{ctx_b}… vs 标注…{ctx_s}… (底本字={base[i]!r} 标注字={stripped[i]!r})")
                i += 1
                # 跳过连续差异
                while i < n and stripped[i] != base[i]: i += 1
            else:
                i += 1
        for d in diffs: print(d)
        print(f"长度: 底本 {len(base)} vs 去标记 {len(stripped)} (差 {len(stripped)-len(base)})")
        pua_b = [c for c in base if is_pua(c)]
        pua_s = [c for c in stripped if is_pua(c)]
        if pua_b != pua_s:
            print(f"PUA差异: 底本 {len(pua_b)} 个 vs 去标记 {len(pua_s)} 个")
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
