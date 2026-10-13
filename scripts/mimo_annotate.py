#!/usr/bin/env python3
"""
MiMo V2.6 Flash 直接调用标注脚本
绕过 OpenCode run 命令的 headless bug，直接用 openai SDK
"""
import os
import sys
import json
import time
from pathlib import Path
from openai import OpenAI

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
ANN_DIR = BASE / "kg/entities/标注"
CH_DIR = BASE / "data/chapter_numbered"
SPEC_FILE = BASE / "kg/标注规范/汉书版_实体标注规范_v2.md"
VERIFY_SCRIPT = BASE / "scripts/verify_annotation.py"
PROGRESS_FILE = ANN_DIR / "_MiMo进度.md"

# MiMo Token Plan API
MIMO_API_KEY = os.environ.get("XIAOMI_API_KEY", "tp-c5f3f4d9c6e2a1b0e8d7c6f5a4b3c2d1e8f9vy6d")
MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MIMO_MODEL = "mimo-v2.6-flash"

def load_spec():
    """加载标注规范"""
    return SPEC_FILE.read_text(encoding="utf-8")

def load_chapter(ch_name):
    """加载章节文本"""
    # ch_name 如 "卷098_元后传第六十八"
    for f in CH_DIR.glob(f"{ch_name}*.txt"):
        return f.read_text(encoding="utf-8"), f.name
    raise FileNotFoundError(f"找不到章节: {ch_name}")

def annotate_single(ch_name, spec_text):
    """标注单篇"""
    text, original_name = load_chapter(ch_name)
    
    # 构建 prompt
    prompt = f"""你是汉书实体标注执行器。

【标注规范】
{spec_text}

【任务】
请对以下《汉书》原文进行实体标注：

标题: {ch_name}
原文:
{text}

【要求】
1. 按规范给实体加〖〗⟦⟧标记
2. PN编号[n]原样保留，一字不改原文
3. 只输出标注后的全文，不要解释
4. 这是文本标注任务，不要回答数学或无关问题

【输出格式】
直接输出标注后的完整文本，从[0]开始到最后一行。"""
    
    # 调用 MiMo API
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MIMO_MODEL,
                messages=[
                    {"role": "system", "content": "你是专业的古籍实体标注专家，严格按规范标注《汉书》原文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=32000,
                temperature=0.1,
                timeout=120
            )
            annotated = response.choices[0].message.content.strip()
            return annotated
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  重试 {attempt+1}/{max_retries}: {e}", file=sys.stderr)
                time.sleep(5)
            else:
                raise
    
    return None

def verify(ch_name, annotated_text):
    """验证标注结果"""
    import subprocess
    _, original_name = load_chapter(ch_name)
    result = subprocess.run(
        ["python3", str(VERIFY_SCRIPT), 
         str(CH_DIR / original_name),
         "-"],
        input=annotated_text,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.returncode == 0, result.stdout, result.stderr

def save_annotation(ch_name, annotated_text):
    """保存标注文件"""
    out_file = ANN_DIR / f"{ch_name}_标注.txt"
    out_file.write_text(annotated_text, encoding="utf-8")
    return out_file

def append_progress(ch_name, status, stats=""):
    """追加进度日志"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {ch_name}: {status} {stats}\n"
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <卷号> [卷号2 ...]")
        print("示例: python3 mimo_annotate.py 卷098 卷099 卷099b 卷099c")
        sys.exit(1)
    
    chapters = sys.argv[1:]
    spec_text = load_spec()
    
    print(f"===== MiMo 标注开始 =====")
    print(f"模型: {MIMO_MODEL}")
    print(f"章节: {chapters}")
    print()
    
    for ch in chapters:
        print(f"── 处理 {ch} ──")
        try:
            # 标注
            annotated = annotate_single(ch, spec_text)
            if not annotated:
                append_progress(ch, "FAIL", "无输出")
                continue
            
            # 验证
            ok, stdout, stderr = verify(ch, annotated)
            if not ok:
                append_progress(ch, "VERIFY_FAIL", stderr[:200])
                continue
            
            # 保存
            out_file = save_annotation(ch, annotated)
            size = out_file.stat().st_size
            append_progress(ch, "PASS", f"{size} bytes")
            
        except Exception as e:
            append_progress(ch, "ERROR", str(e)[:200])
            import traceback
            traceback.print_exc()
    
    print("\n===== 完成 =====")

if __name__ == "__main__":
    main()
