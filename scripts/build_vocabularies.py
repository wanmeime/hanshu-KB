#!/usr/bin/env python3
"""M4-1: 从120卷标注文件提取实体，生成18类词表 + entity_index.json"""
import re, json, os, sys
from pathlib import Path
from collections import defaultdict

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
VOCAB_DIR = BASE / "kg" / "vocabularies"
ENTITIES_DIR = BASE / "kg" / "entities"

SYMBOL_TO_VOCAB = {
    '@': ('01_人名词表', '人名'),
    '=': ('02_地名词表', '地名'),
    ';': ('03_官职词表', '官职'),
    '%': ('04_时间词表', '时间'),
    '&': ('05_朝代词表', '朝代'),
    '^': ('06_名物词表', '制度'),
    '~': ('07_族群词表', '族群'),
    '•': ('08_器物词表', '器物'),
    '!': ('09_天文词表', '天文'),
    '#': ('10_身份词表', '身份'),
    '+': ('11_生物词表', '生物'),
    '?': ('12_神话词表', '神话'),
    '{': ('13_典籍词表', '典籍'),
    ':': ('14_礼仪词表', '礼仪'),
    '[': ('15_刑法词表', '刑法'),
    '_': ('16_思想词表', '思想'),
    '◆': ('17_邦国词表', '邦国'),
    '$': ('18_数量词表', '数量'),
}

VERB_TYPES = {
    '○': '政治',
    '◈': '军事',
    '◉': '刑罚',
    '◇': '经济',
}

# 正则：〖TYPE content〗  和  ⟦TYPE content⟧
NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')

def extract_juan_name(filename):
    """从文件名提取卷短名，如 卷001_标注.txt -> 卷001"""
    m = re.match(r'(卷\d+[a-z]?)_标注\.txt', filename)
    return m.group(1) if m else filename.replace('_标注.txt', '')

def extract_juan_title(filename):
    """从底本文件名提取完整标题"""
    return filename.replace('.txt', '')

def get_juan_titles():
    """获取卷号到标题的映射"""
    titles = {}
    src_dir = BASE / "data" / "chapter_numbered"
    for f in sorted(src_dir.glob("卷*.txt")):
        short = re.match(r'(卷\d+[a-z]?)_', f.name)
        if short:
            titles[short.group(1)] = f.stem
    return titles

def parse_annotation_file(filepath):
    """解析标注文件，返回 (实体列表, 动词列表, 段落数)"""
    entities = []  # [(symbol, display, canonical, para, context)]
    verbs = []     # [(vtype, content, para, context)]
    para_count = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    current_para = "0"
    lines = content.split('\n')
    for line in lines:
        m = PARA_RE.match(line)
        if m:
            current_para = m.group(1)
            para_count += 1
        
        # 提取名词实体
        for match in NOUN_RE.finditer(line):
            symbol = match.group(1)
            raw = match.group(2)
            if '|' in raw:
                parts = raw.split('|', 1)
                display = parts[0]
                canonical = parts[1].strip()
            else:
                display = raw
                canonical = raw
            
            # 获取上下文（前后各30字符）
            start = max(0, match.start() - 30)
            end = min(len(line), match.end() + 30)
            ctx = line[start:end]
            
            entities.append((symbol, display, canonical, current_para, ctx))
        
        # 提取动词
        for match in VERB_RE.finditer(line):
            vtype = match.group(1)
            vcontent = match.group(2)
            start = max(0, match.start() - 30)
            end = min(len(line), match.end() + 30)
            ctx = line[start:end]
            verbs.append((vtype, vcontent, current_para, ctx))
    
    return entities, verbs, para_count

