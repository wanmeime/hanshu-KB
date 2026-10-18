#!/usr/bin/env python3
"""M5-1/2/3: 本体构造 + 概念分类树 + 生卒年推断
生成 ontology/ (OWL/RDF TTL) + taxonomy/ (person.ttl + 分类树) + chronology/person_lifespan_events.json
"""
import json, os, re
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ONT_DIR = BASE / "kg" / "ontology"
TAX_DIR = BASE / "kg" / "taxonomy"
KG_DIR = BASE / "kg"
CHRON_DIR = BASE / "kg" / "chronology" / "data"
ENT_DIR = BASE / "kg" / "entities"
ANN_DIR = ENT_DIR / "标注"
ONT_DIR.mkdir(parents=True, exist_ok=True)
TAX_DIR.mkdir(parents=True, exist_ok=True)

NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')

SYMBOL_TO_TYPE = {
    '@': 'Person', '=': 'Place', ';': 'OfficialTitle', '#': 'Status', '%': 'Time',
    '&': 'Dynasty', '◆': 'State', '^': '=System', '~': 'EthnicGroup', '•': 'Artifact',
    '!': 'Astronomy', '?': 'Mythology', '+': 'Biology', '{': 'Book', ':': 'Ritual',
    '[': 'Law', '_': 'Thought', '$': 'Quantity',
}

TYPE_LABELS = {
    'Person': '人名', 'Place': '地名', 'OfficialTitle': '官职', 'Status': '身份',
    'Time': '时间', 'Dynasty': '朝代', 'State': '邦国', 'System': '制度',
    'EthnicGroup': '族群', 'Artifact': '器物', 'Astronomy': '天文', 'Mythology': '神话',
    'Biology': '生物', 'Book': '典籍', 'Ritual': '礼仪', 'Law': '刑法',
    'Thought': '思想', 'Quantity': '数量',
}

def load_entity_index():
    with open(ENT_DIR / "entity_index.json", 'r', encoding='utf-8') as f:
        return json.load(f)

def load_vocab_summary():
    with open(BASE / "kg" / "vocabularies" / "data" / "vocab_summary.json", 'r', encoding='utf-8') as f:
        return json.load(f)

