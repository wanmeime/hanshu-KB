#!/usr/bin/env python3
"""TASK-003 步骤3（最终版）：缺字校勘——从原始源重建叙事卷 + 整簇解析回填。

背景教训：缺字在底本中的形态是「一个或多个记号(+/PUA/hex) + 部件残余字」
（如 获+[虫PUA]交 = 获駮、+钅句 = 钩、[目PUA]末 = 眜）。分轮处理曾把簇内
记号各自替换导致重复插入。本脚本一趟完成：

1. 用未改动的原始源重建全部 110 个叙事卷文件（撤销历史所有部分回填）
2. 扫描缺字记号、把直接相邻的记号合并为"簇"（簇=一个缺字）
3. 解析（候选=1 真字才回填）：
   a. 正则上下文匹配（上下文先剔除缺字记号；吸收簇后 0-3 个残余字）
   b. difflib 窗口对齐（锚点同样吸收残余）
   c. 同(码位,簇后首字)证据传播：提出候选后须再用正则验证唯一匹配
4. 写回：文件 = 原始正文 + 证据充分的单字替换；未解析位点保留原始记号
5. 输出 data/校勘记录/PUA缺字清单.csv（原始坐标，全量位点）
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
from resolve_pua_align import ws_text_for  # noqa: E402
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


def make_clusters(sites):
    clusters = []
    for off, tok, cat, code in sites:
        if clusters and clusters[-1][1] == off:
            s, e, toks = clusters[-1]
            clusters[-1] = (s, off + len(tok), toks + tok)
        else:
            clusters.append((off, off + len(tok), tok))
    return clusters


def unique_ws_match(p, q, ws_flat, gap_pat=".{0,3}"):
    """唯一匹配时返回 gap。"""
    ms = list(re.finditer(re.escape(p) + gap_pat + re.escape(q), ws_flat))
    if not ms:
        return None
    if len(ms) == 1:
        m = ms[0]
        return ws_flat[m.start() + len(p):m.end() - len(q)]
    gaps = {ws_flat[m.start() + len(p):m.end() - len(q)] for m in ms}
    if len(gaps) == 1:
        return list(gaps)[0]
    return None


def regex_resolve_cluster(pre, post, ws_flat, max_trim=3):
    pre = TOKEN.sub("", pre)
    for trim in range(0, max_trim + 1):
        q = TOKEN.sub("", post[trim:trim + 12])
        if len(q) < 4:
            continue
        for k in (12, 8, 5):
            p, qq = pre[-k:], q[:k]
            if len(p) < 4:
                continue
            gap = unique_ws_match(p, qq, ws_flat)
            if gap:
                return gap, trim, f"唯一匹配(前{k}后{k}字,吸收残余{trim}字)"
    return None, None, None


def align_resolve_cluster(flat, cs, ce, ws_flat, win=280):
    """窗口对齐：返回 (候选字, 替换跨度, 依据, 失败原因)。"""
    anchor_ws = None
    trim_used = 0
    side_used = None
    for side in ("post", "pre"):
        for trim in (0, 1, 2):
            for k in (14, 10, 7, 5):
                if side == "post":
                    chunk = flat[ce + trim:ce + trim + k]
                else:
                    chunk = flat[max(0, cs - k):cs]
                chunk = TOKEN.sub("", chunk)
                if len(chunk) < 4:
                    continue
                ms = list(re.finditer(re.escape(chunk), ws_flat))
                if len(ms) == 1:
                    anchor_ws = ms[0].start() if side == "post" else ms[0].end()
                    trim_used = trim
                    side_used = side
                    break
            if anchor_ws is not None:
                break
        if anchor_ws is not None:
            break
    if anchor_ws is None:
        return None, None, None, "无唯一锚点"
    l_start = max(0, cs - win)
    l_end = ce + (trim_used if side_used == "post" else 0) + win
    w_start = max(0, anchor_ws - win)
    w_end = min(len(ws_flat), anchor_ws + win)
    local_win = flat[l_start:l_end]
    ws_win = ws_flat[w_start:w_end]
    sm = difflib.SequenceMatcher(None, local_win, ws_win, autojunk=False)
    d = cs - l_start
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i1 <= d < i2:
            seg = ws_win[j1:j2]
            if tag == "equal":
                return None, None, None, "维基文库同缺"
            if len(seg) == 1 and (i2 - i1) <= 8:
                return seg, (i1 + l_start, i2 + l_start), \
                    f"窗口对齐({tag}段,底本{i2-i1}字→维基1字)", None
            return None, None, None, f"对齐段{len(seg)}字不回填"
    return None, None, None, "对齐未覆盖缺字位置"


def verify_proposal(flat0, cs, ce, cand, ws_flat):
    """验证候选字：pre + cand + (簇后 0..2 字被吸收) 能唯一匹配。"""
    pre = TOKEN.sub("", flat0[max(0, cs - 10):cs])[-8:]
    if len(pre) < 4:
        return False
    for skip in (0, 1, 2):
        q = TOKEN.sub("", flat0[ce + skip:ce + skip + 8])
        if len(q) < 4:
            continue
        gap = unique_ws_match(pre + cand, q, ws_flat, gap_pat="")
        if gap == "":
            return True
    return False


def _align_segment_text(flat, cs, ce, ws_flat, win=280):
    """复跑窗口对齐，返回覆盖簇位的维基文库段文本（任意长度）。"""
    anchor_ws = None
    trim_used = 0
    side_used = None
    for side in ("post", "pre"):
        for trim in (0, 1, 2):
            for k in (14, 10, 7, 5):
                chunk = (flat[ce + trim:ce + trim + k] if side == "post"
                         else flat[max(0, cs - k):cs])
                chunk = TOKEN.sub("", chunk)
                if len(chunk) < 4:
                    continue
                ms = list(re.finditer(re.escape(chunk), ws_flat))
                if len(ms) == 1:
                    anchor_ws = ms[0].start() if side == "post" else ms[0].end()
                    trim_used = trim
                    side_used = side
                    break
            if anchor_ws is not None:
                break
        if anchor_ws is not None:
            break
    if anchor_ws is None:
        return None
    l_start = max(0, cs - win)
    l_end = ce + (trim_used if side_used == "post" else 0) + win
    w_start = max(0, anchor_ws - win)
    w_end = min(len(ws_flat), anchor_ws + win)
    sm = difflib.SequenceMatcher(None, flat[l_start:l_end], ws_flat[w_start:w_end],
                                 autojunk=False)
    d = cs - l_start
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i1 <= d < i2:
            return ws_flat[w_start:w_end][j1:j2]
    return None


def main():
    rep = json.load(open(ROOT / "scripts/split_report.json", encoding="utf-8"))
    src_lines = SRC.read_text(encoding="utf-8").split("\n")
    table_missing = json.load(
        open(ROOT / "scripts/table_convert_report.json", encoding="utf-8"))["missing"]

    from split_hanshu import parse_toc, file_id  # noqa
    toc_start = next(i for i, ln in enumerate(src_lines) if ln.strip() == "卷一上 高帝纪第一上")
    body_marker = next(i for i, ln in enumerate(src_lines) if ln.strip() == "汉  书" and i > toc_start)
    units = file_id(parse_toc([ln for ln in src_lines[toc_start:body_marker] if ln.strip()]))
    part_of = {u["fid"]: u["part"] for u in units}

    rows = []
    for r in rep:
        if r["is_table"]:
            continue
        fname = r["file"]
        seg0 = "\n".join(ln.strip() for ln in src_lines[r["src_start"] - 1:r["src_end"]])
        seg0 = seg0.strip("\n")
        flat0 = seg0.replace("\n", "")
        starts0 = []
        pos = 0
        for ln in seg0.split("\n"):
            starts0.append(pos)
            pos += len(ln)
        orig_lines = seg0.split("\n")

        sites = scan_tokens(flat0)
        clusters = make_clusters(sites)
        # 重建为原始状态
        (CHAPTER / fname).write_text(seg0 + "\n", encoding="utf-8")
        if not clusters:
            continue

        fid = r["fid"]
        ws_flat = ws_text_for(fid, part_of.get(fid, ""))
        decisions = []  # (cs, ce, cand, basis, row)
        for cs, ce, toks in clusters:
            cat, code = token_category(toks) if len(toks) == 1 else ("缺字记号簇", "")
            li = bisect.bisect_right(starts0, cs) - 1
            row = {
                "卷号": fid, "文件": fname, "行号": li + 1, "列": cs - starts0[li] + 1,
                "PUA码位": code, "缺字类别": cat,
                "上下文": flat0[max(0, cs - 15):cs] + "□" + flat0[ce:ce + 15],
                "疑似字": "", "疑似字码位": "", "状态": "待比对", "依据": "",
            }
            rows.append(row)
            if ws_flat is None:
                row["依据"] = "维基文库页面缺失"
                continue
            pre = flat0[max(0, cs - 14):cs]
            post = flat0[ce:ce + 14]
            gap, trim, how = regex_resolve_cluster(pre, post, ws_flat)
            if gap and len(gap) == 1 and not PUA.match(gap):
                row["疑似字"], row["疑似字码位"] = gap, f"U+{ord(gap):04X}"
                row["状态"], row["依据"] = "已回填", "维基文库比对" + how
                decisions.append((cs, ce + trim, gap, how, row))
                continue
            cand, span, how2, reason = align_resolve_cluster(flat0, cs, ce, ws_flat)
            if cand:
                row["疑似字"], row["疑似字码位"] = cand, f"U+{ord(cand):04X}"
                row["状态"], row["依据"] = "已回填", "维基文库比对" + how2
                decisions.append((span[0], span[1], cand, how2, row))
                continue
            # 对齐段 2-3 字：取段首字作提案，用正则验证后回填
            if reason and reason.startswith("对齐段") and cand is None and reason != "无唯一锚点":
                pass
            # 复跑一次对齐拿段内容（align_resolve 只回传单字段，这里用窗口重算）
            seg_txt = _align_segment_text(flat0, cs, ce, ws_flat)
            proposals = []
            if seg_txt:
                proposals.append(seg_txt[0])
            for prop in proposals:
                if not PUA.match(prop) and CJK.match(prop) and \
                        verify_proposal(flat0, cs, ce, prop, ws_flat):
                    skip = 0
                    pre2 = TOKEN.sub("", flat0[max(0, cs - 10):cs])[-8:]
                    for sk in (0, 1, 2):
                        q2 = TOKEN.sub("", flat0[ce + sk:ce + sk + 8])
                        if len(q2) >= 4 and unique_ws_match(pre2 + prop, q2, ws_flat, "") == "":
                            skip = sk
                            break
                    row["疑似字"], row["疑似字码位"] = prop, f"U+{ord(prop):04X}"
                    row["状态"], row["依据"] = "已回填", f"对齐提案+验证(吸收残余{skip}字)"
                    decisions.append((cs, ce + skip, prop, row["依据"], row))
                    break
                break
            else:
                row["依据"] = reason or "比对未中"
                continue
            row["依据"] = reason or "比对未中"

        # 二轮：同(码位,簇后首字)证据传播 + 正则验证
        key_map = {}
        for cs, ce, toks in clusters:
            li = bisect.bisect_right(starts0, cs) - 1
            row = next(x for x in rows if x["文件"] == fname
                       and x["行号"] == li + 1 and x["列"] == cs - starts0[li] + 1)
            nxt = flat0[ce:ce + 1]
            k = (row["PUA码位"] or row["缺字类别"], nxt)
            key_map.setdefault(k, []).append((cs, ce, row))
        for k, group in key_map.items():
            filled = [row["疑似字"] for _cs, _ce, row in group
                      if row["状态"] == "已回填"]
            if not filled:
                continue
            if len(set(filled)) != 1:
                continue
            cand = filled[0]
            for cs, ce, row in group:
                if row["状态"] == "已回填":
                    continue
                if verify_proposal(flat0, cs, ce, cand, ws_flat):
                    # 确定吸收长度：与已回填处的残余一致（用最小可行 skip）
                    skip = 0
                    for s in (0, 1, 2):
                        q = TOKEN.sub("", flat0[ce + s:ce + s + 8])
                        pre = TOKEN.sub("", flat0[max(0, cs - 10):cs])[-8:]
                        if len(q) >= 4 and unique_ws_match(pre + cand, q, ws_flat, "") == "":
                            skip = s
                            break
                    row["疑似字"], row["疑似字码位"] = cand, f"U+{ord(cand):04X}"
                    row["状态"] = "已回填"
                    row["依据"] = f"同码位同残余推断+验证（{len(group)}处中一致）"
                    decisions.append((cs, ce + skip, cand, row["依据"], row))

        # 写回
        flat1 = flat0
        for cs, ce, cand, _b, _r in sorted(decisions, key=lambda d: -d[0]):
            flat1 = flat1[:cs] + cand + flat1[ce:]
        line_bounds = []
        p = 0
        for ln in orig_lines:
            line_bounds.append((p, p + len(ln)))
            p += len(ln)
        out_lines = []
        delta = 0
        for ls, le in line_bounds:
            out_lines.append(flat1[ls + delta:le + delta])
            delta += len(flat1[ls + delta:le + delta]) - (le - ls)
        (CHAPTER / fname).write_text("\n".join(out_lines) + "\n", encoding="utf-8")

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

    rows.sort(key=lambda x: (x["卷号"],
                             int(x["行号"]) if str(x["行号"]).isdigit() else 99999,
                             int(x["列"]) if str(x["列"]).isdigit() else 0))
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    stat = Counter(r["状态"] for r in rows)
    print(f"总计 {len(rows)} 条；状态分布 {dict(stat)}")


if __name__ == "__main__":
    main()
