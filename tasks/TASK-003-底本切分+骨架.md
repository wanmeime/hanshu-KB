# TASK-003：底本切分 + 目录骨架（M0/M1 里程碑）

## 执行者
Claude Code

## 背景
表8篇已补齐（维基文库）。现在要按执行计划 M0/M1 里程碑：
- M0 底本就绪：120 卷底本 + PUA 校勘
- M1 切分完成：PN 编号 + 小节划分

参考 `docs/项目执行计划.md` 的 §2.3 预处理流水线。

## 底本情况
- 纪/志/传（叙事章节）：`shiji-kb-reference/corpus/other/汉书.txt`（73.9万字，简体，无注）
- 表8篇：`data/raw/hanshu_tables/`（维基文库 wikitext，含注，繁体）

## 你的任务

### 1. 底本切分（data/chapter/）
把 120 卷切成 120 个独立文本文件：
- 命名规范：`data/chapter/卷001_高帝纪第一上.txt`（零填充3位卷号）
- 每个文件内容：该卷纯正文（去卷头标记行，保留正文）
- 参考 shiji-kb-reference 的 chapter/ 目录结构（看它怎么组织的）

### 2. PUA/缺字校勘
本地底本有 185 处私用区缺字 + 2 处占位符：
- 扫描 data/chapter/ 里所有 PUA 字符（U+E000-U+F8FF 区段）
- 每个缺字记录到 `data/校勘记录/PUA缺字清单.csv`（卷号/行号/上下文/疑似字）
- 能从维基文库对上的补上，对不上的留待后续

### 3. PN 段落编号（data/chapter_numbered/）
参考 `shiji-kb-reference/skills/SKILL_01a_标注完整性维护.md` 或 02a 章节切分：
- 每段加 PN 编号（Purple Numbers，如 1.1, 1.2, 1.1.1）
- 目标：全书约 10,000 段落

### 4. 建目录骨架
```
kg/
  entities/          # 实体（人物/官职/地名/氏族...）
  events/            # 事件
  facts/             # 事实
  relations/         # 关系
  ontology/          # 本体
  chronology/        # 年表
  genealogy/         # 世系
  structure/         # 结构
  vocabularies/      # 词表
  taxonomy/          # 分类
  quantity/          # 数量
  data/              # 数据文件
```
参考 shiji-kb-reference/kg/ 的结构。

## 完成标准
- data/chapter/ 有 120 个卷文件
- data/校勘记录/PUA缺字清单.csv 存在
- data/chapter_numbered/ 有 PN 编号文件
- kg/ 目录骨架建好

## 约束
- 不 git commit/push
- 不要编造缺字内容，对不上就留空
- 切分要准确，不能丢内容
