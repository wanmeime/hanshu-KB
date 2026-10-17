# hanshu-KB 项目看板

> 《汉书》历史知识库 · 复刻鲍杰老师《史记》KB（baojie/shiji-kb）的结构化知识库标准
> 参考项目已下载：`/home/jiaoduan/shared/project/hanshu-kb/shiji-kb-reference/`（含 161 个 SKILL 文档）

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

### ✅ 已完成（120/120 卷）🎉
- [x] 下载 shiji-kb 参考项目（161 SKILL）+ 剥 .git 作参考目录
- [x] 项目规划（docs/项目执行计划.md，Claude Code）
- [x] 表8篇补齐（维基文库，含颜师古注）
- [x] 标注规范 v1 + v2.0（20条MVP规则，6待定项全拍板）
- [x] M0/M1：120卷切分 + PN编号(11830) + PUA校勘(175条) + kg骨架
- [x] M2 试点：5篇标注(7351标记) + 45条错误模式 + 重标验证(错误率<5%)
- [x] M3 纪传志表标注：**118卷已标注并推送**（纪类12 + 传类87 + 志类13 + 表类6）
  - 表类口径对齐卷014 MiMo 详细版（动词完整标注）
  - 卷018 PASS 名词1355+动词433（r86~r135补标47段）
  - 卷019 PASS 名词856（百官公卿表制度叙述文）
  - 卷022 PASS 名词272（礼乐志+安世房中歌+郊祀歌）
  - 卷100 PASS 名词193（班氏家传+王命论+幽通赋+宾戏）
  - 卷100b PASS 名词316（叙传骈文）

- [x] M3 全部120卷标注完成并推送（120/120 PASS）
- [x] 卷048标注损坏修复（9段）+ 非标注文件清理 + LICENSE/README署名
- [x] GitHub仓库创建并推送：https://github.com/wanmeime/hanshu-KB
- [x] **M4 事件关系构建**：词表(31698实体) + 年号映射(15帝王41年号) + 事件(11107) + 关系(24787) + 事实(5482) + 家谱(14帝王) + 结构(9681段)
- [x] **M5 知识库成型**：本体TTL(18类型31698实例) + 分类树(8944人物) + 生卒年(43已知+399推断) + 反常推理(529异常) + 置信度/覆盖度评估
- [x] **M6 应用构造**：语法高亮(120卷HTML) + 语义搜索(31698实体) + 历史地图(5387地名92坐标) + 可视化(时间线+网络图)
- [x] **M6 补：人物一生轨迹**（对标 SKILL_W10y 时间线页规范）：173位人物（≥3事件跨≥3年，含帝王泛称合并与停用表过滤），节奏为"年代→事件表"，含生卒年与章节溯源，脚本 `scripts/build_persons_timeline.py`

### 🔄 进行中
- 无

### ⬜ 待完成
- 无（M0-M6 全部完成）

## 关键资产
- 底本：`data/chapter_numbered/`（120卷带PN编号）
- 标注：`kg/entities/标注/`（120卷）+ `kg/entities/entity_index.json`（31698实体）
- 标注规范：`kg/标注规范/汉书版_实体标注规范_v2.md`
- 词表：`kg/vocabularies/`（18类名词+4类动词）
- 年号映射：`kg/chronology/data/`（reign_periods + year_ce_map + 编年表）
- 事件：`kg/events/data/`（120卷事件索引 + all_events.json）
- 关系：`kg/relations/`（all_relations.json + 按类型分.md）
- 事实：`kg/facts/data/all_facts.json`（5482条SPO）
- 家谱：`kg/genealogy/`（imperial_genealogy.json + 汉朝帝王家谱.md）
- 本体：`kg/ontology/hanshu_ontology.ttl`（OWL/RDF）
- 分类树：`kg/taxonomy/`（person.ttl + person_taxonomy.md）
- 评估：`kg/evaluation/`（反常推理 + 置信度 + 覆盖度 + 正确性）
- 应用：`kg/applications/`（语法高亮 + 语义搜索 + 历史地图 + 可视化 + 一生轨迹时间线173页）
- 校验脚本：`scripts/verify_annotation.py`
- GitHub：https://github.com/wanmeime/hanshu-KB

## 更新记录
- 2026-10-17b M6补全人物一生轨迹：对标 SKILL_W10y，173页时间线（王莽806/汉高祖504/汉宣帝482/项羽404事件），泛称合并+停用表过滤，脚本 scripts/build_persons_timeline.py；M6验收口径定为"A级标准=史记KB开源同等，轨迹动画属 map 项目"
- 2026-10-17 M4-M6 质量修复②：事实补"+类"宾语(斩蛇等)、不及物空宾语不再误报、关系正则加误配守卫(删3条伪关系)；异常1837→1059、error清零、置信度high 59.9%、原文校验100%（commit faca544）
- 2026-10-16 M4-M6 全部完成并推送（origin + GitHub）：事件关系+知识库成型+应用构造
- 2026-10-16 120/120卷标注全部PASS + 卷048修复 + GitHub发布
- 2026-10-15 卷015b/卷017标注完成并推送；卷018阶段进度77/130段推送；写交接文档；113/120卷已标
- 2026-10-12 M3 50篇标注完成；修正CodeBuddy烧积分坑（漏--model）；更新看板至真实进度
