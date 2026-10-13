#!/usr/bin/env python3
"""
汉书实体标注脚本 - 使用 OpenRouter DeepSeek V4 Flash
绕过 OpenCode headless bug
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from openai import OpenAI

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
ANN_DIR = BASE / "kg/entities/标注"
CH_DIR = BASE / "data/chapter_numbered"
SPEC_FILE = BASE / "kg/标注规范/汉书版_实体标注规范_v2.md"
VERIFY_SCRIPT = BASE / "scripts/verify_annotation.py"
PROGRESS_FILE = ANN_DIR / "_MiMo进度.md"

# OpenRouter DeepSeek V4 Flash
# 从 .env 读 key（环境变量可能没传进来）
_env = {}
for _line in open("/home/jiaoduan/.hermes/.env"):
    _line = _line.strip()
    if "=" in _line and not _line.startswith("#"):
        _k, _v = _line.split("=", 1)
        _env[_k.strip()] = _v.strip().strip('"')

OR_KEY = _env.get("OPENROUTER_API_KEY", "")
OR_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-chat"  # 便宜且快

def load_spec():
    return SPEC_FILE.read_text(encoding="utf-8")

def load_chapter(ch_name):
    for f in sorted(CH_DIR.glob(f"{ch_name}*.txt")):
        return f.read_text(encoding="utf-8"), f.name
    raise FileNotFoundError(f"找不到: {ch_name}")

def annotate_single(ch_name, spec_text, max_retries=3):
    text, original_name = load_chapter(ch_name)
    
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
    
    client = OpenAI(api_key=OR_KEY, base_url=OR_BASE_URL)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "你是专业的古籍实体标注专家，严格按规范标注《汉书》原文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=32000,
                temperature=0.1,
                timeout=180
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  重试 {attempt+1}/{max_retries}: {e}", file=sys.stderr)
                time.sleep(10)
            else:
                raise
    
    return None

def verify(ch_name, annotated_text):
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
    out_file = ANN_DIR / f"{ch_name}_标注.txt"
    out_file.write_text(annotated_text, encoding="utf-8")
    return out_file

def append_progress(ch_name, status, stats=""):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {ch_name}: {status} {stats}\n"
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <卷号> [卷号2 ...]")
        sys.exit(1)
    
    chapters = sys.argv[1:]
    spec_text = load_spec()
    
    print(f"===== OpenRouter DeepSeek V4 Flash 标注开始 =====")
    print(f"模型: {MODEL}")
    print(f"章节: {chapters}")
    print()
    
    for ch in chapters:
        print(f"── 处理 {ch} ──")
        try:
            annotated = annotate_single(ch, spec_text)
            if not annotated:
                append_progress(ch, "FAIL", "无输出")
                continue
            
            ok, stdout, stderr = verify(ch, annotated)
            if not ok:
                append_progress(ch, "VERIFY_FAIL", stderr[:200])
                continue
            
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
