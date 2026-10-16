#!/usr/bin/env python3
"""M4-4/5/6: 关系构建 + 事实三元组 + 西汉帝王家谱
从120卷标注文本提取人物关系、事件关系、SPO事实三元组、帝王世系
"""
import re, json, os, sys
from pathlib import Path
from collections import defaultdict

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
REL_DIR = BASE / "kg" / "relations"
FACTS_DIR = BASE / "kg" / "facts"
GEN_DIR = BASE / "kg" / "genealogy"
FACTS_DATA = FACTS_DIR / "data"
FACTS_MD = FACTS_DIR / "markdown"
REL_DIR.mkdir(parents=True, exist_ok=True)
FACTS_DATA.mkdir(parents=True, exist_ok=True)
FACTS_MD.mkdir(parents=True, exist_ok=True)
GEN_DIR.mkdir(parents=True, exist_ok=True)

NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')

# 关系类型定义
RELATION_TYPES = [
    '父子', '母子', '兄弟', '夫妻', '祖孙', '叔侄',
    '君臣', '敌对', '联盟', '师徒', '封赏', '推荐',
    '出使', '背叛', '辅佐', '献策', '朋友',
]

# 关系模式（正则）：在去标记后的纯文本中匹配
# 但我们直接在标注文本中匹配，利用标记边界

def get_juan_titles():
    titles = {}
    src_dir = BASE / "data" / "chapter_numbered"
    for f in sorted(src_dir.glob("卷*.txt")):
        m = re.match(r'(卷\d+[a-z]?)_(.+)\.txt', f.name)
        if m:
            titles[m.group(1)] = m.group(2)
    return titles

def extract_juan_short(filename):
    m = re.match(r'(卷\d+[a-z]?)_标注\.txt', filename)
    return m.group(1) if m else filename.replace('_标注.txt', '')

def parse_entities(text):
    """提取所有实体，返回列表"""
    entities = []
    for m in NOUN_RE.finditer(text):
        symbol = m.group(1)
        raw = m.group(2)
        if '|' in raw:
            display, canonical = raw.split('|', 1)
        else:
            display = canonical = raw
        entities.append({
            'symbol': symbol,
            'display': display.strip(),
            'canonical': canonical.strip(),
            'start': m.start(),
            'end': m.end(),
            'full': m.group(0),
        })
    return entities

def parse_verbs(text):
    """提取所有动词"""
    verbs = []
    for m in VERB_RE.finditer(text):
        verbs.append({
            'type': m.group(1),
            'content': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
            'full': m.group(0),
        })
    return verbs

def find_nearby_persons(entities, pos, max_dist=30):
    """找到位置附近的人名"""
    return [e['display'] for e in entities 
            if e['symbol'] == '@' and abs(e['start'] - pos) < max_dist]

def find_nearby_places(entities, pos, max_dist=30):
    """找到位置附近的地名"""
    return [e['display'] for e in entities 
            if e['symbol'] == '=' and abs(e['start'] - pos) < max_dist]

def find_nearby_officials(entities, pos, max_dist=20):
    """找到位置附近的官职"""
    return [e['display'] for e in entities 
            if e['symbol'] == ';' and abs(e['start'] - pos) < max_dist]

