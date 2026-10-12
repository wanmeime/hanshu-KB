# hanshu-KB 项目看板

> 《汉书》历史知识库 · 复刻鲍杰老师《史记》KB（baojie/shiji-kb）的结构化知识库标准
> 参考项目已下载：`/home/jiaoduan/shared/project/hanshu-KB/shiji-kb-reference/`（含 161 个 SKILL 文档）

## 项目目标

把《汉书》整理成和鲍杰老师《史记》KB **同等标准的结构化知识库**。
方法论：复用 shiji-kb 的九步管线 + SKILL 文档（校勘→结构分析→实体构建→事件→关系→本体→推理→管驭→应用）。
数据源：《汉书》（西汉纪传体，74万字，120卷）。

## ⚠️ 工具调用铁律（血的教训）

**CodeBuddy 必须带 `--model custom-local:Deepseek-v4-flash`，否则走默认计费模型烧积分！**
```bash
codebuddy -p --model custom-local:Deepseek-v4-flash --permission-mode bypassPermissions "<任务>"
```
- 漏加 `--model` → 走默认计费通道 → 已烧掉老板 1000+ 积分（2026-10-12 教训）
- 免费微信通道模型 ID：`custom-local:Deepseek-v4-flash`（桥接运行态确认）
- Claude Code 用 `--dangerously-skip-permissions`（YOLO），不烧积分但耗 OpenRouter 额度

## 工作分工（工具链）

| 工具 | 模型 | 用途 | 额度状态 |
|---|---|---|---|
| CodeBuddy | `custom-local:Deepseek-v4-flash`（微信免费，到 10/17）| 批量体力活：实体标注 | 免费，须带 --model |
| Claude Code | GLM-5.3-Flash（OpenRouter）| 精修/考据/高难度 | OpenRouter 保留 $4.45，省着用 |
| Hermes Agent | Step 5 Preview 免费 | 协调、派发、验收、看板 | 免费 |

三者共用本项目目录。**CodeBuddy 主进程起子代理时，主进程退出子代理会被连带杀，产出全丢——必须要求主线程串行逐篇。**

## 操作铁律

1. **每步完成立即推送远端**（Atomgit），禁止批量攒推。
2. **敏感文件绝不提交**：`.claude/`、`secrets.json`、`.env`、`*.bak`。
3. **破坏性操作先确认**。
4. **不虚构数据**：标注必须真实，去标记还原后与底本逐字一致。
5. **验收用 `scripts/verify_annotation.py <底本> <标注文件>`**（参数顺序：底本在前）。
6. **标注铁律**：PN 编号全保留，标注不改原文一字。

## 任务看板（实际进度）

### ✅ 已完成
- [x] 下载 shiji-kb 参考项目（161 SKILL）+ 剥 .git 作参考目录
- [x] 项目规划（docs/项目执行计划.md，Claude Code）
- [x] 表8篇补齐（维基文库，含颜师古注）
- [x] 标注规范 v1 + v2.0（20条MVP规则，6待定项全拍板）
- [x] M0/M1：120卷切分 + PN编号(11830) + PUA校勘(175条) + kg骨架
- [x] M2 试点：5篇标注(7351标记) + 45条错误模式 + 重标验证(错误率<5%)
- [x] M3 第一批：**50篇已标注**（纪类12 + 传类38，已推送GitCode）
  - Claude Code 29篇 + CodeBuddy 21篇（20篇PASS，卷068待返工）

### 🔄 进行中
- [ ] M3 全量标注剩余：表类8篇 + 志类13篇(律历/礼乐/刑法/食货/郊祀/天文/地理/沟洫/艺文) + 五行志5篇 + 部分传类 + 卷068返工

### ⬜ 待完成
- [ ] M4：事件构建 + 年代映射 + SPO事实 + 关系网
- [ ] M5：本体/分类树/置信度/覆盖度
- [ ] M6：应用（人物轨迹/语义检索/地图）

## 关键资产
- 底本：`data/chapter_numbered/`（120卷带PN编号）
- 表8篇：`data/raw/hanshu_tables/`（维基文库）
- 标注规范：`kg/标注规范/汉书版_实体标注规范_v2.md`
- 错误模式：`docs/M2_错误模式汇总.md`（45条）
- 校验脚本：`scripts/verify_annotation.py`
- 已标：`kg/entities/标注/`（50篇）

## 更新记录
- 2026-10-12 M3 50篇标注完成；修正CodeBuddy烧积分坑（漏--model）；更新看板至真实进度
