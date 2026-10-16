#!/usr/bin/env python3
"""M4-7: 段落结构关系 — 生成段落级结构数据"""
import re, json, os
from pathlib import Path

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
STRUCT_DIR = BASE / "kg" / "structure"
STRUCT_DATA = STRUCT_DIR / "data"
STRUCT_DATA.mkdir(parents=True, exist_ok=True)

PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')
NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')

def get_juan_titles():
    titles = {}
    src_dir = BASE / "data" / "chapter_numbered"
    for f in sorted(src_dir.glob("卷*.txt")):
        m = re.match(r'(卷\d+[a-z]?)_(.+)\.txt', f.name)
        if m:
            titles[m.group(1)] = m.group(2)
    return titles

def main():
    print("=== M4-7: 段落结构关系 ===")
    juan_titles = get_juan_titles()
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    all_paragraphs = []
    sections_data = {}
    
    for filepath in ann_files:
        m = re.match(r'(卷\d+[a-z]?)_标注\.txt', filepath.name)
        if not m:
            continue
        juan_short = m.group(1)
        juan_title = juan_titles.get(juan_short, juan_short)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        paras = []
        prev_para = None
        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para_id = m.group(1)
            para_text = line[m.end():]
            if not para_text.strip():
                continue
            
            # 统计实体
            nouns = NOUN_RE.findall(para_text)
            verbs = VERB_RE.findall(para_text)
            persons = [n[1].split('|')[0] for n in nouns if n[0] == '@']
            
            para_data = {
                'chapter': juan_short,
                'title': juan_title,
                'para': para_id,
                'length': len(para_text),
                'noun_count': len(nouns),
                'verb_count': len(verbs),
                'persons': list(set(persons))[:10],
                'prev': prev_para,
            }
            paras.append(para_data)
            all_paragraphs.append(para_data)
            prev_para = para_id
        
        # 段落关系
        para_rels = []
        for i in range(len(paras) - 1):
            para_rels.append({
                'from': paras[i]['para'],
                'to': paras[i+1]['para'],
                'relation': 'next',
            })
        
        sections_data[juan_short] = {
            'title': juan_title,
            'para_count': len(paras),
            'total_length': sum(p['length'] for p in paras),
            'total_nouns': sum(p['noun_count'] for p in paras),
            'total_verbs': sum(p['verb_count'] for p in paras),
        }
        
        with open(STRUCT_DATA / f"paragraph_relations_{juan_short}.json", 'w', encoding='utf-8') as f:
            json.dump({
                'chapter': juan_short,
                'title': juan_title,
                'paragraphs': paras,
                'relations': para_rels,
            }, f, ensure_ascii=False, indent=2)
    
    # 生成 sections_data.json
    with open(STRUCT_DATA / "sections_data.json", 'w', encoding='utf-8') as f:
        json.dump(sections_data, f, ensure_ascii=False, indent=2)
    
    # 生成 README
    lines = [
        "# 汉书段落结构数据",
        "",
        f"共 {len(all_paragraphs)} 个段落，来自 {len(sections_data)} 个章节。",
        "",
        "## 文件说明",
        "- `paragraph_relations_{卷号}.json` — 每卷的段落级结构数据",
        "- `sections_data.json` — 章节级汇总数据",
        "",
        "## 章节统计",
        "",
        "| 卷号 | 章节 | 段落数 | 总字数 | 名词数 | 动词数 |",
        "|------|------|--------|--------|--------|--------|",
    ]
    for juan_short in sorted(sections_data.keys()):
        s = sections_data[juan_short]
        lines.append(f"| {juan_short} | {s['title']} | {s['para_count']} | {s['total_length']} | {s['total_nouns']} | {s['total_verbs']} |")
    
    with open(STRUCT_DIR / "README.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"  处理 {len(sections_data)} 卷，{len(all_paragraphs)} 个段落")
    print(f"\n=== M4-7 完成 ===")

if __name__ == '__main__':
    main()
