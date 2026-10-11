# hanshu-KB 项目看板

> 《汉书》历史知识库 · 复刻《史记》KB 的知识库结构
> 对标标杆：`/home/jiaoduan/shared/project/shiji-map/raw/shiji-kb/kg/`（《史记》KB 知识库核心）

## 项目目标

把《汉书》做成和《史记》KB **同样的结构化知识库**。直接复用 shiji-kb 已验证的 schema、11 大模块结构、词表、脚本，把数据源从《史记》换成《汉书》（西汉纪传体，230 年）。

《史记》KB 核心（`shiji-kb/kg/`）含 11 大模块：
ontology（本体/sku）· entities（实体/人物/官职/身份/别名/消歧/词表）· events（事件）· facts（事实/人物轨迹）· relations（关系）· genealogy（世系）· chronology（年表/在位期）· structure（段落结构）· vocabularies · taxonomy · quantity

史记与汉书同为**纪传体**，抽取/消歧/世系/足迹生成逻辑可直接迁移，汉书是同构复刻。

## 数据源

- 《汉书》原文（维基文库 或 你已有来源）
- 对标标杆：shiji-map/raw/shiji-kb/kg（schema、词表、脚本可复用）
- 生成足迹：一人一传天然完整，最适合"输入人名→生成一生轨迹"

## 工作分工（工具链）

| 工具 | 模型 | 用途 |
|---|---|---|
| CodeBuddy | 微信免费 DeepSeek-V4-Flash（到 10/17） | 日常体力活：批量抽取、格式转换、清洗 |
| Claude Code | GLM-5.3-Flash（OpenRouter 刷额度） | 精修/考据/高难度：人物消歧、关系推理、难句考订 |
| Hermes Agent | Step 5 Preview 免费（到 10/15） | 协调、任务拆解、看板维护、跨设备协作 |

三者共用本项目目录，Hindsight 记忆库按目录名自动共享。

## 操作铁律

1. **每步完成必须立即推送远端**（Atomgit），禁止批量攒着推。
   ```bash
   cd ~/shared/project/hanshu-KB
   git add -A && git commit -m "<本次改动说明>" && git push
   ```
2. **敏感文件绝不提交**：`.claude/`、`secrets.json`、`.env`、`*.bak`（已由 .gitignore 拦截，新增敏感文件先确认）。
3. **破坏性操作先确认**：rm/docker rmi/清目录等先跟老板对齐。
4. **不虚构数据**：抽取结果必须来自原文或权威库，无法确定标注 `[待考]`，绝不编造。
5. **项目命名用拼音**，不用汉字。

## 目录规划

```
hanshu-KB/
├── README.md              # 项目说明
├── PROJECT_KANBAN.md      # 本看板
├── .gitignore             # 敏感文件拦截
├── data/
│   ├── raw/               # 《汉书》原文（未处理）
│   ├── extracted/         # 抽取结果（人物/地点/事件/关系 JSON）
│   └── geo/               # 地名坐标数据
├── scripts/               # 抽取/清洗/校验脚本
├── kb/                    # 知识库成品（可检索结构）
└── docs/                  # 数据字典、字段说明
```

## 任务看板

### 阶段一：摸底与管线搭建（进行中）
- [ ] 下载通鉴项目管线代码，研读数据结构与抽取流程
- [ ] 获取《汉书》原文（维基文库），确定分卷粒度
- [ ] 确定抽取 prompt 模板（复用通鉴四类实体模式）
- [ ] 建 data/scripts/kb/docs 目录骨架

### 阶段二：试点抽取
- [ ] 选 1-2 个高价值传记试点（建议《陈胜项籍传》《高祖本纪》级别）
- [ ] 跑通 人物→地点→事件→关系 全链路
- [ ] 人工校验 + 精修（Claude Code 考据）

### 阶段三：批量生产
- [ ] CodeBuddy 批量抽取剩余卷
- [ ] 实体消歧与融合（人物重名、地名古今）
- [ ] 关系网构建

### 阶段四：知识库成型
- [ ] 人物足迹生成（生平阶段 + 位置映射现代地图）
- [ ] 检索接口 / 与 shiji-map 衔接（史记同目录项目）
- [ ] 决定是否开源（当前 Atomgit 公开仓库）

## 更新记录

- 2026-10-11 项目初始化，建 Atomgit 仓库，通鉴管线代码下载中
