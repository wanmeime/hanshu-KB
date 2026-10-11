#!/usr/bin/env python3
"""TASK-003 步骤3a：扫描 data/chapter/ 全部文件的缺字记号，输出
data/校勘记录/PUA缺字清单.csv。

记号类别：
- PUA私用区：U+E000-U+F8FF 单字符
- 占位符：4位hex残码（如 B430、DA3E）、�
- 加号占位符：孤立 '+'（底本部首丢失标记，常带后续部件字，如 +奥=燠）
- 复合记号：+XXXX（'+'紧跟4位hex，如 +B144）

扫描在拉平文本上进行（行尾记号可与下一行开头组合），位置映射回 行号/列。
缺字常见形态为「记号+部件残余」，由 resolve_pua.py 按维基文库比对回填。
"""
import bisect
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = ROOT / "data/chapter"
OUT = ROOT / "data/校勘记录/PUA缺字清单.csv"

PUA = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
TOKEN = re.compile(r"\+[A-F0-9]{4}|[A-F0-9]{4}|\+|□|〓|�"
                   + "|[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def category(tok: str) -> str:
    if PUA.fullmatch(tok):
        return "PUA私用区"
    if re.fullmatch(r"\+[A-F0-9]{4}", tok):
        return "占位符[复合+hex]"
    if re.fullmatch(r"[A-F0-9]{4}", tok):
        return f"占位符[{tok}]"
    if tok == "+":
        return "加号占位符"
    if tok in ("□", "〓", "�"):
        return f"占位符[{tok}]"
    return "未知"


def main():
    rows = []
    for f in sorted(CHAPTER.glob("卷*.txt")):
        fid = f.stem.split("_")[0].replace("卷", "")
        lines = f.read_text(encoding="utf-8").split("\n")
        # 拉平（各行相接，无分隔符）并记录行起点
        starts = []
        pos = 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        flat = "".join(lines)

        for m in TOKEN.finditer(flat):
            tok = m.group(0)
            cat = category(tok)
            col_off = m.start()
            pre = flat[m.start() - 1:m.start()] if m.start() else ""
            post = flat[m.end():m.end() + 1] if m.end() < len(flat) else ""
            if PUA.fullmatch(tok):
                ok = bool(CJK.match(pre)) or bool(CJK.match(post))
            else:
                ok_pre = bool(CJK.match(pre)) or pre in "+：，"
                ok_post = bool(CJK.match(post)) or post in "，。”；、＋+"
                ok = ok_pre and ok_post
                # hex 误报排除：前后若也是 hex 字母数字则非缺字残码
                if re.fullmatch(r"\+?[A-F0-9]{4}", tok):
                    nxt = flat[m.end():m.end() + 1]
                    ok = ok and not re.match(r"[0-9A-Fa-f]", nxt)
            if not ok:
                continue
            li = bisect.bisect_right(starts, col_off) - 1
            col_in_line = col_off - starts[li]
            ctx_pre = flat[max(0, col_off - 15):col_off]
            ctx_post = flat[m.end():m.end() + 15]
            rows.append({
                "卷号": fid,
                "文件": f.name,
                "行号": li + 1,
                "列": col_in_line + 1,
                "PUA码位": f"U+{ord(tok):04X}" if PUA.fullmatch(tok) else "",
                "缺字类别": cat,
                "上下文": ctx_pre + "□" + ctx_post,
                "疑似字": "",
                "疑似字码位": "",
                "状态": "待比对",
                "依据": "",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["卷号", "文件", "行号", "列", "PUA码位",
                                           "缺字类别", "上下文", "疑似字", "疑似字码位",
                                           "状态", "依据"])
        w.writeheader()
        w.writerows(rows)
    print(f"共 {len(rows)} 条记录 → {OUT}")
    cats = {}
    for r in rows:
        key = r["PUA码位"] or r["缺字类别"]
        cats[key] = cats.get(key, 0) + 1
    for k, v in sorted(cats.items(), key=lambda x: -x[1])[:8]:
        print(k, v)
    json.dump(rows, open(ROOT / "scripts/pua_scan.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
