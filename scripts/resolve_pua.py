#!/usr/bin/env python3
"""TASK-003 步骤3b：用维基文库（zh.wikisource.org）对 data/chapter/ 中的
缺字记号逐一比对，唯一匹配则回填原字，并更新
data/校勘记录/PUA缺字清单.csv。

底本缺字形态说明（实测）：
- 常见为「记号+部件残余」：PUA/'+'后跟部件字，如 [虫PUA]分=蚡、+奥=燠、
  +阝=右耳旁；比对时尝试吸收 0-2 个残余字（trim），缺口=维基文库单字才回填
- hex 残码（B430、DA3E 等）通常无残余字（trim=0）

比对方法：
- 卷号映射维基文库页面（ redirects=1 解析重定向；缺失则回退合卷页）
- wikitext 原文 → 清理注/模板/标记 → opencc t2s 简体
- 缺字前后文（默认12字）唯一匹配、缺口恰 1 字 → 回填
- 幂等保护：回填前校验原位置仍是原记号
"""
import bisect
import csv
import json
import re
import subprocess
import sys
import site
import time
import urllib.parse
from pathlib import Path

sys.path.append(site.getusersitepackages())
import opencc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = ROOT / "data/chapter"
CACHE = ROOT / "scripts/ws_cache"
CSV_OUT = ROOT / "data/校勘记录/PUA缺字清单.csv"

cc = opencc.OpenCC("t2s")
VARIANT_MAP = {"髙": "高", "戸": "户", "臯": "皋"}
PUA = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")


def token_of(r):
    cat = r["缺字类别"]
    if cat == "PUA私用区":
        return chr(int(r["PUA码位"][2:], 16))
    if cat.startswith("占位符[") and cat != "占位符[复合+hex]":
        return cat[len("占位符["):-1]
    if cat == "占位符[复合+hex]":
        return "+" + r["上下文"]  # 不可靠，由调用方重扫
    if cat == "加号占位符":
        return "+"
    return None


def fetch(url, tries=4):
    for t in range(tries):
        raw = subprocess.run(["curl", "-s", "--max-time", "40", url],
                             capture_output=True, text=True).stdout
        if raw.strip().startswith("{"):
            try:
                return json.loads(raw)
            except Exception:
                pass
        time.sleep(1.5)
    return None


def ws_content(fids_title_candidates) -> str | None:
    CACHE.mkdir(exist_ok=True)
    for title in fids_title_candidates:
        cache_file = CACHE / (title.replace("/", "__") + ".txt")
        if cache_file.exists() and cache_file.stat().st_size > 200:
            return cache_file.read_text(encoding="utf-8")
        if cache_file.exists():
            cache_file.unlink()
        url = ("https://zh.wikisource.org/w/api.php?action=query&redirects=1&titles="
               + urllib.parse.quote(title, safe="")
               + "&prop=revisions&rvprop=content&rvslots=main&format=json")
        out = fetch(url)
        text = None
        if out and "query" in out:
            for p in out["query"]["pages"].values():
                if "missing" not in p and "revisions" in p:
                    text = p["revisions"][0]["slots"]["main"]["*"]
        if text and "#REDIRECT" not in text[:60]:
            cache_file.write_text(text, encoding="utf-8")
            time.sleep(0.4)
            return text
        time.sleep(0.4)
    return None


def skip_balanced(text, i):
    depth, j = 0, i
    while j < len(text):
        if text.startswith("{{", j):
            depth += 1
            j += 2
            continue
        if text.startswith("}}", j):
            depth -= 1
            j += 2
            if depth == 0:
                return j
            continue
        j += 1
    return len(text)


LAYOUT_HEADS = ("{{blue|", "{{left|", "{{right|", "{{center|", "{{小字|")


def unwrap_layout_templates(text: str) -> str:
    """{{blue|...}} 等排版模板只留内容（内层可能再嵌套，循环到无）。"""
    changed = True
    guard = 0
    while changed and guard < 500:
        changed = False
        guard += 1
        for head in LAYOUT_HEADS:
            i = text.find(head)
            if i == -1:
                continue
            j = skip_balanced(text, i)
            inner = text[i + len(head):j - 2]
            text = text[:i] + inner + text[j:]
            changed = True
            break
    return text


