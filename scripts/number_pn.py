#!/usr/bin/env python3
"""TASK-003 步骤4：给 data/chapter/ 全部 120 卷加 Purple Numbers 段落编号，
输出到 data/chapter_numbered/（同名文件）。

规则（依据 shiji-kb-reference SKILL_02a）：
- [0] 篇名（文件名标题）
- [N] 一级段落，章内从 1 连续递增
- 行末无句末标点且下一行非空 → 与下一行合并（阶段1.5 误分段修复，4 条规则）
- 段落 >500 字 → 空父 [N] + 语义子段 [N.1..N.k]（按句末边界切，≤500字）
- 表类（卷013-020）：含全角"｜"的行 = 表行 → [rN]，章内跨表连续递增
- 自检：父子铁律、同层连续性
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/chapter"
OUT = ROOT / "data/chapter_numbered"

ENDINGS = set("。！？”』…：；")
SENT_END = re.compile(r"[。！？”』…]")
TABLE_FILES = {f.name for f in SRC.glob("卷*.txt")
               if f.stem.split("_")[0][1:4].isdigit()
               and 13 <= int(f.stem.split("_")[0][1:4]) <= 20}


def merge_wrapped(lines):
    """阶段1.5：行末无句末标点 → 与下一行合并。"""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        cur = lines[i]
        j = i + 1
        while j < n and lines[j].strip():
            tail = cur.rstrip()[-1] if cur.strip() else ""
            if (not cur.strip() or tail in ENDINGS
                    or len(cur.strip()) < 10):
                break
            cur = cur.rstrip() + lines[j].strip()
            j += 1
        out.append(cur.strip())
        i = j if j > i + 1 else i + 1
    return [ln for ln in out if ln]


def split_long(text, threshold=500, cap=120):
    """段落 >threshold 视为超长（多为整卷单行的底本格式残留），
    按句末边界切分，子段粒度贴近全书自然段（实测中位25字/P75 90字），cap=120。"""
    if len(text) <= threshold:
        return [text]
    parts = re.findall(r".*?[。！？”』…]|.+?$", text, flags=re.M)
    chunks = []
    buf = ""
    for s in parts:
        if buf and len(buf) + len(s) > cap:
            chunks.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        chunks.append(buf)
    return chunks


def number_file(path):
    title = path.stem.split("_", 1)[1]
    is_table = path.name in TABLE_FILES
    raw = path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in raw.split("\n")]

    if is_table:
        # 表卷：不合并行；按原文顺序处理，含"｜"的行=表行（[rN] 章内连续），
        # 其余=段落（[N]）
        out = [f"[0] {title}", ""]
        n = 0
        r = 0
        for ln in lines:
            if not ln:
                continue
            if "｜" in ln:
                r += 1
                out.append(f"[r{r}] {ln}")
                out.append("")
                continue
            n += 1
            chunks = split_long(ln)
            if len(chunks) == 1:
                out.append(f"[{n}] {ln}")
                out.append("")
            else:
                out.append(f"[{n}]")
                out.append("")
                for k, c in enumerate(chunks, 1):
                    out.append(f"[{n}.{k}] {c}")
                    out.append("")
    else:
        paras = merge_wrapped(lines)
        out = [f"[0] {title}", ""]
        n = 0
        for ln in paras:
            n += 1
            chunks = split_long(ln)
            if len(chunks) == 1:
                out.append(f"[{n}] {ln}")
                out.append("")
            else:
                out.append(f"[{n}]")
                out.append("")
                for k, c in enumerate(chunks, 1):
                    out.append(f"[{n}.{k}] {c}")
                    out.append("")
    return "\n".join(out).rstrip() + "\n", n, (r if is_table else 0)


def lint(text, fname):
    """父子铁律 + 同层连续。"""
    problems = []
    nums = []
    rnums = []
    for ln in text.split("\n"):
        m = re.match(r"^\[(\d+(?:\.\d+)*)\]", ln)
        if m:
            nums.append(m.group(1))
        m = re.match(r"^\[r(\d+)\]", ln)
        if m:
            rnums.append(int(m.group(1)))
    for num in nums:
        if "." in num:
            parent = num.rsplit(".", 1)[0]
            if parent not in nums:
                problems.append(f"{fname}: [{num}] 缺父 [{parent}]")
    seq = [int(x.split(".")[0]) for x in nums]
    if seq and seq[0] != 0:
        problems.append(f"{fname}: 首段不是 [0]")
    # 顶级段落连续性：按首次出现顺序去重后检查
    seen_top = []
    dup = set()
    for x in seq[1:]:
        t = x
        if t not in dup:
            dup.add(t)
            seen_top.append(t)
    expected = list(range(1, max(seen_top) + 1)) if seen_top else []
    if seen_top != expected:
        problems.append(f"{fname}: 顶级段落不连续")
    if rnums and rnums != list(range(1, max(rnums) + 1)):
        problems.append(f"{fname}: [rN] 不连续")
    return problems


def main():
    OUT.mkdir(exist_ok=True)
    stats = []
    problems = []
    for f in sorted(SRC.glob("卷*.txt")):
        text, n, nr = number_file(f)
        (OUT / f.name).write_text(text, encoding="utf-8")
        problems += lint(text, f.name)
        stats.append({"file": f.name, "paras": n, "rows": nr,
                      "chars": len(text)})
    json.dump(stats, open(ROOT / "scripts/pn_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total_paras = sum(s["paras"] for s in stats)
    total_rows = sum(s["rows"] for s in stats)
    print(f"文件 {len(stats)} 个；段落 {total_paras}（表行另 {total_rows}）")
    if problems:
        print("LINT 问题:")
        for p in problems[:20]:
            print(" ", p)
    else:
        print("LINT: 通过（父子铁律、[0]首段、顶级连续、rN 连续）")
    # 段落数最多的文件
    top = sorted(stats, key=lambda s: -s["paras"])[:8]
    for s in top:
        print(f"  {s['file']}: 段 {s['paras']} 表行 {s['rows']}")


if __name__ == "__main__":
    main()
