#!/usr/bin/env python3
"""M4-3: 事件提取 — 从120卷标注文本提取结构化历史事件
生成 events/data/{卷号}_{卷名}_事件索引.md + events/events_summary.json + events/事件时间索引.md
"""
import re, json, os, sys
from pathlib import Path
from collections import defaultdict

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
EVENTS_DIR = BASE / "kg" / "events"
EVENTS_DATA = EVENTS_DIR / "data"
EVENTS_DATA.mkdir(parents=True, exist_ok=True)

NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')
TITLE_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s*(.+)$')

SYMBOL_NAMES = {
    '@': '人名', '=': '地名', ';': '官职', '#': '身份', '%': '时间',
    '&': '朝代', '◆': '邦国', '^': '制度', '~': '族群', '•': '器物',
    '!': '天文', '?': '神话', '+': '生物', '{': '典籍', ':': '礼仪',
    '[': '刑法', '_': '思想', '$': '数量',
}

VERB_TYPES = {
    '○': ('政治', '政治活动'),
    '◈': ('军事', '战争'),
    '◉': ('刑罚', '政治整顿'),
    '◇': ('经济', '经济活动'),
}

# 事件类型推断
EVENT_TYPE_MAP = {
    '立': '继位/封立', '封': '封赏', '嗣': '继位', '薨': '逝世',
    '废': '废黜', '徙': '迁徙', '绍封': '绍封', '免': '免职',
    '复': '复封', '反': '叛乱', '谋反': '叛乱',
    '诛': '诛杀', '自杀': '自杀', '要斩': '处刑', '弃市': '处刑',
    '下狱死': '下狱', '斩': '战争', '击': '战争', '破': '战争',
    '攻': '战争', '围': '战争', '降': '投降', '杀': '战争',
    '赦': '赦免', '拜': '任命',
}

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

def parse_entities_in_text(text):
    """提取文本中的所有实体"""
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
            'type': SYMBOL_NAMES.get(symbol, '未知'),
            'display': display.strip(),
            'canonical': canonical.strip(),
            'pos': m.start(),
        })
    return entities

def parse_verbs_in_text(text):
    """提取文本中的所有动词"""
    verbs = []
    for m in VERB_RE.finditer(text):
        vtype = m.group(1)
        vcontent = m.group(2).strip()
        verbs.append({
            'type': vtype,
            'type_name': VERB_TYPES.get(vtype, ('未知', '未知'))[0],
            'content': vcontent,
            'pos': m.start(),
        })
    return verbs

def infer_event_name(verbs, persons, text):
    """推断事件名称"""
    if not verbs:
        if persons:
            return f"{persons[0]}相关记载"
        return "叙事段落"
    
    v = verbs[0]
    vcontent = v['content']
    
    # 根据动词内容推断事件类型
    for key, etype in EVENT_TYPE_MAP.items():
        if key in vcontent:
            if persons:
                return f"{persons[0]}{vcontent}"
            return vcontent
    
    if persons:
        return f"{persons[0]}{vcontent}"
    return vcontent

def infer_event_type(verbs, text):
    """推断事件类型"""
    if not verbs:
        return "叙事"
    
    v = verbs[0]
    vcontent = v['content']
    
    for key, etype in EVENT_TYPE_MAP.items():
        if key in vcontent:
            return etype
    
    return VERB_TYPES.get(v['type'], ('未知', '未知'))[1]

def extract_events_from_file(filepath, juan_short, juan_title):
    """从标注文件提取事件"""
    events = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    current_time = None
    current_para = "0"
    event_id = 0
    
    lines = content.split('\n')
    for line in lines:
        m = PARA_RE.match(line)
        if not m:
            continue
        
        current_para = m.group(1)
        para_text = line[m.end():]
        
        if not para_text.strip():
            continue
        
        entities = parse_entities_in_text(para_text)
        verbs = parse_verbs_in_text(para_text)
        
        # 提取时间
        times = [e for e in entities if e['symbol'] == '%']
        if times:
            # 取第一个非时长的时间作为当前时间
            for t in times:
                if '|时长' not in t['display'] and '时长' not in t['canonical']:
                    current_time = t['display']
                    break
        
        # 提取人名
        persons = [e['display'] for e in entities if e['symbol'] == '@']
        # 提取地名
        places = [e['display'] for e in entities if e['symbol'] == '=']
        # 提取邦国
        states = [e['display'] for e in entities if e['symbol'] in ('◆', '&')]
        
        # 只有包含动词或人名的段落才作为事件
        if not verbs and not persons:
            continue
        
        # 如果有多个动词，可能对应多个事件
        if verbs:
            for vi, verb in enumerate(verbs):
                event_id += 1
                
                # 找动词附近的人名
                nearby_persons = []
                for e in entities:
                    if e['symbol'] == '@' and abs(e['pos'] - verb['pos']) < 50:
                        nearby_persons.append(e['display'])
                if not nearby_persons:
                    nearby_persons = persons[:3]
                
                # 找动词附近的地名
                nearby_places = []
                for e in entities:
                    if e['symbol'] == '=' and abs(e['pos'] - verb['pos']) < 50:
                        nearby_places.append(e['display'])
                if not nearby_places:
                    nearby_places = places[:2]
                
                event_name = infer_event_name([verb], nearby_persons, para_text)
                event_type = infer_event_type([verb], para_text)
                
                events.append({
                    'id': f"{juan_short}-{event_id:03d}",
                    'para': current_para,
                    'name': event_name,
                    'type': event_type,
                    'time': current_time or '',
                    'persons': nearby_persons[:5],
                    'places': nearby_places[:3],
                    'states': states[:3],
                    'verb': verb['content'],
                    'verb_type': verb['type_name'],
                    'text': para_text[:200],
                })
        else:
            # 无动词但有人的段落（叙事/记载）
            event_id += 1
            event_name = f"{persons[0]}相关记载" if persons else "叙事"
            events.append({
                'id': f"{juan_short}-{event_id:03d}",
                'para': current_para,
                'name': event_name,
                'type': '叙事',
                'time': current_time or '',
                'persons': persons[:5],
                'places': places[:3],
                'states': states[:3],
                'verb': '',
                'verb_type': '',
                'text': para_text[:200],
            })
    
    return events

