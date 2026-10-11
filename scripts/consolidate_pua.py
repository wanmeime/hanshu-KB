#!/usr/bin/env python3
"""TASK-003 步骤3c（整合）：以原始源文件为基准，确定性重建缺字清单并完成校勘。

流程：
1. 从 shiji-kb-reference/corpus/other/汉书.txt（未改动）按 split_report.json 的
   卷区间重建每个叙事卷的"原始文本"，扫描全部缺字记号（PUA/'+'/hex/复合）
   ——得到原始位点全集（即 data/chapter 初版状态）。
2. 与当前 data/chapter 文件逐卷 difflib 对比：已被此前回填的位点恢复出来，
   候选字=当前文件中的字。
3. 同(码位,残余序列)一致性传播：同一码位+相同后续残余在别处已确定 → 推断回填
   （依据标注"同码位同残余推断"）。
4. 其余位点：先正则上下文匹配（含残余吸收），再 difflib 窗口对齐；唯一匹配
   且候选 1 字 → 回填 data/chapter。
5. 输出完整 CSV：全部原始位点（原始行列坐标），状态=已回填/待比对/同缺待议。
   表卷（wikisource）的 {{!|X|desc}} 缺字模板也一并登记。
"""
import bisect
import csv
import difflib
import json
import re
import sys
import site
from collections import Counter
from pathlib import Path

sys.path.append(site.getusersitepackages())
sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_pua import clean_ws  # noqa: E402
from resolve_pua_align import align_resolve, ws_text_for  # noqa: E402
from split_hanshu import SRC  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = ROOT / "data/chapter"
CSV_OUT = ROOT / "data/校勘记录/PUA缺字清单.csv"

