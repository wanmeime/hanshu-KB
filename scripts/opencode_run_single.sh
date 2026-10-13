#!/bin/bash
# 标注单篇汉书，带重试（最多3次，间隔30s）
# 用法: bash scripts/opencode_run.sh <卷号> <源文件相对路径>
set -e
VOL=$1
SRC=$2
BASE="/home/jiaoduan/shared/project/hanshu-KB"
OUT="$BASE/kg/entities/标注/${VOL}_标注.txt"
LOG="$BASE/.mimo_run_${VOL}.log"
export PATH="$HOME/.opencode/bin:$PATH"
cd "$BASE"

for i in 1 2 3; do
  echo "[$(date '+%H:%M:%S')] 第${i}次尝试标 ${VOL}" >> "$LOG"
  rm -f "$OUT"
  opencode run --auto -m opencode/mimo-v2.6-flash-free \
    "你是汉书实体标注执行器。先读kg/标注规范/汉书版_实体标注规范_v2.md。然后处理:${VOL}，文件是data/chapter_numbered/${SRC}。按v2规范给实体加〖〗⟦⟧标记,PN编号[n]原样保留,一字不改原文,写入${OUT},再运行python3 scripts/verify_annotation.py data/chapter_numbered/${SRC} ${OUT}确认退出码0,通过才算完成。不要做其他事。" \
    >> "$LOG" 2>&1
  if [ -f "$OUT" ] && python3 scripts/verify_annotation.py "data/chapter_numbered/${SRC}" "$OUT" > /dev/null 2>&1; then
    echo "[$(date '+%H:%M:%S')] ${VOL} PASS" >> "$LOG"
    exit 0
  fi
  echo "[$(date '+%H:%M:%S')] ${VOL} 失败,重试..." >> "$LOG"
  sleep 30
done
echo "[$(date '+%H:%M:%S')] ${VOL} 3次全失败" >> "$LOG"
exit 1