def generate_event_md(events, juan_short, juan_title):
    """生成单卷事件索引 .md"""
    lines = [
        f"# {juan_short}_{juan_title} 事件索引",
        "",
        f"共 **{len(events)}** 个事件",
        "",
        "## 事件列表概览",
        "",
        "| 事件ID | 事件名称 | 事件类型 | 时间 | 地点 | 主要人物 | 朝代 |",
        "|--------|---------|---------|------|------|---------|------|",
    ]
    
    for e in events:
        time_str = f"〖%{e['time']}〗" if e['time'] else "-"
        place_str = '、'.join(f"〖={p}〗" for p in e['places']) if e['places'] else "-"
        person_str = '、'.join(f"〖@{p}〗" for p in e['persons']) if e['persons'] else "-"
        state_str = '、'.join(f"〖&{s}〗" for s in e['states']) if e['states'] else "-"
        lines.append(f"| {e['id']} | {e['name']} | {e['type']} | {time_str} | {place_str} | {person_str} | {state_str} |")
    
    lines.extend(["", "## 事件详情", ""])
    for e in events:
        lines.extend([
            f"### {e['id']} {e['name']}",
            "",
            f"- **段落**：[{e['para']}]",
            f"- **类型**：{e['type']}",
            f"- **时间**：{e['time'] or '未标注'}",
            f"- **人物**：{'、'.join(e['persons']) if e['persons'] else '无'}",
            f"- **地点**：{'、'.join(e['places']) if e['places'] else '无'}",
            f"- **动词**：{e['verb'] or '无'}" + (f"（{e['verb_type']}）" if e['verb_type'] else ""),
            "",
        ])
    
    filepath = EVENTS_DATA / f"{juan_short}_{juan_title}_事件索引.md"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    print("=== M4-3: 事件提取 ===")
    
    juan_titles = get_juan_titles()
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    all_events = {}
    total_events = 0
    chapter_event_counts = {}
    
    for filepath in ann_files:
        juan_short = extract_juan_short(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        
        events = extract_events_from_file(filepath, juan_short, juan_title)
        all_events[juan_short] = {
            'title': juan_title,
            'count': len(events),
            'events': events,
        }
        total_events += len(events)
        chapter_event_counts[juan_short] = {
            'title': juan_title,
            'count': len(events),
        }
        
        generate_event_md(events, juan_short, juan_title)
    
    print(f"  处理 {len(ann_files)} 卷，共提取 {total_events} 个事件")
    
    # 生成 events_summary.json
    summary = {
        'metadata': {
            'total_events': total_events,
            'total_chapters': len(ann_files),
            'source': '120个已标注汉书章节',
        },
        'chapters': chapter_event_counts,
    }
    with open(EVENTS_DIR / "events_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成事件时间索引.md
    lines = [
        f"# 汉书全120卷事件时间索引",
        "",
        f"共 **{total_events}** 个事件，来自 **{len(ann_files)}** 个章节。",
        "",
        "## 章节索引",
        "",
        "| 编号 | 章节 | 事件数 |",
        "|------|------|--------|",
    ]
    
    for juan_short in sorted(chapter_event_counts.keys()):
        info = chapter_event_counts[juan_short]
        lines.append(f"| {juan_short} | [{info['title']}](data/{juan_short}_{info['title']}_事件索引.md) | {info['count']} |")
    
    with open(EVENTS_DIR / "事件时间索引.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    # 生成全量事件 JSON
    with open(EVENTS_DATA / "all_events.json", 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    
    print(f"  生成 {len(chapter_event_counts)} 个事件索引 .md")
    print(f"  生成 events_summary.json")
    print(f"  生成 事件时间索引.md")
    print(f"  生成 all_events.json")
    print(f"\n=== M4-3 完成 ===")
    
    return total_events

if __name__ == '__main__':
    main()