def build_vocabularies():
    """主函数：构建词表和实体索引"""
    print("=== M4-1: 词表构建 + 实体索引 ===")
    
    juan_titles = get_juan_titles()
    
    # 数据结构：{symbol: {display_name: {canonical, count, chapters: set, examples: list}}}
    vocab_data = {s: defaultdict(lambda: {'canonical': '', 'count': 0, 'chapters': set(), 'examples': []}) for s in SYMBOL_TO_VOCAB}
    verb_data = {v: defaultdict(lambda: {'count': 0, 'chapters': set(), 'examples': []}) for v in VERB_TYPES}
    
    # 实体索引
    entity_index = {}
    total_nouns = 0
    total_verbs = 0
    chapter_stats = {}
    
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    print(f"找到 {len(ann_files)} 个标注文件")
    
    for filepath in ann_files:
        juan_short = extract_juan_name(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        
        entities, verbs, para_count = parse_annotation_file(filepath)
        
        ch_nouns = 0
        ch_verbs = 0
        
        for symbol, display, canonical, para, ctx in entities:
            if not display.strip():
                continue
            entry = vocab_data[symbol][display]
            entry['count'] += 1
            if canonical and not entry['canonical']:
                entry['canonical'] = canonical
            entry['chapters'].add(juan_title)
            if len(entry['examples']) < 3:
                entry['examples'].append(ctx)
            ch_nouns += 1
            
            # 实体索引
            key = f"{symbol}{display}"
            if key not in entity_index:
                entity_index[key] = {
                    'type': SYMBOL_TO_VOCAB[symbol][1],
                    'symbol': symbol,
                    'display': display,
                    'canonical': canonical,
                    'count': 0,
                    'chapters': []
                }
            entity_index[key]['count'] += 1
            if canonical and not entity_index[key]['canonical']:
                entity_index[key]['canonical'] = canonical
            if juan_title not in entity_index[key]['chapters']:
                entity_index[key]['chapters'].append(juan_title)
        
        for vtype, vcontent, para, ctx in verbs:
            if not vcontent.strip():
                continue
            entry = verb_data[vtype][vcontent]
            entry['count'] += 1
            entry['chapters'].add(juan_title)
            if len(entry['examples']) < 3:
                entry['examples'].append(ctx)
            ch_verbs += 1
        
        total_nouns += ch_nouns
        total_verbs += ch_verbs
        chapter_stats[juan_title] = {'nouns': ch_nouns, 'verbs': ch_verbs, 'paras': para_count}
    
    print(f"总计：名词 {total_nouns} 次，动词 {total_verbs} 次")
    
    # 生成词表 .md 文件
    VOCAB_DIR.mkdir(parents=True, exist_ok=True)
    
    for symbol, (vocab_name, type_name) in SYMBOL_TO_VOCAB.items():
        entries = vocab_data[symbol]
        sorted_entries = sorted(entries.items(), key=lambda x: -x[1]['count'])
        
        total_count = sum(e['count'] for e in entries.values())
        
        md_lines = [
            f"# 汉书{type_name}词表",
            "",
            f"> 标记符号：`〖{symbol}词条〗`  ",
            f"> 词条总数：**{len(entries)}**  ",
            f"> 总出现次数：**{total_count}**  ",
            f"> 数据来源：120 个已标注章节",
            "",
        ]
        
        for i, (display, entry) in enumerate(sorted_entries[:500], 1):
            canonical_str = f"（规范名：{entry['canonical']}）" if entry['canonical'] and entry['canonical'] != display else ""
            chapters_str = ', '.join(sorted(entry['chapters']))
            
            md_lines.extend([
                f"## {i}. {display}",
                "",
                f"**出现次数**：{entry['count']} 次",
                "",
                f"**出现章节**：{chapters_str}",
                "",
            ])
            
            if entry['examples']:
                md_lines.append("**典型用例**：")
                md_lines.append("")
                for ex in entry['examples']:
                    md_lines.append(f"- {ex}")
                md_lines.append("")
        
        filepath = VOCAB_DIR / f"{vocab_name}.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        print(f"  生成 {vocab_name}.md：{len(entries)} 词条，{total_count} 次")
    
    # 生成动词词表
    verb_total = 0
    for vtype, type_name in VERB_TYPES.items():
        entries = verb_data[vtype]
        sorted_entries = sorted(entries.items(), key=lambda x: -x[1]['count'])
        total_count = sum(e['count'] for e in entries.values())
        verb_total += total_count
        
        md_lines = [
            f"# 汉书{type_name}动词词表",
            "",
            f"> 标记符号：`⟦{vtype}词条⟧`  ",
            f"> 词条总数：**{len(entries)}**  ",
            f"> 总出现次数：**{total_count}**  ",
            f"> 数据来源：120 个已标注章节",
            "",
        ]
        
        for i, (display, entry) in enumerate(sorted_entries, 1):
            chapters_str = ', '.join(sorted(entry['chapters']))
            md_lines.extend([
                f"## {i}. {display}",
                "",
                f"**出现次数**：{entry['count']} 次",
                "",
                f"**出现章节**：{chapters_str}",
                "",
            ])
            if entry['examples']:
                md_lines.append("**典型用例**：")
                md_lines.append("")
                for ex in entry['examples']:
                    md_lines.append(f"- {ex}")
                md_lines.append("")
        
        filepath = VOCAB_DIR / f"19_{type_name}动词词表.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        print(f"  生成 19_{type_name}动词词表.md：{len(entries)} 词条，{total_count} 次")
    
    # 生成 entity_index.json
    entity_index_path = ENTITIES_DIR / "entity_index.json"
    with open(entity_index_path, 'w', encoding='utf-8') as f:
        json.dump(entity_index, f, ensure_ascii=False, indent=2)
    print(f"  生成 entity_index.json：{len(entity_index)} 个实体")
    
    # 生成词表数据 JSON
    vocab_json = {
        'metadata': {
            'total_nouns': total_nouns,
            'total_verbs': total_verbs,
            'total_entities': len(entity_index),
            'chapters': len(ann_files),
        },
        'vocabularies': {},
        'verbs': {},
    }
    for symbol, (vocab_name, type_name) in SYMBOL_TO_VOCAB.items():
        entries = vocab_data[symbol]
        vocab_json['vocabularies'][type_name] = {
            'symbol': symbol,
            'count': len(entries),
            'total_occurrences': sum(e['count'] for e in entries.values()),
        }
    for vtype, type_name in VERB_TYPES.items():
        entries = verb_data[vtype]
        vocab_json['verbs'][type_name] = {
            'symbol': vtype,
            'count': len(entries),
            'total_occurrences': sum(e['count'] for e in entries.values()),
        }
    
    vocab_json_path = VOCAB_DIR / "data" / "vocab_summary.json"
    vocab_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(vocab_json_path, 'w', encoding='utf-8') as f:
        json.dump(vocab_json, f, ensure_ascii=False, indent=2)
    
    # 生成章节统计
    stats_path = BASE / "kg" / "data" / "chapter_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(chapter_stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== M4-1 完成 ===")
    print(f"名词实体：{total_nouns} 次，{len(entity_index)} 个唯一实体")
    print(f"动词实体：{total_verbs} 次")
    print(f"词表文件：{len(SYMBOL_TO_VOCAB) + len(VERB_TYPES)} 个")
    
    return total_nouns, total_verbs, len(entity_index)

if __name__ == '__main__':
    build_vocabularies()