def clean_ws(raw: str) -> str:
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = unwrap_layout_templates(raw)
    raw = re.sub(r"__[A-Z]+__", "", raw)
    out, i = [], 0
    while i < len(raw):
        if raw.startswith("{{", i):
            name = raw[i + 2:i + 14]
            if name.startswith(("header", "footer", "reflist", "PD-", "displaytitle",
                                "DEFAULTSORT", "Otheruses", "notewiki", "pages",
                                "PageQuality", "署名")):
                i = skip_balanced(raw, i)
                continue
        out.append(raw[i])
        i += 1
    raw = "".join(out)
    out, i = [], 0
    while i < len(raw):
        if raw.startswith("{{", i):
            j = skip_balanced(raw, i)
            inner = raw[i + 2:j - 2]
            if inner.startswith("!"):
                parts = inner.split("|")
                out.append(parts[1] if len(parts) > 1 else "")
            elif inner.split("|")[0].strip() == "YL":
                parts = inner.split("|")
                out.append(parts[1] if len(parts) > 1 else "")
            i = j
            continue
        out.append(raw[i])
        i += 1
    raw = "".join(out)
    raw = re.sub(r"<ref[^>]*/>", "", raw)
    raw = re.sub(r"<ref[^>]*>.*?</ref>", "", raw, flags=re.S)
    for _ in range(10):
        raw, n = re.subn(r"\[\[[^\[\]|]*\|([^\[\]]*)\]\]", r"\1", raw)
        raw = re.sub(r"\[\[([^\[\]|]*)\]\]", r"\1", raw)
        if not n:
            break
    raw = re.sub(r"-\{([^{}]*)\}-", lambda m: m.group(1).split("|")[-1].split(":")[-1], raw)
    raw = re.sub(r"-\{|\}-", "", raw)
    raw = raw.replace("'''", "").replace("''", "")
    raw = re.sub(r"</?[A-Za-z][^>]*/?>", "", raw)
    raw = "\n".join(ln for ln in raw.split("\n") if not ln.strip().startswith("=="))
    # opencc 会把生僻字误转（如 𨻻→啮），扩展区字符先用哨兵保护
    astral = re.compile(r"[\U00020000-\U0003FFFF\u3400-\u4dbf]")
    sentinels = {}
    def _prot(m):
        ch = m.group(0)
        key = "\x00" + hex(len(sentinels)) + "\x00"
        sentinels[key] = ch
        return key
    protected = astral.sub(_prot, raw)
    text = cc.convert(protected)
    for key, ch in sentinels.items():
        text = text.replace(key, ch)
    for k, v in VARIANT_MAP.items():
        text = text.replace(k, v)
    return text


def resolve_occurrence(pre: str, post: str, ws_flat: str, max_trim=2):
    """尝试 trim 0..max_trim（吸收残余字）× 上下文长度 12/8/5。
    返回 (候选字, trim, 说明) 或 (None, None, 原因)。"""
    for trim in range(0, max_trim + 1):
        for k in (12, 8, 5):
            p, q = pre[-k:], post[trim:trim + k]
            if not p or not q:
                continue
            pat = re.escape(p) + ".{0,3}" + re.escape(q)
            ms = list(re.finditer(pat, ws_flat))
            if not ms:
                continue
            if len(ms) == 1:
                m = ms[0]
                gap = ws_flat[m.start() + len(p):m.end() - len(q)]
                return gap, trim, f"唯一匹配(前{k}后{k}字,吸收残余{trim}字)"
            gaps = {ws_flat[m.start() + len(p):m.end() - len(q)] for m in ms}
            if len(gaps) == 1 and len(list(gaps)[0]) == 1:
                return list(gaps)[0], trim, f"多匹配同缺口({len(ms)}处,吸收残余{trim}字)"
    return None, None, "上下文无匹配"