PUA = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
TOKEN = re.compile(r"\+[A-F0-9]{4}|[A-F0-9]{4}|\+|□|〓|�"
                   + "|[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

FIELDS = ["卷号", "文件", "行号", "列", "PUA码位", "缺字类别", "上下文",
          "疑似字", "疑似字码位", "状态", "依据"]


def token_category(tok):
    if PUA.fullmatch(tok):
        return "PUA私用区", f"U+{ord(tok):04X}"
    if re.fullmatch(r"\+[A-F0-9]{4}", tok):
        return "占位符[复合+hex]", ""
    if re.fullmatch(r"[A-F0-9]{4}", tok):
        return f"占位符[{tok}]", ""
    if tok == "+":
        return "加号占位符", ""
    return f"占位符[{tok}]", ""


def scan_tokens(flat):
    out = []
    for m in TOKEN.finditer(flat):
        tok = m.group(0)
        cat, code = token_category(tok)
        pre = flat[m.start() - 1:m.start()] if m.start() else ""
        post = flat[m.end():m.end() + 1] if m.end() < len(flat) else ""
        if cat == "PUA私用区":
            ok = bool(CJK.match(pre)) or bool(CJK.match(post))
        else:
            ok_pre = bool(CJK.match(pre)) or pre in "+：，"
            ok_post = bool(CJK.match(post)) or post in "，。”；、＋+"
            ok = ok_pre and ok_post
        if ok:
            out.append((m.start(), tok, cat, code))
    return out


def regex_resolve(pre, post, ws_flat, max_trim=3):
    for trim in range(0, max_trim + 1):
        for k in (12, 8, 5):
            p, q = pre[-k:], post[trim:trim + k]
            if not p or not q:
                continue
            ms = list(re.finditer(re.escape(p) + ".{0,3}" + re.escape(q), ws_flat))
            if not ms:
                continue
            if len(ms) == 1:
                m = ms[0]
                gap = ws_flat[m.start() + len(p):m.end() - len(q)]
                return gap, trim, f"唯一匹配(前{k}后{k}字,吸收残余{trim}字)"
            gaps = {ws_flat[m.start() + len(p):m.end() - len(q)] for m in ms}
            if len(gaps) == 1 and len(list(gaps)[0]) == 1:
                return list(gaps)[0], trim, f"多匹配同缺口({len(ms)}处,吸收残余{trim}字)"
    return None, None, None


def line_starts(seg):
    starts, pos = [], 0
    for ln in seg.split("\n"):
        starts.append(pos)
        pos += len(ln)
    return starts


def residual2(ctx):
    """上下文中 □ 之后紧随的至多 2 字（缺字编码的部件残余）。"""
    i = ctx.index("□") + 1
    res = ctx[i:i + 2]
    # 去掉残余里若还包含缺字记号的情况
    return TOKEN.sub("", res)


def main():
    rep = json.load(open(ROOT / "scripts/split_report.json", encoding="utf-8"))
    src_lines = SRC.read_text(encoding="utf-8").split("\n")
    table_missing = json.load(
        open(ROOT / "scripts/table_convert_report.json", encoding="utf-8"))["missing"]

    rows = []
    site_rows = {}  # (文件, off, tok) -> row（原始位点）
    for r in rep:
        if r["is_table"]:
            continue
        fname = r["file"]
        seg0 = "\n".join(ln.strip() for ln in src_lines[r["src_start"] - 1:r["src_end"]])
        seg0 = seg0.strip("\n")
        cur = (CHAPTER / fname).read_text(encoding="utf-8").rstrip("\n")
        flat0 = seg0.replace("\n", "")
        flat1 = cur.replace("\n", "")
        sites = scan_tokens(flat0)
        starts0 = line_starts(seg0)
        for off, tok, cat, code in sites:
            li = bisect.bisect_right(starts0, off) - 1
            row = {
                "卷号": r["fid"], "文件": fname, "行号": li + 1,
                "列": off - starts0[li] + 1,
                "PUA码位": code, "缺字类别": cat,
                "上下文": flat0[max(0, off - 15):off] + "□" + flat0[off + len(tok):off + len(tok) + 15],
                "疑似字": "", "疑似字码位": "", "状态": "待比对", "依据": "",
            }
            rows.append(row)
            site_rows[(fname, off, tok)] = row
        # 恢复已回填位点
        if flat0 != flat1:
            sm = difflib.SequenceMatcher(None, flat0, flat1, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal" or tag == "insert":
                    continue
                span1 = flat1[j1:j2]
                for off, tok, cat, code in sites:
                    if i1 <= off and off + len(tok) <= i2:
                        row = site_rows[(fname, off, tok)]
                        if tag == "replace" and len(span1) == 1 and not PUA.match(span1):
                            row["疑似字"] = span1
                            row["疑似字码位"] = f"U+{ord(span1):04X}"
                            row["状态"] = "已回填"
                            row["依据"] = "维基文库比对（前轮回填恢复）"
                        elif tag == "delete" and not span1:
                            row["状态"] = "待复核"
                            row["依据"] = "当前文件该位已空缺"

    # 同(码位,残余)一致性传播
    groups = {}
    for row in rows:
        key = row["PUA码位"] or row["缺字类别"]
        groups.setdefault(key, []).append(row)
    for key, group in groups.items():
        evidence = {}
        for g in group:
            if g["状态"] == "已回填":
                evidence.setdefault(residual2(g["上下文"]), set()).add(g["疑似字"])
        evidence = {k: v for k, v in evidence.items() if len(v) == 1}
        if not evidence:
            continue
        for g in group:
            if g["状态"] == "已回填":
                continue
            res = residual2(g["上下文"])
            if res in evidence:
                ch = next(iter(evidence[res]))
                g["疑似字"] = ch
                g["疑似字码位"] = f"U+{ord(ch):04X}"
                g["状态"] = "已回填"
                g["依据"] = f"同码位同残余推断（{len(group)}处中一致回填）"

    # 剩余待比对：正则 + 对齐
    unresolved = [row for row in rows if row["状态"] == "待比对"]
    part_of = {}
    from split_hanshu import parse_toc, file_id  # noqa
    toc_start = next(i for i, ln in enumerate(src_lines) if ln.strip() == "卷一上 高帝纪第一上")
    body_marker = next(i for i, ln in enumerate(src_lines) if ln.strip() == "汉  书" and i > toc_start)
    units = file_id(parse_toc([ln for ln in src_lines[toc_start:body_marker] if ln.strip()]))
    part_of = {u["fid"]: u["part"] for u in units}

    newly = 0
    by_file = {}
    for row in unresolved:
        by_file.setdefault(row["文件"], []).append(row)
    for fname, group in by_file.items():
        fid = fname.split("_")[0].replace("卷", "")
        ws_flat = ws_text_for(fid, part_of.get(fid, ""))
        if ws_flat is None:
            for row in group:
                row["依据"] = "维基文库页面缺失"
            continue
        cur = (CHAPTER / fname).read_text(encoding="utf-8").rstrip("\n")
        lines = cur.split("\n")
        starts = line_starts(cur)
        flat = cur.replace("\n", "")
        edits = []
        for row in group:
            off = starts[row["行号"] - 1] + row["列"] - 1
            # 幂等：当前文件该位仍是记号吗
            m = re.match(r"\+[A-F0-9]{4}|\+|[A-F0-9]{4}", flat[off:off + 6])
            if row["PUA码位"]:
                if not PUA.fullmatch(flat[off]):
                    row["依据"] = "位置异常跳过"
                    continue
                tok, toklen = flat[off], 1
            elif m:
                tok, toklen = m.group(0), len(m.group(0))
            else:
                row["依据"] = "位置异常跳过"
                continue
            pre = flat[off - 14:off]
            post = flat[off + toklen:off + toklen + 14]
            gap, trim, how = regex_resolve(pre, post, ws_flat)
            if gap and len(gap) == 1 and not PUA.match(gap):
                row["疑似字"], row["疑似字码位"] = gap, f"U+{ord(gap):04X}"
                row["状态"], row["依据"] = "已回填", f"维基文库比对{how}"
                edits.append((off, toklen + trim, gap))
                newly += 1
                continue
            cand, how2, span = align_resolve(flat, off, tok, ws_flat)
            if cand and len(cand) == 1 and not PUA.match(cand):
                row["疑似字"], row["疑似字码位"] = cand, f"U+{ord(cand):04X}"
                row["状态"], row["依据"] = "已回填", how2
                abs_span = (span[0] + (off - 280 if off >= 280 else 0),
                            span[1] + (off - 280 if off >= 280 else 0))
                edits.append((abs_span[0], abs_span[1] - abs_span[0], cand))
                newly += 1
                continue
            row["依据"] = how2 or "比对未中"
        if edits:
            for off, old_len, cand in sorted(edits, key=lambda x: -x[0]):
                flat = flat[:off] + cand + flat[off + old_len:]
            new_lines = []
            nl = len(starts)
            for i, st in enumerate(starts):
                end = starts[i + 1] if i + 1 < nl else len(flat)
                new_lines.append(flat[st:end])
            (CHAPTER / fname).write_text("\n".join(new_lines), encoding="utf-8")

    # 表卷缺字模板登记
    for rec in table_missing:
        ch = rec["char"][0] if rec["char"] else ""
        rows.append({
            "卷号": "", "文件": rec.get("context", ""), "行号": "", "列": "",
            "PUA码位": f"U+{ord(ch):04X}" if ch else "",
            "缺字类别": "维基文库缺字模板",
            "上下文": (rec.get("desc") or "")[:40],
            "疑似字": ch, "疑似字码位": f"U+{ord(ch):04X}" if ch else "",
            "状态": "已登记（维基文库以{{!|}}模板表示）",
            "依据": "wikitext 缺字模板，详见 scripts/table_convert_report.json",
        })

    def sort_key(row):
        try:
            return (row["卷号"], int(row["行号"]), int(row["列"]))
        except (ValueError, TypeError):
            return (row["卷号"], 99999, 0)
    rows.sort(key=sort_key)
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    stat = Counter(r["状态"] for r in rows)
    print(f"总计 {len(rows)} 条；状态分布 {dict(stat)}；本轮新回填 {newly}")


if __name__ == "__main__":
    main()
