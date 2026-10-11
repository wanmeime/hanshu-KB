# TASK-001：精读《史记》KB 结构 + 设计汉书 KB schema

## 执行者
Claude Code（GLM-5.3-Flash）

## 背景
我们要把《汉书》做成和《史记》KB 同样的结构化知识库。
《史记》KB 的知识库核心在这里：`/home/jiaoduan/shared/project/shiji-map/raw/shiji-kb/kg/`
汉书项目目录：`/home/jiaoduan/shared/project/hanshu-KB/`

史记和汉书同为纪传体，schema、词表、抽取/消歧/世系/足迹逻辑可直接迁移。
你的任务：精读史记 KB 的真实结构，产出一份"汉书 KB schema 迁移设计"。

## 必读的史记 KB 结构（raw/shiji-kb/kg/ 下 11 模块）
- ontology/（ontology-v1、ontology-v2/.../skus，看 sku 和本体怎么组织）
- entities/（人物/官职/身份/别名 entity_aliases/消歧 disambiguation_map/词表 *_wordlist，看 JSON 字段结构）
- events/、facts/（含人物轨迹 trajectory，看 fact_*.md 和 trajectory 文件格式）
- relations/、genealogy/（世系）、chronology/（年表/在位期/年号）
- structure/、vocabularies/、taxonomy/、quantity/
- 各模块的 README.md 必读，它们说明字段定义和用法
- shiji-map/scripts/ 里的抽取/清洗/校验/足迹生成脚本也扫一遍，标出哪些能复用

## 任务产出（写到 hanshu-KB/docs/ 下）

### 1. docs/史记KB结构分析.md
- 11 大模块各自的职责、数据格式（JSON/MD）、字段清单
- 重点：entities 人物实体的完整字段 schema、facts 里 trajectory 的格式、genealogy 世系格式
- 哪些是硬数据（重做）vs 哪些是可复用工具（词表/脚本）

### 2. docs/汉书KB-schema设计.md
- 汉书 KB 的完整目录结构（对齐史记 11 模块）
- 每类实体的字段 schema（直接复用史记字段，标注汉书特有差异，如汉代特有的官职/爵位/外戚/西域都护等）
- 数据字典：字段名、类型、含义、示例

### 3. docs/汉书原文来源方案.md
- 《汉书》原文从哪里来（维基文库/其他），分卷粒度（本纪12/表8/志10/列传70）
- 建议先下哪 1-2 卷做试点

### 4. 抽取流程复用评估
- 史记 scripts/ 里哪些脚本能直接/改造后用于汉书，哪些要重写
- 列出清单

## 完成标准
- 上述 3 份文档 + 脚本复用清单都落地在 docs/ 下
- schema 设计必须基于史记 KB 的**真实字段**，不能凭空编
- 明确标注哪些字段/工具复用、哪些重做

## 约束
- 只读史记 KB 和写文档，不要 git commit/push（Coordinator 统一推送）
- 不要下载史记原文以外的数据
- 遇到看不懂的史记内部约定，如实记录并标注疑问，不要猜