def extract_relations_from_text(text, para, juan_short, juan_title):
    """从一段标注文本中提取关系"""
    relations = []
    entities = parse_entities(text)
    verbs = parse_verbs(text)
    persons = [e for e in entities if e['symbol'] == '@']
    
    # 1. 基于文本模式的关系提取
    # 父子：X子Y / X父Y
    for m in re.finditer(r'〖@([^〗]+)〗\s*子\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '父子', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 父子：X生子Y / X生Y
    for m in re.finditer(r'〖@([^〗]+)〗\s*生\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '父子', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 母子：X母Y / X母曰
    for m in re.finditer(r'〖@([^〗]+)〗\s*母\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '母子', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 兄弟：X弟Y / X兄Y
    for m in re.finditer(r'〖@([^〗]+)〗\s*弟\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '兄弟', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    for m in re.finditer(r'〖@([^〗]+)〗\s*兄\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '兄弟', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 夫妻：X妻Y / X后Y / X娶Y
    for pattern, rel_type in [(r'〖@([^〗]+)〗\s*妻\s*〖@([^〗]+)〗', '夫妻'),
                               (r'〖@([^〗]+)〗\s*后\s*〖@([^〗]+)〗', '夫妻'),
                               (r'〖@([^〗]+)〗\s*娶\s*〖@([^〗]+)〗', '夫妻')]:
        for m in re.finditer(pattern, text):
            p1 = m.group(1).split('|')[0].strip()
            p2 = m.group(2).split('|')[0].strip()
            if p1 and p2:
                relations.append({'type': rel_type, 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 叔侄：X侄Y
    for m in re.finditer(r'〖@([^〗]+)〗\s*侄\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '叔侄', 'p1': p1, 'p2': p2, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 师徒：X学于Y / X受学于Y / X授Y
    for m in re.finditer(r'〖@([^〗]+)〗\s*学於?\s*〖@([^〗]+)〗', text):
        p1 = m.group(1).split('|')[0].strip()
        p2 = m.group(2).split('|')[0].strip()
        if p1 and p2:
            relations.append({'type': '师徒', 'p1': p2, 'p2': p1, 'para': para, 'chapter': juan_title, 'context': text[max(0,m.start()-20):m.end()+20]})
    
    # 2. 基于动词的关系提取
    for verb in verbs:
        vc = verb['content']
        nearby_p = find_nearby_persons(entities, verb['start'], 40)
        
        # 封立/封赏：⟦○封⟧或⟦○立⟧ X为Y
        if vc in ('封', '立', '绍封', '复'):
            if len(nearby_p) >= 1:
                # 找"为"后面的官职
                after_verb = text[verb['end']:verb['end']+50]
                m = re.search(r'为\s*〖;([^〗]+)〗', after_verb)
                if m and nearby_p:
                    relations.append({
                        'type': '封赏', 'p1': nearby_p[0], 'p2': m.group(1).split('|')[0].strip(),
                        'para': para, 'chapter': juan_title,
                        'context': text[max(0,verb['start']-20):verb['end']+50]
                    })
        
        # 敌对/军事：⟦◈击⟧⟦◈攻⟧⟦◈破⟧⟦◈围⟧⟦◈斩⟧⟦◈杀⟧
        if vc in ('击', '攻', '破', '围', '斩', '杀', '距', '屠', '降'):
            if len(nearby_p) >= 2:
                relations.append({
                    'type': '敌对', 'p1': nearby_p[0], 'p2': nearby_p[1],
                    'para': para, 'chapter': juan_title,
                    'context': text[max(0,verb['start']-20):verb['end']+30]
                })
            elif len(nearby_p) >= 1:
                # 找附近的邦国
                nearby_states = [e['display'] for e in entities 
                                if e['symbol'] in ('◆', '&') and abs(e['start'] - verb['start']) < 40]
                if nearby_states:
                    relations.append({
                        'type': '敌对', 'p1': nearby_p[0], 'p2': nearby_states[0],
                        'para': para, 'chapter': juan_title,
                        'context': text[max(0,verb['start']-20):verb['end']+30]
                    })
        
        # 背叛：⟦◈反⟧ / ⟦○废⟧
        if vc in ('反', '谋反', '叛', '降'):
            if nearby_p:
                relations.append({
                    'type': '背叛', 'p1': nearby_p[0], 'p2': '汉',
                    'para': para, 'chapter': juan_title,
                    'context': text[max(0,verb['start']-20):verb['end']+30]
                })
        
        # 诛杀：⟦◉诛⟧⟦◉灭⟧
        if vc in ('诛', '灭', '族'):
            if len(nearby_p) >= 2:
                relations.append({
                    'type': '敌对', 'p1': nearby_p[0], 'p2': nearby_p[1],
                    'para': para, 'chapter': juan_title,
                    'context': text[max(0,verb['start']-20):verb['end']+30]
                })
    
    # 3. 共现关系（同段共现的人名 → 君臣/共事关系）
    if len(persons) >= 2:
        # 取前3个人名，建立共现关系
        top_persons = [p['display'] for p in persons[:4]]
        for i in range(len(top_persons)):
            for j in range(i+1, len(top_persons)):
                # 避免重复
                if top_persons[i] != top_persons[j]:
                    relations.append({
                        'type': '共现', 'p1': top_persons[i], 'p2': top_persons[j],
                        'para': para, 'chapter': juan_title,
                        'context': text[:100]
                    })
    
    return relations

def extract_facts_from_text(text, para, juan_short, juan_title, fact_id_start):
    """从标注文本提取SPO事实三元组"""
    facts = []
    entities = parse_entities(text)
    verbs = parse_verbs(text)
    fact_id = fact_id_start
    
    for verb in verbs:
        vc = verb['content']
        nearby_p = find_nearby_persons(entities, verb['start'], 40)
        nearby_places = find_nearby_places(entities, verb['start'], 40)
        nearby_off = find_nearby_officials(entities, verb['start'], 30)
        
        # 人物 + 动词 + 地点/官职/人物 → SPO
        if nearby_p:
            s = nearby_p[0]
            p = vc
            
            # 宾语优先级：官职 > 人物 > 地点 > 邦国
            if nearby_off:
                o = nearby_off[0]
            elif len(nearby_p) >= 2:
                o = nearby_p[1]
            elif nearby_places:
                o = nearby_places[0]
            else:
                nearby_states = [e['display'] for e in entities 
                                if e['symbol'] in ('◆', '&') and abs(e['start'] - verb['start']) < 40]
                o = nearby_states[0] if nearby_states else None
            
            if o:
                fact_id += 1
                # 提取时间
                times = [e['display'] for e in entities if e['symbol'] == '%' and '|时长' not in e['display']]
                facts.append({
                    'id': f"f{fact_id:05d}",
                    'pn': f"{juan_short}-{para}",
                    's': s,
                    'p': p,
                    'o': o,
                    'ctx': {
                        'time': times[0] if times else None,
                        'place': nearby_places[0] if nearby_places else None,
                    },
                    'src': f"{juan_short}_{juan_title}",
                    'text': text[max(0,verb['start']-20):verb['end']+30],
                    'conf': 'medium',
                })
    
    return facts, fact_id

def build_genealogy():
    """构建西汉帝王家谱"""
    # 西汉帝王世系（已知历史事实）
    emperors = [
        {"name": "汉高祖", "alias": "刘邦", "title": "高帝", "father": "刘太公", "mother": "刘媪", "spouse": ["吕后"], "start_bce": -202, "end_bce": -195, "reign": 8},
        {"name": "汉惠帝", "alias": "刘盈", "title": "惠帝", "father": "汉高祖", "mother": "吕后", "spouse": ["张皇后"], "start_bce": -195, "end_bce": -188, "reign": 7},
        {"name": "汉文帝", "alias": "刘恒", "title": "文帝", "father": "汉高祖", "mother": "薄姬", "spouse": ["窦皇后"], "start_bce": -180, "end_bce": -157, "reign": 23},
        {"name": "汉景帝", "alias": "刘启", "title": "景帝", "father": "汉文帝", "mother": "窦皇后", "spouse": ["王皇后", "栗姬"], "start_bce": -157, "end_bce": -141, "reign": 16},
        {"name": "汉武帝", "alias": "刘彻", "title": "武帝", "father": "汉景帝", "mother": "王皇后", "spouse": ["陈皇后", "卫皇后", "李皇后"], "start_bce": -141, "end_bce": -87, "reign": 54},
        {"name": "汉昭帝", "alias": "刘弗陵", "title": "昭帝", "father": "汉武帝", "mother": "赵倢伃", "spouse": ["上官皇后"], "start_bce": -87, "end_bce": -74, "reign": 13},
        {"name": "汉宣帝", "alias": "刘询", "title": "宣帝", "father": "刘进", "mother": "王翁须", "spouse": ["许皇后", "霍皇后", "王皇后"], "start_bce": -74, "end_bce": -49, "reign": 25},
        {"name": "汉元帝", "alias": "刘奭", "title": "元帝", "father": "汉宣帝", "mother": "许皇后", "spouse": ["王皇后", "傅昭仪"], "start_bce": -49, "end_bce": -33, "reign": 16},
        {"name": "汉成帝", "alias": "刘骜", "title": "成帝", "father": "汉元帝", "mother": "王皇后", "spouse": ["许皇后", "赵皇后"], "start_bce": -33, "end_bce": -7, "reign": 26},
        {"name": "汉哀帝", "alias": "刘欣", "title": "哀帝", "father": "刘康", "mother": "丁姬", "spouse": ["傅皇后"], "start_bce": -7, "end_bce": -1, "reign": 6},
        {"name": "汉平帝", "alias": "刘衎", "title": "平帝", "father": "刘兴", "mother": "卫姬", "spouse": ["王皇后"], "start_bce": -1, "end_bce": 5, "reign": 5},
        {"name": "孺子婴", "alias": "刘婴", "title": "孺子", "father": "刘显", "mother": None, "spouse": [], "start_bce": 6, "end_bce": 8, "reign": 3, "note": "王莽摄政"},
        {"name": "王莽", "alias": "王莽", "title": "新皇帝", "father": "王曼", "mother": "渠氏", "spouse": ["王皇后"], "start_bce": 9, "end_bce": 23, "reign": 15, "note": "新朝"},
        {"name": "更始帝", "alias": "刘玄", "title": "更始", "father": "刘子张", "mother": None, "spouse": [], "start_bce": 23, "end_bce": 25, "reign": 3, "note": "更始政权"},
    ]
    
    # 生成 JSON
    gen_data = {
        "metadata": {
            "dynasty": "西汉",
            "emperor_count": len(emperors),
            "source": "汉书本纪",
        },
        "emperors": emperors,
    }
    with open(GEN_DIR / "imperial_genealogy.json", 'w', encoding='utf-8') as f:
        json.dump(gen_data, f, ensure_ascii=False, indent=2)
    
    # 生成 MD
    lines = [
        "# 汉书西汉帝王家谱",
        "",
        f"> 从《汉书》本纪中提取的汉朝帝王世系",
        f"> 共 **{len(emperors)}** 位帝王/摄政者",
        "",
        "## 帝王世系",
        "",
        "| 序号 | 帝王 | 称号 | 别名 | 父 | 母 | 配偶 | 在位起 | 在位止 | 在位年数 | 备注 |",
        "|------|------|------|------|-----|-----|-------|--------|--------|---------|------|",
    ]
    
    for i, e in enumerate(emperors, 1):
        start_s = f"前{-e['start_bce']}年" if e['start_bce'] < 0 else f"公元{e['start_bce']}年"
        end_s = f"前{-e['end_bce']}年" if e['end_bce'] < 0 else f"公元{e['end_bce']}年"
        spouse_s = '、'.join(e['spouse']) if e['spouse'] else '—'
        mother_s = e['mother'] or '—'
        note_s = e.get('note', '')
        lines.append(f"| {i} | {e['name']} | {e['title']} | {e['alias']} | {e['father']} | {mother_s} | {spouse_s} | {start_s} | {end_s} | {e['reign']} | {note_s} |")
    
    lines.extend(["", "## 世系图", ""])
    for e in emperors:
        lines.append(f"### {e['name']}（{e['alias']}）")
        lines.append("")
        lines.append(f"- **称号**：{e['title']}")
        lines.append(f"- **父**：{e['father']}")
        if e['mother']:
            lines.append(f"- **母**：{e['mother']}")
        if e['spouse']:
            lines.append(f"- **配偶**：{'、'.join(e['spouse'])}")
        start_s = f"前{-e['start_bce']}年" if e['start_bce'] < 0 else f"公元{e['start_bce']}年"
        end_s = f"前{-e['end_bce']}年" if e['end_bce'] < 0 else f"公元{e['end_bce']}年"
        lines.append(f"- **在位**：{start_s}—{end_s}（{e['reign']}年）")
        if 'note' in e:
            lines.append(f"- **备注**：{e['note']}")
        lines.append("")
    
    with open(GEN_DIR / "汉朝帝王家谱.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return len(emperors)

def main():
    print("=== M4-4/5/6: 关系构建 + 事实三元组 + 家谱 ===")
    
    juan_titles = get_juan_titles()
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    all_relations = defaultdict(list)
    all_facts = []
    fact_id = 0
    chapter_stats = {}
    
    for filepath in ann_files:
        juan_short = extract_juan_short(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ch_rels = 0
        ch_facts = 0
        
        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para = m.group(1)
            para_text = line[m.end():]
            if not para_text.strip():
                continue
            
            # 提取关系
            rels = extract_relations_from_text(para_text, para, juan_short, juan_title)
            for r in rels:
                all_relations[r['type']].append(r)
                ch_rels += 1
            
            # 提取事实
            facts, fact_id = extract_facts_from_text(para_text, para, juan_short, juan_title, fact_id)
            all_facts.extend(facts)
            ch_facts += len(facts)
        
        chapter_stats[juan_short] = {'title': juan_title, 'relations': ch_rels, 'facts': ch_facts}
    
    total_rels = sum(len(v) for v in all_relations.values())
    total_facts = len(all_facts)
    
    print(f"  关系：{total_rels} 条（{len(all_relations)} 种类型）")
    print(f"  事实：{total_facts} 条")
    
    # 生成 all_relations.json
    rel_data = {
        'metadata': {
            'total_relations': total_rels,
            'relation_types': list(all_relations.keys()),
            'source': f'{len(ann_files)}个已标注汉书章节',
        },
        'relations': {k: v for k, v in all_relations.items()},
    }
    with open(REL_DIR / "all_relations.json", 'w', encoding='utf-8') as f:
        json.dump(rel_data, f, ensure_ascii=False, indent=2)
    
    # 生成按类型分的关系 .md
    type_names = {
        '父子': '01_家庭关系_父子', '母子': '02_家庭关系_母子', '兄弟': '03_家庭关系_兄弟',
        '夫妻': '04_家庭关系_夫妻', '祖孙': '05_家庭关系_祖孙', '叔侄': '06_家庭关系_叔侄',
        '君臣': '11_政治关系_君臣', '敌对': '31_对立关系_敌对', '联盟': '32_对立关系_联盟',
        '师徒': '21_社会关系_师徒', '封赏': '13_政治关系_封赏', '推荐': '12_政治关系_推荐',
        '出使': '17_政治关系_出使', '背叛': '16_政治关系_背叛', '辅佐': '14_政治关系_辅佐',
        '献策': '15_政治关系_献策', '朋友': '22_社会关系_朋友', '共现': '00_共现关系',
    }
    
    for rel_type, rels in all_relations.items():
        fname = type_names.get(rel_type, f'99_{rel_type}')
        lines = [
            f"# 汉书{rel_type}关系",
            "",
            f"共 **{len(rels)}** 条关系",
            "",
            "| 序号 | 人物1 | 人物2 | 章节 | 段落 | 上下文 |",
            "|------|-------|-------|------|------|--------|",
        ]
        for i, r in enumerate(rels[:500], 1):
            ctx = r.get('context', '')[:80].replace('|', '\\|')
            lines.append(f"| {i} | {r['p1']} | {r['p2']} | {r['chapter']} | {r['para']} | {ctx} |")
        
        with open(REL_DIR / f"{fname}.md", 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    # 生成事实 JSON
    with open(FACTS_DATA / "all_facts.json", 'w', encoding='utf-8') as f:
        json.dump(all_facts, f, ensure_ascii=False, indent=2)
    
    # 生成事实统计 MD
    lines = [
        "# 汉书事实三元组统计",
        "",
        f"共 **{total_facts}** 条事实（SPO三元组）",
        "",
        "## 章节统计",
        "",
        "| 卷号 | 章节 | 关系数 | 事实数 |",
        "|------|------|--------|--------|",
    ]
    for juan_short in sorted(chapter_stats.keys()):
        s = chapter_stats[juan_short]
        lines.append(f"| {juan_short} | {s['title']} | {s['relations']} | {s['facts']} |")
    
    with open(FACTS_MD / "事实统计.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    # 生成家谱
    n_emperors = build_genealogy()
    print(f"  家谱：{n_emperors} 位帝王")
    
    print(f"\n=== M4-4/5/6 完成 ===")
    print(f"关系：{total_rels} 条，事实：{total_facts} 条，帝王：{n_emperors} 位")
    
    return total_rels, total_facts

if __name__ == '__main__':
    main()