def main():
    scan = json.load(open(ROOT / "scripts/pua_scan.json", encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from split_hanshu import SRC, parse_toc, file_id  # noqa
    src_lines = SRC.read_text(encoding="utf-8").split("\n")
    toc_start = next(i for i, ln in enumerate(src_lines) if ln.strip() == "卷一上 高帝纪第一上")
    body_marker = next(i for i, ln in enumerate(src_lines) if ln.strip() == "汉  书" and i > toc_start)
    units = file_id(parse_toc([ln for ln in src_lines[toc_start:body_marker] if ln.strip()]))
    part_of = {u["fid"]: u["part"] for u in units}

    by_file = {}
    for r in scan:
        by_file.setdefault(r["文件"], []).append(r)

    resolved = 0
    unmatched = 0
    for fname, occs in sorted(by_file.items()):
        fid = fname.split("_")[0].replace("卷", "")
        part = part_of.get(fid, "")
        base = fid[:3]
        cands = []
        if part and part not in ("b",):
            cands = [f"漢書/卷{base}{part}", f"漢書/卷{base}"]
        elif part == "b":
            cands = [f"漢書/卷{base}下", f"漢書/卷{base}b", f"漢書/卷{base}"]
        else:
            cands = [f"漢書/卷{base}"]
        ws_raw = ws_content(cands)
        if ws_raw is None:
            for r in occs:
                r["状态"], r["依据"] = "待比对", f"维基文库页面缺失({cands[0]})"
            unmatched += len(occs)
            print(f"{fname}: 页面缺失 {cands[0]}，{len(occs)} 条待比对")
            continue
        ws_flat = re.sub(r"\s+", "", clean_ws(ws_raw))
        lines = (CHAPTER / fname).read_text(encoding="utf-8").split("\n")
        starts = []
        pos = 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        flat = "".join(lines)

        filled = 0
        for r in occs:
            # 当前位置的记号（从文件现状取，幂等保护）
            off = starts[r["行号"] - 1] + r["列"] - 1
            cur = flat[off:off + 6]
            if r["PUA码位"]:
                want = chr(int(r["PUA码位"][2:], 16))
                tok = cur[0] if cur and PUA.fullmatch(cur[0]) else None
                if tok != want:
                    continue  # 位置已变化（此前已回填），跳过
            else:
                tok = None
                if cur[:1] == "+":
                    m = re.match(r"\+[A-F0-9]{4}|\+", cur)
                    tok = m.group(0) if m else None
                if tok is None:
                    m = re.match(r"[A-F0-9]{4}", cur)
                    tok = m.group(0) if m else None
                if tok is None:
                    continue  # 位置已变化
            pre = flat[off - 12:off]
            post = flat[off + len(tok):off + len(tok) + 14]
            gap, trim, how = resolve_occurrence(pre, post, ws_flat)
            if gap and len(gap) == 1 and not PUA.match(gap):
                r["疑似字"], r["疑似字码位"] = gap, f"U+{ord(gap):04X}"
                r["状态"], r["依据"] = "已回填", f"维基文库比对{how}"
                r["_replace"] = (off, len(tok) + trim, gap)
                resolved += 1
                filled += 1
            elif gap:
                r["疑似字"], r["疑似字码位"] = gap, "、".join(f"U+{ord(c):04X}" for c in gap)
                r["状态"], r["依据"] = "待比对", f"维基文库比对{how}，缺口{len(gap)}字不回填"
                unmatched += 1
            else:
                r["状态"], r["依据"] = "待比对", f"维基文库比对无匹配({cands[0]})"
                unmatched += 1
        if filled:
            print(f"{fname}: 回填 {filled} 条")
    # 写回文件：按每行替换
    # （在上循环内已收集 edits，此处统一按文件写回）
    per_file_edits = {}
    for fname, occs in by_file.items():
        for r in occs:
            if "_replace" in r:
                per_file_edits.setdefault(fname, []).append(r["_replace"])
    for fname, edits in per_file_edits.items():
        lines = (CHAPTER / fname).read_text(encoding="utf-8").split("\n")
        starts = []
        pos = 0
        for ln in lines:
            starts.append(pos)
            pos += len(ln)
        flat = "".join(lines)
        for off, old_len, cand in sorted(edits, key=lambda x: -x[0]):
            flat = flat[:off] + cand + flat[off + old_len:]
        new_lines = []
        prev = 0
        n_lines = len(starts)
        for i, st in enumerate(starts):
            end = starts[i + 1] if i + 1 < n_lines else len(flat)
            new_lines.append(flat[st:end])
        (CHAPTER / fname).write_text("\n".join(new_lines), encoding="utf-8")

    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["卷号", "文件", "行号", "列", "PUA码位",
                                           "缺字类别", "上下文", "疑似字", "疑似字码位",
                                           "状态", "依据"])
        w.writeheader()
        for r in scan:
            r.pop("_replace", None)
        w.writerows(scan)
    print(f"\n回填 {resolved} 条，未回填 {unmatched} 条，总计 {len(scan)} 条 → CSV 已更新")


if __name__ == "__main__":
    main()
