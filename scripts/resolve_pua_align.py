#!/usr/bin/env python3
"""TASK-003 步骤3c：对剩余"待比对"缺字记号用 difflib 窗口对齐法解析。

方法：
- 在缺字记号前后取局部窗口，在维基文库简体文本中定位锚点（后文/前文唯一匹配）
- 对齐底本窗口与维基文库窗口（SequenceMatcher），底本"替换/删除"段
  （即缺字记号+部件残余+异文差异）对应的维基文库段恰为 1 字 → 回填
- 前次正则法已回填 91 条，本脚本处理其余，并把结果合并进 CSV
"""
import bisect
import csv
import subprocess
import difflib
import json
import re
import sys
import site
from pathlib import Path

sys.path.append(site.getusersitepackages())
sys.path.insert(0, str(ROOT_DIR := str(Path(__file__).resolve().parent.parent / "scripts")))
from resolve_pua import clean_ws  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = ROOT / "data/chapter"
CSV_OUT = ROOT / "data/校勘记录/PUA缺字清单.csv"
PUA = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
TOKEN = re.compile(r"\+[A-F0-9]{4}|[A-F0-9]{4}|\+"
                   + "|[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")


def ws_text_for(fid, part):
    base = fid[:3]
    cands = []
    if part and part != "b":
        cands = [f"漢書/卷{base}{part}", f"漢書/卷{base}"]
    elif part == "b":
        cands = [f"漢書/卷{base}下", f"漢書/卷{base}b", f"漢書/卷{base}"]
    else:
        cands = [f"漢書/卷{base}"]
    for title in cands:
        p = ROOT / "scripts/ws_cache" / (title.replace("/", "__") + ".txt")
        if p.exists() and p.stat().st_size > 200:
            return re.sub(r"\s+", "", clean_ws(p.read_text(encoding="utf-8")))
    return None


def align_resolve(flat, off, tok, ws_flat, win=280):
    """返回 (候选字, 依据) 或 (None, 原因)。"""
    # 1) 锚点：后文优先（吸收 0-2 个残余字），再前文
    anchor_ws = None
    trim_used = 0
    side_used = None
    for side in ("post", "pre"):
        for trim in (0, 1, 2):
            for k in (14, 10, 7, 5):
                if side == "post":
                    chunk = flat[off + len(tok) + trim:off + len(tok) + trim + k]
                else:
                    chunk = flat[off - k:off]
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
        return None, None, "无唯一锚点"
    # 2) 窗口对齐
    if side_used == "post":
        l_start, l_end = max(0, off - win), off + len(tok) + trim_used + win
        w_start, w_end = max(0, anchor_ws - win), min(len(ws_flat), anchor_ws + win)
    else:
        l_start, l_end = max(0, off - win), off + len(tok) + win
        w_start, w_end = max(0, anchor_ws - win), min(len(ws_flat), anchor_ws + win)
    local_win = flat[l_start:l_end]
    ws_win = ws_flat[w_start:w_end]
    sm = difflib.SequenceMatcher(None, local_win, ws_win, autojunk=False)
    d_in_win = off - l_start
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i1 <= d_in_win < i2:
            seg = ws_win[j1:j2]
            if tag == "equal":
                return None, None, "维基文库同缺"
            if len(seg) == 1 and (i2 - i1) <= 8:
                return seg, f"窗口对齐({tag}段,底本{i2-i1}字→维基1字)", (i1 + l_start, i2 + l_start)
            return None, None, f"对齐段{len(seg)}字不回填"
    return None, None, "对齐未覆盖缺字位置"


