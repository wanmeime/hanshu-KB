# hanshu-KB（《汉书》历史知识库）

> 将《汉书》120卷80万字转化为可交互、可探索的知识图谱。

**在线仓库**: [GitHub](https://github.com/baojie/hanshu-KB) | **参考项目**: [baojie/shiji-kb](https://github.com/baojie/shiji-kb)（史记知识库）

## 这是什么？

用AI将《汉书》120卷转化为结构化知识图谱，让两千年前的文字像代码一样可以语法高亮、跳转、搜索、推理。

**核心成果**：
- **120卷全量实体标注** — 142,004次标注（18类名词 + 4类动词，共22类）
- 标注符号体系与 [baojie/shiji-kb](https://github.com/baojie/shiji-kb) 完全对齐
- 验证脚本去标记后与底本逐字全等，120/120卷 PASS

## 定位

- 复用 [shiji-kb](https://github.com/baojie/shiji-kb)（鲍捷）的可迁移 SKILL 管线方法论和标注规范
- 覆盖《汉书》（前四史之一，西汉 230 年历史，约 120 卷 / 80 万字）
- 目标：与已有《史记》项目衔接，逐步扩展 24 史

## 目录结构

```
data/chapter_numbered/   120卷带PN编号底本
kg/
  entities/标注/          120卷实体标注文件（〖〗⟦⟧标记体系）
  events/                事件（M4阶段）
  relations/             关系（M5阶段）
  ontology/              本体（M5阶段）
  genealogy/             家谱（M5阶段）
  chronology/            年表（M4阶段）
  facts/                 事实三元组（M5阶段）
  structure/             结构分析（M2阶段）
  taxonomy/              分类体系
  vocabularies/          词汇表
  quantity/              数量
  标注规范/              标注规范文档
scripts/                 抽取/处理/验证管线
docs/                    交接文档、进度记录
```

## 数据源参考

- 《汉书》全文：维基文库等开放文本
- 人物/地理：CBDB（哈佛+北大+中研院）、CHGIS
- 实体标注参考：GuNER 2023（二十四史）、古白平行语料库

## 状态

- [x] 项目骨架
- [x] 数据准备（120卷底本 + PN编号）
- [x] 标注规范（v2.0，对齐史记KB）
- [x] **120卷全量实体标注完成**
- [x] 事件关系构建（M4）
- [x] 知识库成型（M5）
- [x] 应用构造（M6，含人物一生轨迹时间线 173 页）

## 致谢与许可证

### 标注规范与方法论来源

本项目的实体标注规范（18类名词 + 4类动词标记体系）和SKILL管线方法论源自 **[baojie/shiji-kb](https://github.com/baojie/shiji-kb)**（史记知识库）项目，由 **鲍捷（[baojie](https://github.com/baojie)）** 创建并开源。在此致谢。

### 许可证

- **标注数据**：[CC BY-NC-SA 4.0](LICENSE) — 署名-非商业性使用-相同方式共享（可自由用于学术研究和非商业项目，需注明出处，衍生作品需使用相同许可；商业使用请联系作者获取授权）
- **分析脚本**：MIT License — 自由使用、修改、分发
- **《汉书》原文**：公有领域作品

学术文献请引用：汉书知识库，2026，在线发布于 https://github.com/baojie/hanshu-KB

### 免责声明

本项目由AI辅助生成，标注和知识提取中不可避免地存在错误和疏漏。本知识库严格局限于《汉书》本身的文本内容，不涉及史实考证。
