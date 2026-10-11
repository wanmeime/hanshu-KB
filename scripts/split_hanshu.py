#!/usr/bin/env python3
"""TASK-003 步骤1：把 shiji-kb-reference/corpus/other/汉书.txt 按 120 卷切分到 data/chapter/。

方案依据：
- 本地汉书.txt 头部目录（120 条）为切分依据，卷号采用目录中的传统卷号
  （卷一上/卷一下同属卷一，惠帝纪=卷二 …… 异姓诸侯王表=卷十三）。
- 文件名 = 卷{三位卷号}[字母后缀]_{目录标题}.txt；同卷号的后续分卷按
  b/c/d/e 后缀（沿用 data/raw/hanshu_tables 卷015/卷015b 先例）。
- 卷十三—卷二十（八表 10 个分卷单元）正文以 data/raw/hanshu_tables/ 的
  维基文库补源文件为准，本脚本只处理其余 110 个分卷。
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shiji-kb-reference/corpus/other/汉书.txt"
OUT = ROOT / "data/chapter"

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
PARTS = {"上", "中", "下", "中之上", "中之下", "下之上", "下之下"}
SUFFIXES = "bcdefg"

num_re = re.compile(r"^(一|二|三|四|五|六|七|八|九|十)(百)?(一|二|三|四|五|六|七|八|九|十)?(一|二|三|四|五|六|七|八|九|十)?$")


def cn2int(s: str) -> int:
    """卷中文数字 → 整数（支持 一~一百、二十七、一百 等本目录出现的范围）。"""
    if s == "一百":
        return 100
    if "百" in s:
        raise ValueError(f"仅支持到一百，无法解析: {s!r}")
    if "十" in s:
        tens, _, ones = s.partition("十")
        return (CN_DIGIT[tens] if tens else 1) * 10 + (CN_DIGIT[ones] if ones else 0)
    return CN_DIGIT[s]


def parse_toc(lines):
    """解析头部目录 120 条 → [(seq, base, part, note, title)]。"""
    units = []
    pat = re.compile(r"^卷([" + "".join(CN_DIGIT) + "百]+)("
                     + "|".join(sorted(PARTS, key=len, reverse=True))
                     + r")?(?:（[^）]*）)?\s*(.+)$")
    for ln in lines:
        m = pat.match(ln.strip())
        if not m:
            raise ValueError(f"目录行解析失败: {ln!r}")
        numstr, part, title = m.groups()
        units.append({
            "seq": len(units) + 1,
            "base": cn2int(numstr),
            "part": part or "",
            "title": title.strip(),
        })
    return units


def file_id(units):
    """为每个分卷单元分配文件名卷号：首个用纯数字，后续加 b/c/d/e。"""
    seen = {}
    for u in units:
        base = u["base"]
        idx = seen.get(base, 0)
        seen[base] = idx + 1
        u["fid"] = f"{base:03d}" + (SUFFIXES[idx - 1] if idx else "")
    return units


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 1. 定位目录区：从第一个 "卷一上" 行到 "汉  书" 分隔行
    toc_start = next(i for i, ln in enumerate(lines) if ln.strip() == "卷一上 高帝纪第一上")
    body_marker = next(i for i, ln in enumerate(lines) if ln.strip() == "汉  书" and i > toc_start)
    toc_lines = [ln for ln in lines[toc_start:body_marker] if ln.strip()]
    units = file_id(parse_toc(toc_lines))
    print(f"目录条目数: {len(units)}")
    if len(units) != 120:
        print("!! 目录条目数不是 120，中止", file=sys.stderr)
        sys.exit(1)

    # 2. 遍历正文，检测卷头
    #    样式A：卷一上  高帝纪第一上（卷号+标题同一行）
    #    样式B：卷十一 / 哀帝纪第十一（卷号行 + 下一非空行为标题）
    part_alt = "|".join(sorted(PARTS, key=len, reverse=True))
    NUMCLS = "[" + "".join(CN_DIGIT) + "百]+"
    head_pat = [
        # 卷号+（注记）独立行 → 标题在下一非空行
        re.compile(r"^卷(" + NUMCLS + ")(" + part_alt + r")?（[^）]*）\s*$"),
        # 纯卷号行 → 标题在下一非空行
        re.compile(r"^卷(" + NUMCLS + ")(" + part_alt + r")?\s*$"),
        # 卷号（注记）+标题同行
        re.compile(r"^卷(" + NUMCLS + ")(" + part_alt + r")?（[^）]*）[ 　]*(\S.*)$"),
        # 卷号+标题同行（可无空格，如“卷三十一陈胜项籍传第一”）
        re.compile(r"^卷(" + NUMCLS + ")(" + part_alt + r")?[ 　]*(\S.*)$"),
    ]

    body_units = []  # (start_idx, numstr, part, title or None)
    i = body_marker + 1
    n = len(lines)
    while i < n:
        ln = lines[i]
        m2 = None
        for pi, pat in enumerate(head_pat):
            m = pat.match(ln.strip())
            if m:
                m2 = (pi, m)
                break
        if m2:
            pi, m = m2
            if pi in (0, 1):
                # 下一非空行视为标题行
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                title = lines[j].strip() if j < n else ""
                body_units.append({"start": i, "numstr": m.group(1), "part": m.group(2) or "",
                                   "title": title, "title_line": j})
                i = j + 1
            else:
                body_units.append({"start": i, "numstr": m.group(1), "part": m.group(2) or "",
                                   "title": m.group(3).strip()})
                i += 1
            continue
        i += 1

    print(f"正文检测到卷头数: {len(body_units)}")
    for b in body_units:
        b["num"] = cn2int(b["numstr"])

    # 3. 对齐目录与正文
    if len(body_units) != len(units):
        print("!! 正文卷头数与目录条目数不一致，中止", file=sys.stderr)
        for k, b in enumerate(body_units):
            print(f"  body[{k}] 卷{b['numstr']}{b['part']} {b.get('title','')[:20]}", file=sys.stderr)
        sys.exit(1)
    mismatches = []
    for toc_u, b in zip(units, body_units):
        if toc_u["base"] != b["num"] or toc_u["part"] != b["part"]:
            mismatches.append((toc_u, b))
    if mismatches:
        print(f"!! 卷号对齐失败 {len(mismatches)} 处:", file=sys.stderr)
        for t, b in mismatches[:20]:
            print(f"  目录: 卷{t['base']}{t['part']} {t['title']}  vs  正文: 卷{b['numstr']}{b['part']} {b.get('title','')}", file=sys.stderr)
        sys.exit(1)

    # 4. 切分输出（非表卷：表 = base 13..20）
    out_dir = OUT
    report = []
    for toc_u, b in zip(units, body_units):
        is_table = 13 <= toc_u["base"] <= 20
        end = b.get("title_line", b["start"]) + 1
        # 正文结束于下一个卷头行之前
        next_start = b.get("title_line", b["start"])
        content_lines = []
        for ln in lines[end:]:
            pass
        # 重新计算：内容 = title 行之后到下一个卷头 start 之前
        idx_in_list = body_units.index(b)
        nxt = body_units[idx_in_list + 1]["start"] if idx_in_list + 1 < len(body_units) else len(lines)
        content_lines = lines[end:nxt]
        # 去掉每行首尾空白（底本缩进等格式痕迹），空行保留
        content_lines = [ln.strip() for ln in content_lines]
        # 去掉首尾空行
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        content = "\n".join(content_lines) + "\n"
        fname = f"卷{toc_u['fid']}_{toc_u['title']}.txt"
        report.append({
            "seq": toc_u["seq"], "fid": toc_u["fid"], "base": toc_u["base"],
            "part": toc_u["part"], "title": toc_u["title"],
            "body_title": b.get("title", ""),
            "is_table": is_table,
            "chars": len(content.replace("\n", "")),
            "src_start": end + 1, "src_end": nxt,
            "file": fname,
        })
        if not is_table:
            (out_dir / fname).write_text(content, encoding="utf-8")

    json.dump(report, open(ROOT / "scripts/split_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total = sum(r["chars"] for r in report if not r["is_table"])
    print(f"非表卷 {sum(1 for r in report if not r['is_table'])} 个，正文合计 {total} 字符")
    for r in report:
        flag = "表" if r["is_table"] else ("  " if r["body_title"] == r["title"] or r["title"].startswith(r["body_title"]) else "!!标题差异")
        print(f"{r['seq']:>3} 卷{r['fid']:<4} {r['title']:<22} {r['chars']:>7} {flag}")


if __name__ == "__main__":
    main()
