#!/usr/bin/env python3
"""分批装配标注稿 + 逐段完整性预校验。

用法:
    python3 scripts/assemble_annotation.py <底本> <输出> <chunk1> [chunk2 ...]

chunk 文件每行格式:  段落行号<TAB>标注后段落文本
   - 底本按行切分，行号即 chunk 中的"段落行号"（0-based，对应底本第 N+1 行）
   - 空行可省略（自动补空行）；非空行必须全部提供，否则报错
   - 先对每段做 strip_marks 与底本逐字比对，任一段不符即中止，不写出文件
"""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_annotation import strip_marks

PUA_TOKEN = re.compile(r'<PUA-([0-9A-Fa-f]{4,6})>')


def unescape_pua(text):
    return PUA_TOKEN.sub(lambda m: chr(int(m.group(1), 16)), text)


def main(base_path, out_path, chunk_paths):
    base = open(base_path, encoding='utf-8').read().split('\n')
    ann = {}
    for cp in chunk_paths:
        for ln, raw in enumerate(open(cp, encoding='utf-8').read().split('\n'), 1):
            if '\t' not in raw and not raw.strip():
                continue
            idx, _, text = raw.partition('\t')
            idx = int(idx)
            text = unescape_pua(text).rstrip('\r')
            if idx in ann:
                print(f"重复标注行号 {idx} (来自 {cp}:{ln})")
                sys.exit(2)
            # 自动补齐行首 PN 编号（如 "[12] "），编号不在标注范围内
            src = base[idx] if idx < len(base) else ''
            if src.startswith('[') and '] ' in src:
                prefix = src[:src.index('] ') + 2]
                if not text.startswith(prefix):
                    text = prefix + text
            ann[idx] = text

    errs = []
    for idx in sorted(ann):
        src = base[idx] if idx < len(base) else '<越界>'
        if strip_marks(ann[idx]) != src:
            errs.append((idx, src, ann[idx]))
    missing = [i for i, l in enumerate(base) if l.strip() and i not in ann]
    if errs or missing:
        print("预校验 FAIL")
        for idx, src, got in errs:
            print(f"\n[行{idx}] 底本: {src[:120]}")
            print(f"[行{idx}] 标注: {got[:120]}")
            s, b = strip_marks(got), src
            n = min(len(s), len(b))
            for k in range(n):
                if s[k] != b[k]:
                    print(f"  首个差异@{k}: 底本 {b[k]!r} vs 标注 {s[k]!r}")
                    print(f"  底本上下文: …{b[max(0,k-15):k+15]}…")
                    print(f"  标注上下文: …{s[max(0,k-15):k+15]}…")
                    break
            else:
                print(f"  长度差: 底本 {len(b)} vs 去标记 {len(s)}")
        if missing:
            print(f"\n缺标注行号: {missing}")
        sys.exit(1)

    out = []
    marks_n = marks_v = 0
    for i, line in enumerate(base):
        t = ann.get(i, '')
        if t:
            marks_n += t.count('〖')
            marks_v += t.count('⟦')
        out.append(t)
    open(out_path, 'w', encoding='utf-8').write('\n'.join(out))
    print(f"OK 写出 {out_path}  行数 {len(out)}  名词标记 {marks_n}  动词标记 {marks_v}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
