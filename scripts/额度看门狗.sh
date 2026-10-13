#!/bin/bash
# OpenRouter 额度看门狗：监控额度，低于阈值自动切 CodeBuddy
# 阈值：$0.50（低于此值视为即将清零）
KEY=$(python3 -c "import json; d=json.load(open('/home/jiaoduan/.openclaw/secrets.json')); print(d.get('OPENROUTER_API_KEY',''))" 2>/dev/null)
[ -z "$KEY" ] && KEY=$(grep -oP 'sk-or-\S+' /home/jiaoduan/.openclaw/secrets.json 2>/dev/null | head -1 | tr -d '"')

THRESHOLD=0.50
LOGFILE="/home/jiaoduan/shared/project/hanshu-KB/.额度看门狗.log"
SWITCH_FLAG="/home/jiaoduan/shared/project/hanshu-KB/.切换到CodeBuddy"

check_and_switch() {
  CREDITS=$(curl -s "https://openrouter.ai/api/v1/credits" -H "Authorization: Bearer $KEY" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d['total_credits']-d['total_usage'])" 2>/dev/null)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 剩余额度: \$${CREDITS}" >> "$LOGFILE"

  if [ -z "$CREDITS" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ 查询失败，重试" >> "$LOGFILE"
    return 1
  fi

  # 用 python 比较浮点
  SHOULD_SWITCH=$(python3 -c "print('1' if float('$CREDITS') < $THRESHOLD else '0')" 2>/dev/null)
  if [ "$SHOULD_SWITCH" = "1" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚨 额度 \$${CREDITS} 低于 \$${THRESHOLD}，触发切换 CodeBuddy" >> "$LOGFILE"
    touch "$SWITCH_FLAG"
    # 通知飞书
    lark-cli send --text "⚠️ OpenRouter 额度降至 \$${CREDITS}，已触发切换到 CodeBuddy 继续汉书 KB 项目标注。已完成29篇，剩余继续。" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 飞书通知失败" >> "$LOGFILE"
    exit 0
  fi
  return 0
}

# 循环监控，每3分钟一次，最多监控8小时
for i in $(seq 1 160); do
  check_and_switch && continue
  sleep 180
done
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 看门狗超时退出（额度未低于阈值）" >> "$LOGFILE"
