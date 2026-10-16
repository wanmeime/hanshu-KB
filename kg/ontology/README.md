# 汉书知识库本体

> 从120卷标注实例 Bottom-Up 归纳生成
> 复用史记KB方法论（SKILL_06a 实体到本体）

## 本体结构

### 实体类型（18类名词 + 4类动词）

| 类型 | RDF类 | 实体数 | 说明 |
|------|-------|--------|------|
| 人名 | hs:Person | 8944 | |
| 地名 | hs:Place | 5387 | |
| 官职 | hs:OfficialTitle | 3307 | |
| 数量 | hs:Quantity | 3300 | |
| 神话 | hs:Mythology | 2652 | |
| 时间 | hs:Time | 2114 | |
| 典籍 | hs:Book | 1360 | |
| =System | hs:=System | 849 | |
| 器物 | hs:Artifact | 808 | |
| 身份 | hs:Status | 676 | |
| 天文 | hs:Astronomy | 501 | |
| 生物 | hs:Biology | 348 | |
| 族群 | hs:EthnicGroup | 302 | |
| 礼仪 | hs:Ritual | 267 | |
| 刑法 | hs:Law | 262 | |
| 邦国 | hs:State | 261 | |
| 朝代 | hs:Dynasty | 192 | |
| 思想 | hs:Thought | 168 | |

### 关系类型

| 关系 | RDF属性 | 定义域 | 值域 |
|------|---------|--------|------|
| 父子 | hs:fatherOf | Person | Person |
| 母子 | hs:motherOf | Person | Person |
| 兄弟 | hs:brotherOf | Person | Person |
| 夫妻 | hs:spouseOf | Person | Person |
| 君臣 | hs:serves | Person | Person |
| 敌对 | hs:enemyOf | Person | Person |
| 联盟 | hs:alliedWith | Person | Person |
| 师徒 | hs:teacherOf | Person | Person |
| 封赏 | hs:appointedBy | Person | Person |
| 出生于 | hs:bornIn | Person | Time |
| 卒于 | hs:diedIn | Person | Time |

## 文件说明
- `hanshu_ontology.ttl` — OWL/RDF 本体文件（TTL格式）

## 统计
- 实体类型：18 类
- 实体总数：31698 个
- 名词标注：131887 次
- 动词标注：10966 次