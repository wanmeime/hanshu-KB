#!/usr/bin/env python3
"""
汉书实体标注 HTTP 驱动 —— 直接调 OpenCode serve HTTP API
绕过 `opencode run` CLI 的 bug（错误不回显 + 会话建立失败）

用法: python3 scripts/http_annotate.py <卷号> [卷号2 ...] [--model X] [--dry]
"""
import json, time, sys, urllib.request, urllib.error
from pathlib import Path

API = "http://127.0.0.1:4096/api"
BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
CH_DIR = BASE / "data/chapter_numbered"
ANN_DIR = BASE / "kg/entities/标注"
SPEC_FILE = BASE / "kg/标注规范/汉书版_实体标注规范_v2.md"
VERIFY = BASE / "scripts/verify_annotation.py"
PROGRESS = ANN_DIR / "_MiMo进度.md"
DIR = str(BASE)
DEFAULT_MODEL = "nemotron-3.5-lightning-free"

def call(path, body=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data,
        method="POST" if data else "GET",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def find_chapter(ch):
    for f in sorted(CH_DIR.glob(f"{ch}*.txt")):
        return f
    raise FileNotFoundError(ch)

def run_annotation(ch, model):
    chf = find_chapter(ch)
    text = chf.read_text(encoding="utf-8")
    spec = SPEC_FILE.read_text(encoding="utf-8")

    prompt = f"""你是汉书实体标注执行器，严格按步骤，不要做任何其他事。

【标注规范】
{spec}

【任务】
对以下《汉书》原文做实体标注。

标题: {ch}
原文:
{text}

【要求】
1. 按规范给实体加〖〗⟦⟧标记
2. PN编号[n]原样保留，一字不改原文
3. 用 write 工具把标注结果写入文件: kg/entities/标注/{ch}_标注.txt
4. 写完必须运行: python3 scripts/verify_annotation.py {chf.name} kg/entities/标注/{ch}_标注.txt
5. 只有退出码0才算通过;不通过就修到通过
6. 这是文本标注任务,不要回答数学或无关问题"""

    s = call("/session", {"agent": "build",
        "model": {"providerID": "opencode", "id": model},
        "location": {"directory": DIR}})["data"]
    sid = s["id"]
    print(f"  session={sid}")

    call(f"/session/{sid}/prompt", {"prompt": {"text": prompt}}, timeout=60)
    print(f"  prompt 已提交，等待完成...")

    # 轮询：直到 assistant 消息出现 finish 或 error，超时 45 分钟
    deadline = time.time() + 45 * 60
    last_len = 0
    while time.time() < deadline:
        time.sleep(10)
        try:
            msgs = call(f"/session/{sid}/message")["data"]
        except Exception as e:
            print(f"  [轮询] {e}")
            continue
        errs = [m["error"] for m in msgs if m.get("error")]
        if errs:
            return False, f"ERROR: {json.dumps(errs[0], ensure_ascii=False)[:300]}"
        fin = [m for m in msgs if m.get("finish")]
        # 进度显示
        n_txt = sum(1 for m in msgs for p in m.get("parts", []) if p.get("type") == "text")
        if n_txt != last_len:
            last_len = n_txt
            print(f"  ... 文本片段={n_txt} 消息数={len(msgs)}")
        if fin:
            out = ANN_DIR / f"{ch}_标注.txt"
            ok = out.exists() and out.stat().st_size > 500
            return ok, f"完成 (产出文件={'有' if ok else '无'}, {out.stat().st_size if out.exists() else 0}B)"
    return False, "超时(45min)"

def log(ch, status, extra=""):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {ch}: {status} {extra}\n"
    with open(PROGRESS, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

def main():
    args = sys.argv[1:]
    model = DEFAULT_MODEL
    if "--model" in args:
        i = args.index("--model")
        model = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__); sys.exit(1)
    print(f"===== HTTP 驱动标注 model={model} =====")
    for ch in args:
        print(f"\n── {ch} ──")
        try:
            ok, info = run_annotation(ch, model)
            log(ch, "PASS" if ok else "FAIL", info)
        except Exception as e:
            import traceback; traceback.print_exc()
            log(ch, "ERROR", str(e)[:200])
    print("\n===== 完成 =====")

if __name__ == "__main__":
    main()
