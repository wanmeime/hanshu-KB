#!/usr/bin/env python3
"""TASK-003 步骤2：把 data/raw/hanshu_tables/ 的维基文库 wikitext 转成
data/chapter/ 卷013—卷020（10 个分卷文件）的简体纯正文。

处理规则：
- 删除页头注释块、{{header}}/{{footer}}/{{reflist}} 等页面装饰模板（括号平衡扫描）
- {{*|...}} 注（师古曰/应劭曰等）删除；<ref>...</ref> 删除
- {{!|X|描述}} 缺字模板 → 保留显示字 X，并登记缺字记录
- {{YL|X|...}} 年号链接 → X
- [[a|b]]→b；-{x}-→x；'''粗体'''→x；<p> 等标签删除；__TOC__ 等魔术字删除
- ==/=== 维基文库编辑标题删除（卷019 按原 ==年表== 分界拆分上/下）
- wikitable 行 → 单元格以全角"｜"连接（空单元格保留为空串，保住列位）
- 全文 opencc t2s 转简体，再归一异体字（髙→高、戸→户、臯→皋）
"""
import json
import re
import sys
import site
import unicodedata
from pathlib import Path

sys.path.append(site.getusersitepackages())
import opencc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TBL = ROOT / "data/raw/hanshu_tables"
OUT = ROOT / "data/chapter"

cc = opencc.OpenCC("t2s")
VARIANT_MAP = {"髙": "高", "戸": "户", "臯": "皋"}

missing_log = []  # 缺字模板记录（{{!|X|desc}}）

FURNITURE = ("header", "footer", "reflist", "alsosee", "PD-", "displaytitle",
             "DEFAULTSORT", "Otheruses", "notewiki")


def skip_balanced(text, i):
    """从 text[i:] 的 '{{' 起，返回平衡模板块的结束位置（'}}' 之后）。"""
    depth = 0
    j = i
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


def remove_furniture(text):
    """删除页面装饰模板块与魔术字。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("{{", i):
            name = text[i + 2:i + 14]
            if name.startswith(FURNITURE) or name.split("|")[0].strip().startswith(FURNITURE):
                i = skip_balanced(text, i)
                continue
        out.append(text[i])
        i += 1
    t = "".join(out)
    t = re.sub(r"__[A-Z]+__", "", t)
    return t


def process_templates(text, ctx):
    """扫描所有 {{...}}：{{*|..}}→删、{{!|X|d}}→X(登记)、{{YL|X|..}}→X、其余→删。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("{{", i):
            j = skip_balanced(text, i)
            block = text[i:j]
            inner = block[2:-2]
            if inner.startswith("*"):
                pass  # 注，删除
            elif inner.startswith("!"):
                parts = inner.split("|")
                ch = parts[1] if len(parts) > 1 else ""
                desc = parts[2] if len(parts) > 2 else ""
                if ch:
                    missing_log.append({"char": ch, "desc": desc, "context": ctx})
                out.append(ch)
            else:
                name = inner.split("|")[0].strip()
                if name == "YL":
                    parts = inner.split("|")
                    out.append(parts[1] if len(parts) > 1 else "")
                # 其余模板一律删除
            i = j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def clean_markup(text: str) -> str:
    """处理 <ref>/链接/-{}/粗体/剩余标签。"""
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    for _ in range(10):
        text, n = re.subn(r"\[\[[^\[\]|]*\|([^\[\]]*)\]\]", r"\1", text)
        text = re.sub(r"\[\[([^\[\]|]*)\]\]", r"\1", text)
        if not n:
            break
    text = re.sub(r"-\{([^{}]*)\}-", lambda m: m.group(1).split("|")[-1].split(":")[-1], text)
    text = re.sub(r"-\{|\}-", "", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"</?[A-Za-z][^>]*/?>", "", text)
    return text


