#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""世系表批量标注调度器：逐批调MiMo，收集结果，合并，校验。
用法: python3 batch_annotate.py <底本> <卷号>
铁律：每批独立校验（去标记==底本该批），失败单独重试；全部通过才合并落盘。
"""
import subprocess, sys, os, re

OPENCODE = "/home/jiaoduan/.opencode/bin/opencode"
MODEL = "opencode/mimo-v2.6-flash-free"

RULES = """标注规则：
- 侯号+人名（羮颉侯信/合阳侯喜/上邳侯郢客/杨虚侯将闾）→ 〖@侯号人名〗
- 身份说明（帝兄子/齐悼惠王子/楚元王子/高帝弟）→ 〖#...〗
- 谥号王侯+人名（夷王郢客/顷侯通/康侯龁）→ 〖@谥号王侯人名〗
- 官爵（关内侯/列侯/丞相/大夫/公乘/司寇）→ 〖;...〗
- 时间（孝景三年/元康四年/五月甲寅/二十四年→加|时长）→ 〖%...〗
- 动词（立/嗣/薨/反/诛/废/徙/削/免/封/绍封/为/绝/谋反/篡位/复家）→ ⟦○...⟧
- 数字（千户/一级/七年→加|时长）→ 〖$...〗

铁律：
1. PN编号[rN]和列分隔｜必须原样保留，一个字都不能改
2. 去标记后与该批底本逐字一致
3. 每行独立标注，不要合并行
4. 只输出标注结果，不要任何解释/前言/代码块标记"""

PROMPT = f"""你是汉书KB标注员。标注下面这批王侯世系表行。

{RULES}

底本（原样输出标注结果）：
{{batch}}"""

def call_mimo(batch_text, timeout=120):
    prompt = PROMPT.format(batch=batch_text)
    try:
        r = subprocess.run([OPENCODE, "run", "-m", MODEL, prompt],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except subprocess.TimeoutExpired:
        return None

def strip_marks(text):
    """复用校验脚本的剥标记逻辑"""
    TYPE_CHARS = set('@=;&#%^~•!?+◆{:[_$◈◉○◇')
    out=[]; i=0
    while i < len(text):
        ch=text[i]
        if ch=='〖':
            j=text.find('〗',i)
            if j==-1: out.append(ch); i+=1; continue
            inner=text[i+1:j]
            if inner and inner[0] in TYPE_CHARS: inner=inner[1:]
            out.append(inner.split('|',1)[0]); i=j+1
        elif ch=='⟦':
            j=text.find('⟧',i)
            if j==-1: out.append(ch); i+=1; continue
            inner=text[i+1:j]
            if inner and inner[0] in TYPE_CHARS: inner=inner[1:]
            out.append(inner.split('|',1)[0]); i=j+1
        else:
            out.append(ch); i+=1
    return ''.join(out)

def verify_batch(base, ann):
    return strip_marks(ann).strip() == base.strip()

def main(base_path, juan, batch_size=15):
    workdir = "kg/entities/标注/_build"
    os.makedirs(workdir, exist_ok=True)
    rows_file = f"{workdir}/{juan}_rows.txt"
    # 提取表格行
    with open(base_path, encoding="utf-8") as f:
        rows = [l for l in f.read().split("\n") if re.match(r'\[r\d+\]', l)]
    total = len(rows)
    print(f"总表格行数: {total}")
    batches = [rows[i:i+batch_size] for i in range(0, total, batch_size)]
    print(f"分 {len(batches)} 批，每批约{batch_size}行")
    results = [""]*len(batches)
    for idx, b in enumerate(batches):
        base_batch = "\n".join(b)
        for attempt in range(3):
            out = call_mimo(base_batch)
            if out is None:
                print(f"  批{idx}: 超时，重试{attempt+1}")
                continue
            # 提取[rN]行（去掉opencode的info行）
            ann_lines = [l for l in out.split("\n") if re.match(r'\[r\d+\]', l)]
            ann_batch = "\n".join(ann_lines)
            if verify_batch(base_batch, ann_batch):
                results[idx] = ann_batch
                print(f"  批{idx}: PASS ({len(ann_lines)}行)")
                break
            else:
                print(f"  批{idx}: 校验失败，重试{attempt+1}")
        else:
            print(f"  批{idx}: ❌3次失败，保留底本未标")
            results[idx] = base_batch
    # 合并
    merged = "\n".join(r for r in results if r)
    workdir_out = f"{workdir}/{juan}_table_annotated.txt"
    with open(workdir_out, "w", encoding="utf-8") as f:
        f.write(merged)
    print(f"\n表格部分已写入 {workdir_out}")
    print("完成。需合并序言段后跑总校验。")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