def build_ontology_tll(entity_index):
    """生成 OWL/RDF 本体 TTL 文件"""
    print("  构建本体 TTL...")
    
    # 按类型分组实体
    type_entities = defaultdict(set)
    for key, entity in entity_index.items():
        symbol = entity['symbol']
        rdf_type = SYMBOL_TO_TYPE.get(symbol, 'Entity')
        type_entities[rdf_type].add(entity['display'])
    
    lines = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix hs: <http://hanshu-kb.org/ontology#> .",
        "",
        "# 汉书知识库本体 (Hanshu KB Ontology)",
        "# 从120卷标注实例 Bottom-Up 归纳生成",
        "",
        "# === 本体元数据 ===",
        "hs:HanshuOntology a owl:Ontology ;",
        '    rdfs:label "汉书知识库本体" ;',
        '    rdfs:comment "从《汉书》120卷实体标注归纳生成的本体，复用史记KB方法论" .',
        "",
        "# === 实体类型定义 ===",
    ]
    
    # 定义类层次
    class_hierarchy = {
        'Entity': None,
        'Person': 'Entity',
        'Place': 'Entity',
        'Time': 'Entity',
        'Organization': 'Entity',
        'OfficialTitle': 'Organization',
        'State': 'Organization',
        'Dynasty': 'Organization',
        'EthnicGroup': 'Organization',
        'Status': 'Entity',
        'System': 'Entity',
        'Artifact': 'Entity',
        'Astronomy': 'Entity',
        'Mythology': 'Entity',
        'Biology': 'Entity',
        'Book': 'Entity',
        'Ritual': 'Entity',
        'Law': 'Entity',
        'Thought': 'Entity',
        'Quantity': 'Entity',
    }
    
    for cls, parent in class_hierarchy.items():
        label = TYPE_LABELS.get(cls, cls)
        if parent:
            lines.append(f"hs:{cls} a owl:Class ;")
            lines.append(f'    rdfs:label "{label}" ;')
            lines.append(f"    rdfs:subClassOf hs:{parent} .")
        else:
            lines.append(f"hs:{cls} a owl:Class ;")
            lines.append(f'    rdfs:label "{label}" .')
        lines.append("")
    
    # 定义属性
    properties = [
        ('hasName', '名称', 'hs:Entity', 'xsd:string'),
        ('hasCanonicalName', '规范名', 'hs:Entity', 'xsd:string'),
        ('hasTime', '时间', 'hs:Entity', 'hs:Time'),
        ('hasPlace', '地点', 'hs:Entity', 'hs:Place'),
        ('hasDynasty', '朝代', 'hs:Entity', 'hs:Dynasty'),
        ('bornIn', '出生于', 'hs:Person', 'hs:Time'),
        ('diedIn', '卒于', 'hs:Person', 'hs:Time'),
        ('bornAt', '出生地', 'hs:Person', 'hs:Place'),
        ('hasTitle', '官职', 'hs:Person', 'hs:OfficialTitle'),
        ('fatherOf', '父', 'hs:Person', 'hs:Person'),
        ('motherOf', '母', 'hs:Person', 'hs:Person'),
        ('spouseOf', '配偶', 'hs:Person', 'hs:Person'),
        ('brotherOf', '兄弟', 'hs:Person', 'hs:Person'),
        ('serves', '臣事', 'hs:Person', 'hs:Person'),
        ('enemyOf', '敌对', 'hs:Person', 'hs:Person'),
        ('alliedWith', '联盟', 'hs:Person', 'hs:Person'),
        ('teacherOf', '师', 'hs:Person', 'hs:Person'),
        ('appointedBy', '封赏', 'hs:Person', 'hs:Person'),
    ]
    
    lines.append("# === 对象属性 ===")
    for prop, label, domain, rng in properties:
        lines.append(f"hs:{prop} a owl:ObjectProperty ;")
        lines.append(f'    rdfs:label "{label}" ;')
        lines.append(f"    rdfs:domain {domain} ;")
        lines.append(f"    rdfs:range {rng} .")
        lines.append("")
    
    # 实例声明（全量实体，31698）
    lines.append("# === 实例（全量）===")
    for rdf_type, entities in sorted(type_entities.items()):
        sorted_entities = sorted(entities)
        lines.append(f"# {TYPE_LABELS.get(rdf_type, rdf_type)} ({len(sorted_entities)} 个)")
        for entity in sorted_entities:
            # 转义特殊字符
            safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', entity)
            if not safe_name:
                continue
            lines.append(f"hs:{rdf_type}_{safe_name} a hs:{rdf_type} ;")
            lines.append(f'    rdfs:label "{entity}" .')
        lines.append("")
    
    ttl_path = ONT_DIR / "hanshu_ontology.ttl"
    with open(ttl_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return len(type_entities), sum(len(v) for v in type_entities.values())

def build_taxonomy(entity_index):
    """构建概念分类树"""
    print("  构建分类树...")
    
    # 人物分类（按出现频率和上下文）
    persons = [(e['display'], e['count']) for e in entity_index.values() if e['symbol'] == '@']
    persons.sort(key=lambda x: -x[1])
    
    # 生成 person.ttl (OWL)
    lines = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix hs: <http://hanshu-kb.org/ontology#> .",
        "",
        "# 汉书人物分类本体",
        "",
        "hs:Person a owl:Class ; rdfs:label \"人物\" .",
        "",
        "# 人物子类",
        "hs:Emperor rdfs:subClassOf hs:Person ; rdfs:label \"帝王\" .",
        "hs:Prince rdfs:subClassOf hs:Person ; rdfs:label \"诸侯王\" .",
        "hs:Marquis rdfs:subClassOf hs:Person ; rdfs:label \"列侯\" .",
        "hs:Official rdfs:subClassOf hs:Person ; rdfs:label \"官员\" .",
        "hs:General rdfs:subClassOf hs:Person ; rdfs:label \"将领\" .",
        "hs:Scholar rdfs:subClassOf hs:Person ; rdfs:label \"学者\" .",
        "hs:Empress rdfs:subClassOf hs:Person ; rdfs:label \"后妃\" .",
        "hs:ForeignLeader rdfs:subClassOf hs:Person ; rdfs:label \"外族首领\" .",
        "hs:OtherPerson rdfs:subClassOf hs:Person ; rdfs:label \"其他人物\" .",
        "",
        "# 人物实例（全量，含出现次数；14 位君主归 hs:Emperor）",
    ]

    # 君主名与别名集合（reign_periods）
    emperor_alias = set()
    EMPEROR = {'汉高祖','汉惠帝','高后','汉文帝','汉景帝','汉武帝','汉昭帝','汉宣帝',
               '汉元帝','汉成帝','汉哀帝','汉平帝','孺子婴','王莽','更始帝'}
    try:
        rp = json.loads((KG_DIR / "chronology" / "data" / "reign_periods.json").read_text('utf-8'))
        for r, d in rp['rulers'].items():
            if r in EMPEROR:
                emperor_alias.add(r)
                emperor_alias.update(d.get('alias', []))
    except Exception:
        pass

    persons.sort(key=lambda x: -x[1])
    for name, count in persons:
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
        if not safe_name:
            continue
        sub = 'hs:Emperor' if name in emperor_alias else 'hs:Person'
        lines.append(f"hs:Person_{safe_name} a {sub} ;")
        lines.append(f'    rdfs:label "{name}" ;')
        lines.append(f'    hs:occurrenceCount {count} .')
    
    with open(TAX_DIR / "person.ttl", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    # 生成 person_taxonomy.md
    lines = [
        "# 汉书人物分类树",
        "",
        f"> 从120卷标注提取，共 {len(persons)} 个人物实体",
        "",
        "## 分类体系",
        "",
        "```",
        "Person",
        "├── Emperor（帝王）",
        "├── Prince（诸侯王）",
        "├── Marquis（列侯）",
        "├── Official（官员）",
        "├── General（将领）",
        "├── Scholar（学者）",
        "├── Empress（后妃）",
        "├── ForeignLeader（外族首领）",
        "└── OtherPerson（其他人物）",
        "```",
        "",
        "## 高频人物（前100）",
        "",
        "| 排名 | 人物 | 出现次数 |",
        "|------|------|---------|",
    ]
    
    for i, (name, count) in enumerate(persons[:100], 1):
        lines.append(f"| {i} | {name} | {count} |")
    
    with open(TAX_DIR / "person_taxonomy.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    # 生成 person_classified.json
    classified = {
        'metadata': {'total_persons': len(persons)},
        'categories': {
            'Emperor': [],
            'Prince': [],
            'Marquis': [],
            'Official': [],
            'General': [],
            'Scholar': [],
            'Empress': [],
            'ForeignLeader': [],
            'OtherPerson': [{'name': n, 'count': c} for n, c in persons],
        },
    }
    with open(TAX_DIR / "data" / "person_classified.json", 'w', encoding='utf-8') as f:
        json.dump(classified, f, ensure_ascii=False, indent=2)
    
    return len(persons)

def infer_lifespans():
    """推断人物生卒年"""
    print("  推断生卒年...")
    
    # 已知帝王生卒年
    known_lifespans = {
        "汉高祖": {"birth": -256, "death": -195, "confidence": "high", "source": "史记/汉书本纪"},
        "刘邦": {"birth": -256, "death": -195, "confidence": "high", "source": "史记/汉书本纪"},
        "汉惠帝": {"birth": -210, "death": -188, "confidence": "high", "source": "汉书本纪"},
        "刘盈": {"birth": -210, "death": -188, "confidence": "high", "source": "汉书本纪"},
        "吕后": {"birth": -241, "death": -180, "confidence": "high", "source": "史记/汉书本纪"},
        "汉文帝": {"birth": -203, "death": -157, "confidence": "high", "source": "汉书本纪"},
        "刘恒": {"birth": -203, "death": -157, "confidence": "high", "source": "汉书本纪"},
        "汉景帝": {"birth": -188, "death": -141, "confidence": "high", "source": "汉书本纪"},
        "刘启": {"birth": -188, "death": -141, "confidence": "high", "source": "汉书本纪"},
        "汉武帝": {"birth": -156, "death": -87, "confidence": "high", "source": "汉书本纪"},
        "刘彻": {"birth": -156, "death": -87, "confidence": "high", "source": "汉书本纪"},
        "汉昭帝": {"birth": -94, "death": -74, "confidence": "high", "source": "汉书本纪"},
        "刘弗陵": {"birth": -94, "death": -74, "confidence": "high", "source": "汉书本纪"},
        "汉宣帝": {"birth": -91, "death": -49, "confidence": "high", "source": "汉书本纪"},
        "刘询": {"birth": -91, "death": -49, "confidence": "high", "source": "汉书本纪"},
        "汉元帝": {"birth": -75, "death": -33, "confidence": "high", "source": "汉书本纪"},
        "刘奭": {"birth": -75, "death": -33, "confidence": "high", "source": "汉书本纪"},
        "汉成帝": {"birth": -51, "death": -7, "confidence": "high", "source": "汉书本纪"},
        "刘骜": {"birth": -51, "death": -7, "confidence": "high", "source": "汉书本纪"},
        "汉哀帝": {"birth": -25, "death": -1, "confidence": "high", "source": "汉书本纪"},
        "刘欣": {"birth": -25, "death": -1, "confidence": "high", "source": "汉书本纪"},
        "汉平帝": {"birth": -9, "death": 5, "confidence": "high", "source": "汉书本纪"},
        "刘衎": {"birth": -9, "death": 5, "confidence": "high", "source": "汉书本纪"},
        "王莽": {"birth": -45, "death": 23, "confidence": "high", "source": "汉书王莽传"},
        "萧何": {"birth": None, "death": -193, "confidence": "medium", "source": "汉书萧何传"},
        "曹参": {"birth": None, "death": -190, "confidence": "medium", "source": "汉书曹参传"},
        "张良": {"birth": None, "death": -186, "confidence": "medium", "source": "史记/汉书"},
        "韩信": {"birth": -231, "death": -196, "confidence": "medium", "source": "汉书韩信传"},
        "陈平": {"birth": None, "death": -178, "confidence": "medium", "source": "汉书陈平传"},
        "周勃": {"birth": None, "death": -169, "confidence": "medium", "source": "汉书周勃传"},
        "卫青": {"birth": None, "death": -106, "confidence": "medium", "source": "汉书卫青传"},
        "霍去病": {"birth": -140, "death": -117, "confidence": "high", "source": "汉书霍去病传"},
        "霍光": {"birth": None, "death": -68, "confidence": "medium", "source": "汉书霍光传"},
        "董仲舒": {"birth": -179, "death": -104, "confidence": "medium", "source": "汉书董仲舒传"},
        "司马相如": {"birth": -817, "death": None, "confidence": "low", "source": "汉书司马相如传"},
        "司马迁": {"birth": -145, "death": -86, "confidence": "medium", "source": "汉书司马迁传"},
        "扬雄": {"birth": -53, "death": 18, "confidence": "medium", "source": "汉书扬雄传"},
        "班固": {"birth": 32, "death": 92, "confidence": "high", "source": "后汉书班固传"},
        "张骞": {"birth": None, "death": -114, "confidence": "medium", "source": "汉书张骞传"},
        "李广": {"birth": None, "death": -119, "confidence": "medium", "source": "汉书李广传"},
        "苏武": {"birth": None, "death": -60, "confidence": "low", "source": "汉书苏武传"},
        "赵充国": {"birth": -137, "death": -52, "confidence": "medium", "source": "汉书赵充国传"},
        "刘秀": {"birth": -5, "death": 57, "confidence": "high", "source": "后汉书"},  # 汉光武帝
    }
    
    # 从标注文件中提取薨/崩/死事件来补充
    lifespan_events = []
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    for filepath in ann_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para = m.group(1)
            text = line[m.end():]
            
            # 查找薨/崩/死/自杀模式
            for m2 in re.finditer(r'〖@([^〗]+)〗\s*(薨|崩|死|自杀|要斩|弃市|下狱死)', text):
                name = m2.group(1).split('|')[0].strip()
                verb = m2.group(2)
                
                # 查找附近的时间
                times = [t for t in NOUN_RE.findall(text) if t[0] == '%']
                time_str = times[0][1].split('|')[0] if times else None
                
                if name not in known_lifespans:
                    lifespan_events.append({
                        'person': name,
                        'event': verb,
                        'time': time_str,
                        'source': filepath.stem,
                        'para': para,
                    })
    
    # 生成 person_lifespan_events.json
    lifespan_data = {
        'metadata': {
            'known_count': len(known_lifespans),
            'inferred_count': len(lifespan_events),
            'method': '已知历史事实 + 标注文本薨/崩/死事件提取',
        },
        'known_lifespans': known_lifespans,
        'inferred_events': lifespan_events[:1000],  # 限制大小
    }
    
    with open(CHRON_DIR / "person_lifespan_events.json", 'w', encoding='utf-8') as f:
        json.dump(lifespan_data, f, ensure_ascii=False, indent=2)
    
    return len(known_lifespans), len(lifespan_events)

def build_ontology_md(entity_index, vocab_summary):
    """生成本体说明 MD"""
    lines = [
        "# 汉书知识库本体",
        "",
        "> 从120卷标注实例 Bottom-Up 归纳生成",
        "> 复用史记KB方法论（SKILL_06a 实体到本体）",
        "",
        "## 本体结构",
        "",
        "### 实体类型（18类名词 + 4类动词）",
        "",
        "| 类型 | RDF类 | 实体数 | 说明 |",
        "|------|-------|--------|------|",
    ]
    
    type_counts = defaultdict(int)
    for entity in entity_index.values():
        symbol = entity['symbol']
        rdf_type = SYMBOL_TO_TYPE.get(symbol, 'Entity')
        type_counts[rdf_type] += 1
    
    for rdf_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        label = TYPE_LABELS.get(rdf_type, rdf_type)
        lines.append(f"| {label} | hs:{rdf_type} | {count} | |")
    
    lines.extend([
        "",
        "### 关系类型",
        "",
        "| 关系 | RDF属性 | 定义域 | 值域 |",
        "|------|---------|--------|------|",
        "| 父子 | hs:fatherOf | Person | Person |",
        "| 母子 | hs:motherOf | Person | Person |",
        "| 兄弟 | hs:brotherOf | Person | Person |",
        "| 夫妻 | hs:spouseOf | Person | Person |",
        "| 君臣 | hs:serves | Person | Person |",
        "| 敌对 | hs:enemyOf | Person | Person |",
        "| 联盟 | hs:alliedWith | Person | Person |",
        "| 师徒 | hs:teacherOf | Person | Person |",
        "| 封赏 | hs:appointedBy | Person | Person |",
        "| 出生于 | hs:bornIn | Person | Time |",
        "| 卒于 | hs:diedIn | Person | Time |",
        "",
        "## 文件说明",
        "- `hanshu_ontology.ttl` — OWL/RDF 本体文件（TTL格式）",
        "",
        f"## 统计",
        f"- 实体类型：{len(type_counts)} 类",
        f"- 实体总数：{len(entity_index)} 个",
        f"- 名词标注：{vocab_summary['metadata']['total_nouns']} 次",
        f"- 动词标注：{vocab_summary['metadata']['total_verbs']} 次",
    ])
    
    with open(ONT_DIR / "README.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    print("=== M5-1/2/3: 本体构造 + 分类树 + 生卒年推断 ===")
    
    entity_index = load_entity_index()
    vocab_summary = load_vocab_summary()
    
    # M5-1: 本体构造
    n_types, n_instances = build_ontology_tll(entity_index)
    build_ontology_md(entity_index, vocab_summary)
    print(f"  本体 TTL：{n_types} 类型，{n_instances} 实例")
    
    # M5-2: 分类树
    n_persons = build_taxonomy(entity_index)
    print(f"  分类树：{n_persons} 人物")
    
    # M5-3: 生卒年推断
    n_known, n_inferred = infer_lifespans()
    print(f"  生卒年：{n_known} 已知 + {n_inferred} 推断")
    
    print(f"\n=== M5-1/2/3 完成 ===")

if __name__ == '__main__':
    main()