def parse_wikitable(lines, i):
    """解析 {| ... |} 表格 → 行列表（单元格列表）。返回 (rows, next_i)。"""
    i += 1
    rows = []
    cur = None
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("|}"):
            if cur:
                rows.append(cur)
            return rows, i + 1
        if s.startswith("|-"):
            if cur:
                rows.append(cur)
            cur = []
            i += 1
            continue
        if s.startswith("|+"):
            if cur:
                rows.append(cur)
                cur = None
            rows.append([clean_inline(s[2:])])
            i += 1
            continue
        if s.startswith("!") or s.startswith("|"):
            mark = "!" if s.startswith("!") else "|"
            body = s[1:]
            cells = re.split(r"!!" if mark == "!" else r"\|\|", body)
            for c in cells:
                if cur is None:
                    cur = []
                # 扩展语法：| 属性="…" 或 属性=N … | 内容 → 取内容
                m2 = re.match(r'^\s*(?:[A-Za-z-]+=(?:"[^"]*"|[A-Za-z0-9.%;-]+)\s*)+\|\s*(.*)$', c, flags=re.S)
                if m2:
                    c = m2.group(1)
                cur.append(clean_inline_markup(c).replace("　", "").strip())
            i += 1
            continue
        if cur and s:
            cur[-1] += s
        i += 1
    if cur:
        rows.append(cur)
    return rows, i


def convert(text: str, label: str):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = remove_furniture(text)
    text = process_templates(text, label)
    text = clean_markup(text)
    lines = text.split("\n")
    out_lines = []
    i = 0
    n = len(lines)
    table_rows_total = 0
    while i < n:
        s = lines[i].strip()
        if s.startswith("{|"):
            rows, i = parse_wikitable(lines, i)
            table_rows_total += len(rows)
            for r in rows:
                out_lines.append("｜".join(r))
            continue
        if s.startswith("=="):
            i += 1
            continue
        cleaned = clean_inline_markup(s)
        if cleaned:
            out_lines.append(cleaned)
        i += 1
    body = "\n".join(out_lines)
    body = cc.convert(body)
    for k, v in VARIANT_MAP.items():
        body = body.replace(k, v)
    return body, table_rows_total


def clean_inline_markup(s: str) -> str:
    s = re.sub(r"</?[A-Za-z][^>]*/?>", "", s)
    return s.strip()


def main():
    plan = [
        ("卷013_异姓诸侯王表第一.txt", "卷013_异姓诸侯王表第一.txt", None),
        ("卷014_诸侯王表第二.txt", "卷014_诸侯王表第二.txt", None),
        ("卷015_王子侯表第三上.txt", "卷015_王子侯表第三上.txt", None),
        ("卷015b_王子侯表第三下.txt", "卷015b_王子侯表第三下.txt", None),
        ("卷016_高惠高后文功臣表第四.txt", "卷016_高惠高后文功臣表第四.txt", None),
        ("卷017_景武昭宣元成功臣表第五.txt", "卷017_景武昭宣元成功臣表第五.txt", None),
        ("卷018_外戚恩泽侯表第六.txt", "卷018_外戚恩泽侯表第六.txt", None),
        ("卷019_百官公卿表第七上.txt", "卷019_百官公卿表第七上下.txt", "pre"),
        ("卷019b_百官公卿表第七下.txt", "卷019_百官公卿表第七上下.txt", "post"),
        ("卷020_古今人表第八.txt", "卷020_古今人表第八.txt", None),
    ]
    results = []
    for out_name, src_name, mode in plan:
        raw = (TBL / src_name).read_text(encoding="utf-8")
        n_before = len(missing_log)
        if mode is None:
            body, nrows = convert(raw, out_name)
        else:
            lines = raw.split("\n")
            split_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "==年表==")
            part_raw = "\n".join(lines[:split_idx]) if mode == "pre" else "\n".join(lines[split_idx:])
            body, nrows = convert(part_raw, out_name)
        (OUT / out_name).write_text(body + "\n", encoding="utf-8")
        delta = len(missing_log) - n_before
        results.append({"file": out_name, "rows": nrows,
                        "chars": len(body.replace("\n", "")), "missing_templates": delta})
        print(f"{out_name}: {len(body.replace(chr(10),''))} 字符, 表行 {nrows}, 缺字模板 {delta}")
    # 缺字模板记录去重（同文件同字同描述合并）
    seen = set()
    deduped = []
    for rec in missing_log:
        k = (rec["context"], rec["char"], rec["desc"])
        if k not in seen:
            seen.add(k)
            deduped.append(rec)
    json.dump({"results": results, "missing": deduped},
              open(ROOT / "scripts/table_convert_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
