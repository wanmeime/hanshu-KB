#!/bin/bash
# 世系表分批派发：把表格按N行切批，逐批喂给MiMo，避免单次上下文爆炸
# 用法: table_batch_dispatch.sh <底本> <卷号> [批大小]
set -e
BASE="$1"; JUAN="$2"; BATCH="${3:-15}"
OUTDIR="kg/entities/标注/_build"
mkdir -p "$OUTDIR"

# 提取所有 [rN] 行
grep -aE "^\[r[0-9]+\]" "$BASE" > "$OUTDIR/${JUAN}_rows.txt"
TOTAL=$(wc -l < "$OUTDIR/${JUAN}_rows.txt")
echo "总表格行数: $TOTAL, 批大小: $BATCH"

# 分批
split -l "$BATCH" -d -a 3 "$OUTDIR/${JUAN}_rows.txt" "$OUTDIR/${JUAN}_batch_"
ls "$OUTDIR/${JUAN}_batch_"* | wc -l | xargs echo "批次数:"