def main():
    # 新扫描（当前文件状态）+ 既有 CSV（保留已回填 91 条）
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts/scan_pua.py")],
                   capture_output=True, text=True)
    scan = json.load(open(ROOT / "scripts/pua_scan.json", encoding="utf-8"))
    csv_rows = list(csv.DictReader(open(CSV_OUT, encoding="utf-8-sig")))
    # CSV 中已回填的键
    done_keys = {(r["文件"], r["行号"], r["列"], r["缺字类别"]) for r in csv_rows
                 if r["状态"] == "已回填"}
    # 解析目录 part 信息
    from split_hanshu import SRC, parse_toc, file_id  # noqa
    src_lines = SRC.read_text(encoding="utf-8").split("\n")
    toc_start = next(i for i, ln in enumerate(src_lines) if ln.strip() == "卷一上 高帝纪第一上")
    body_marker = next(i for i, ln in enumerate(src_lines) if ln.strip() == "汉  书" and i > toc_start)
    units = file_id(parse_toc([ln for ln in src_lines[toc_start:body_marker] if ln.strip()]))
    part_of = {u["fid"]: u["part"] for u in units}

    resolved = 0
    unmatched = 0
    for r in scan:
        key = (r["文件"], str(r["行号"]), str(r["列"]), r["缺字类别"])
        if key in done_keys:
            continue
        fid = r["文件"].split("_")[0].replace("卷", "")
        ws_flat = ws_text_for(fid, part_of.get(fid, ""))
        if ws_flat is None:
            r["状态"], r["依据"] = "待比对", "维基文库页面缺失"
            unmatched += 1
            continue
        lines = (CHAPTER / r["文件"]).read_text(encoding="utf-8").split("\n")
        starts = []
        pos = 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        flat = "".join(lines)
        off = starts[r["行号"] - 1] + r["列"] - 1
        tok = flat[off:off + 1]
        if tok == "+":
            m = re.match(r"\+[A-F0-9]{4}|\+", flat[off:off + 6])
            tok = m.group(0) if m else "+"
        elif not PUA.fullmatch(tok):
            m = re.match(r"[A-F0-9]{4}", flat[off:off + 5])
            tok = m.group(0) if m else None
            if tok is None:
                r["状态"], r["依据"] = "待比对", "位置已变化"
                unmatched += 1
                continue
        cand, how = align_resolve(flat, off, tok, ws_flat)
        if cand and len(cand) == 1 and not PUA.match(cand):
            r["疑似字"], r["疑似字码位"] = cand, f"U+{ord(cand):04X}"
            r["状态"], r["依据"] = "已回填", how
            resolved += 1
        else:
            r["状态"], r["依据"] = "待比对", (how or "对齐失败")
            unmatched += 1

    # 应用回填
    per_file = {}
    for r in scan:
        if r["状态"] == "已回填" and "对齐" in r["依据"]:
            per_file.setdefault(r["文件"], []).append(r)
    for fname, rows in per_file.items():
        lines = (CHAPTER / fname).read_text(encoding="utf-8").split("\n")
        starts = []
        pos = 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        flat = "".join(lines)
        edits = []
        for r in rows:
            off = starts[r["行号"] - 1] + r["列"] - 1
            tok = flat[off]
            m = re.match(r"\+[A-F0-9]{4}|\+|[A-F0-9]{4}", flat[off:off + 6])
            toklen = len(m.group(0)) if m else 1
            edits.append((off, toklen, r["疑似字"]))
        for off, old_len, cand in sorted(edits, key=lambda x: -x[0]):
            flat = flat[:off] + cand + flat[off + old_len:]
        new_lines = []
        nl = len(starts)
        for i, st in enumerate(starts):
            end = starts[i + 1] if i + 1 < nl else len(flat)
            new_lines.append(flat[st:end])
        (CHAPTER / fname).write_text("\n".join(new_lines), encoding="utf-8")

    # CSV = 已回填91条(旧) + 本轮更新/新增
    final_rows = []
    new_keys = {(r["文件"], str(r["行号"]), str(r["列"]), r["缺字类别"]) for r in scan}
    for r in csv_rows:
        key = (r["文件"], r["行号"], r["列"], r["缺字类别"])
        if key in new_keys:
            continue
        final_rows.append(r)
    final_rows.extend(scan)
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["卷号", "文件", "行号", "列", "PUA码位",
                                           "缺字类别", "上下文", "疑似字", "疑似字码位",
                                           "状态", "依据"])
        w.writeheader()
        w.writerows(scan)
    print(f"\n对齐法回填 {resolved} 条，未回填 {unmatched} 条（本轮处理 {resolved+unmatched}）")
    json.dump(scan, open(ROOT / "scripts/pua_scan.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
