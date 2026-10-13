#!/usr/bin/env python3
"""锚点替换式标注装配：底本行 + (查找串→替换串) 规格 → 完整标注文件。

chunk spec 每行格式: 行号<TAB>查找串<TAB>替换串[<TAB>次数]
  - 查找串/替换串中均不得含标记字符（〖〗⟦⟧〘〙）
  - strip_marks(替换串) 必须等于 查找串（消歧走 〖TYPE 显示名|规范名〗）
  - 同一行多条规格按顺序处理；与已占用区间重叠的匹配自动跳过
  - 次数默认 -1 = 全部未占用匹配；正数 = 只取前 N 个匹配
用法: python3 annot_spec.py <底本> <输出> <spec1> [spec2 ...]
"""
import sys, os, re

MARK_CH = set('〖〗⟦⟧〘〙')

def strip_marks(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in '〖⟦〘':
            close = {'〖': '〗', '⟦': '⟧', '〘': '〙'}[ch]
            j = text.find(close, i)
            if j == -1:
                out.append(ch); i += 1; continue
            inner = text[i+1:j]
            if ch in '〖⟦' and inner and inner[0] in '@=;&#%^~•!?+◆{:[_$◈◉○◇':
                inner = inner[1:]
            out.append(inner.split('|', 1)[0])
            i = j + 1
        else:
            out.append(ch); i += 1
    return ''.join(out)


def spans_of(hay, needle):
    res = []
    start = 0
    while True:
        k = hay.find(needle, start)
        if k == -1:
            break
        res.append((k, k + len(needle)))
        start = k + len(needle)
    return res


def main(base_path, out_path, spec_paths):
    base = open(base_path, encoding='utf-8').read().split('\n')
    specs = {}
    errors = []
    for sp in spec_paths:
        for ln, raw in enumerate(open(sp, encoding='utf-8').read().split('\n'), 1):
            if not raw.strip():
                continue
            parts = raw.split('\t')
            if len(parts) < 3:
                errors.append(f"{sp}:{ln} 字段不足: {raw!r}")
                continue
            idx = int(parts[0])
            find, repl = parts[1], parts[2]
            cnt = int(parts[3]) if len(parts) > 3 else -1
            if not find:
                errors.append(f"{sp}:{ln} 空查找串")
                continue
            if any(c in MARK_CH for c in find):
                errors.append(f"{sp}:{ln} 查找串含标记字符: {find!r}")
                continue
            if strip_marks(repl) != find:
                errors.append(f"{sp}:{ln} 替换串去标记≠查找串: {find!r} vs {strip_marks(repl)!r}")
                continue
            specs.setdefault(idx, []).append((find, repl, cnt, f"{sp}:{ln}"))
    if errors:
        print("SPEC ERROR")
        for e in errors:
            print(e)
        sys.exit(2)

    out = []
    marks_n = marks_v = 0
    for i, src in enumerate(base):
        occupied = []
        edits = []
        for find, repl, cnt, where in specs.get(i, []):
            applied = 0
            for (a, b) in spans_of(src, find):
                if any(not (b <= oa or a >= ob) for oa, ob in occupied):
                    continue
                if cnt != -1 and applied >= cnt:
                    break
                occupied.append((a, b))
                edits.append((a, b, repl))
                applied += 1
            if applied == 0 and cnt != 0:
                errors.append(f"行{i} 锚点未命中({where}): {find!r}")
        if errors:
            break
        edits.sort()
        buf = []
        pos = 0
        for a, b, repl in edits:
            buf.append(src[pos:a])
            buf.append(repl)
            pos = b
        buf.append(src[pos:])
        text = ''.join(buf)
        marks_n += text.count('〖')
        marks_v += text.count('⟦')
        out.append(text)
    if errors:
        print("FAIL")
        for e in errors:
            print(e)
        sys.exit(1)
    open(out_path, 'w', encoding='utf-8').write('\n'.join(out))
    print(f"OK {out_path}  行数 {len(out)}  名词标记 {marks_n}  动词标记 {marks_v}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
