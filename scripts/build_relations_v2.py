#!/usr/bin/env python3
"""关系重构 v2：去共现水分，扩充语义关系
- 从120卷标注文本提取语义关系（父子/母子/兄弟/夫妻/祖孙/叔侄/君臣/封赏/敌对/联盟/背叛/献策/推荐/师徒/辅佐/出使/朋友）
- 共现关系单独存放到 co_occurrence.json
- 同一对(p1,p2)在同一卷同一段去重，优先语义关系
"""
import re, json, os, glob
from pathlib import Path
from collections import defaultdict

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
REL_DIR = BASE / "kg" / "relations"

NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')

# 语义关系类型优先级（数字越小优先级越高，去重时保留优先级高的）
REL_PRIORITY = {
    '父子': 1, '母子': 2, '兄弟': 3, '夫妻': 4, '祖孙': 5, '叔侄': 6,
    '君臣': 7, '封赏': 8, '敌对': 9, '背叛': 10, '联盟': 11,
    '献策': 12, '推荐': 13, '师徒': 14, '辅佐': 15, '出使': 16, '朋友': 17,
}

# 文本模式关系：宽松匹配，允许人名间有少量字符
# (pattern, rel_type, group1_idx, group2_idx) — group1为p1, group2为p2
TEXT_PATTERNS = [
    # 父子：X...子...Y (X是父, Y是子); X...生...Y (X生Y); X...父...Y (Y之父为X→X父Y); X之子Y
    (r'〖@([^〗]+)〗[^\n]{0,6}子[^\n]{0,4}〖@([^〗]+)〗', '父子', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}生[^\n]{0,4}〖@([^〗]+)〗', '父子', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}之子[^\n]{0,4}〖@([^〗]+)〗', '父子', 1, 2),
    # 母子：X...母...Y (X母Y); 母X生Y
    (r'〖@([^〗]+)〗[^\n]{0,6}母[^\n]{0,4}〖@([^〗]+)〗', '母子', 1, 2),
    (r'母〖@([^〗]+)〗[^\n]{0,6}生[^\n]{0,4}〖@([^〗]+)〗', '母子', 1, 2),
    # 兄弟：X...兄...Y; X...弟...Y; X与Y...兄弟
    (r'〖@([^〗]+)〗[^\n]{0,4}兄[^\n]{0,6}〖@([^〗]+)〗', '兄弟', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}弟[^\n]{0,6}〖@([^〗]+)〗', '兄弟', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}兄弟', '兄弟', 1, 2),
    # 夫妻：X...妻...Y; X...后...Y; X...娶...Y; X...妃...Y; X...嫁...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}妻[^\n]{0,4}〖@([^〗]+)〗', '夫妻', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}娶[^\n]{0,4}〖@([^〗]+)〗', '夫妻', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}妃[^\n]{0,4}〖@([^〗]+)〗', '夫妻', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}嫁[^\n]{0,4}〖@([^〗]+)〗', '夫妻', 1, 2),
    # 祖孙：X...孙...Y (X孙Y→X祖Y); X...祖...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}孙[^\n]{0,4}〖@([^〗]+)〗', '祖孙', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}祖[^\n]{0,4}〖@([^〗]+)〗', '祖孙', 1, 2),
    # 叔侄：X...叔...Y; X...侄...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}叔[^\n]{0,4}〖@([^〗]+)〗', '叔侄', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}侄[^\n]{0,4}〖@([^〗]+)〗', '叔侄', 1, 2),
    # 君臣：X...事...Y (Y事X→X君Y); X...仕...Y; X...臣...Y; X...相...Y (Y相X)
    (r'〖@([^〗]+)〗[^\n]{0,6}事[^\n]{0,4}〖@([^〗]+)〗', '君臣', 2, 1),
    (r'〖@([^〗]+)〗[^\n]{0,6}仕[^\n]{0,4}〖@([^〗]+)〗', '君臣', 2, 1),
    (r'〖@([^〗]+)〗[^\n]{0,6}臣[^\n]{0,4}〖@([^〗]+)〗', '君臣', 2, 1),
    (r'〖@([^〗]+)〗[^\n]{0,6}相[^\n]{0,4}〖@([^〗]+)〗', '君臣', 2, 1),
    # 推荐：X...荐...Y; X...举...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}荐[^\n]{0,4}〖@([^〗]+)〗', '推荐', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}举[^\n]{0,4}〖@([^〗]+)〗', '推荐', 1, 2),
    # 献策：X...说...Y; X...谏...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}说[^\n]{0,4}〖@([^〗]+)〗', '献策', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}谏[^\n]{0,4}〖@([^〗]+)〗', '献策', 1, 2),
    # 联盟：X与Y...盟; X与Y...约; X与Y...合
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}盟', '联盟', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}约', '联盟', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}合', '联盟', 1, 2),
    # 朋友：X与Y...友; X与Y...善; X与Y...交
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}友', '朋友', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}善', '朋友', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,4}与〖@([^〗]+)〗[^\n]{0,6}交', '朋友', 1, 2),
    # 师徒：X...学于...Y (X学于Y→Y师X); X...师...Y; X...弟子...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}学[於于][^\n]{0,4}〖@([^〗]+)〗', '师徒', 2, 1),
    (r'〖@([^〗]+)〗[^\n]{0,6}师[^\n]{0,4}〖@([^〗]+)〗', '师徒', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}弟子[^\n]{0,4}〖@([^〗]+)〗', '师徒', 1, 2),
    # 出使：X...使于...Y; X...遣...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}使[於于][^\n]{0,4}〖@([^〗]+)〗', '出使', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}遣[^\n]{0,4}〖@([^〗]+)〗', '出使', 1, 2),
    # 辅佐：X...辅...Y; X...佐...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}辅[^\n]{0,4}〖@([^〗]+)〗', '辅佐', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}佐[^\n]{0,4}〖@([^〗]+)〗', '辅佐', 1, 2),
    # 敌对（文本模式）：X...攻...Y; X...伐...Y; X...杀...Y; X...破...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}攻[^\n]{0,4}〖@([^〗]+)〗', '敌对', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}伐[^\n]{0,4}〖@([^〗]+)〗', '敌对', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}杀[^\n]{0,4}〖@([^〗]+)〗', '敌对', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}破[^\n]{0,4}〖@([^〗]+)〗', '敌对', 1, 2),
    # 背叛（文本模式）：X...叛...Y; X...反...Y
    (r'〖@([^〗]+)〗[^\n]{0,6}叛[^\n]{0,4}〖@([^〗]+)〗', '背叛', 1, 2),
    (r'〖@([^〗]+)〗[^\n]{0,6}反[^\n]{0,4}〖@([^〗]+)〗', '背叛', 1, 2),
]

# 动词关系：动词前人名(主语) + 动词后人名/邦国(宾语)
FENGSHANG_VERBS = {'封', '立', '嗣', '拜', '绍封', '复', '赐', '除'}
DIDUI_VERBS = {'击', '杀', '攻', '破', '伐', '围', '斩', '诛', '灭', '屠', '禽', '虏', '败', '击破', '破杀'}
BEIPAN_VERBS = {'反', '谋反', '叛', '弑', '篡'}

# 无效人名过滤字符
INVALID_CHARS = set('[]。：；\n〖〗⟦⟧')


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


def load_ruler_aliases():
    with open(BASE / "kg" / "chronology" / "data" / "reign_periods.json", encoding='utf-8') as f:
        rulers = json.load(f)['rulers']
    aliases = set()
    for info in rulers.values():
        for a in info.get('alias', []):
            aliases.add(a)
    return aliases


def valid_person(name):
    if not name or len(name) > 20:
        return False
    if any(c in name for c in INVALID_CHARS):
        return False
    return True


def parse_persons(text):
    """返回 [(display, start, end), ...] 仅人名"""
    persons = []
    for m in NOUN_RE.finditer(text):
        if m.group(1) == '@':
            raw = m.group(2)
            disp = raw.split('|')[0].strip()
            if valid_person(disp):
                persons.append((disp, m.start(), m.end()))
    return persons


def extract_relations_from_para(text, para, juan_short, juan_title, ruler_aliases):
    """从一段标注文本提取语义关系。context 用整段原文，保证 p1/p2 都在 context 中。"""
    relations = []
    persons = parse_persons(text)

    # 1. 文本模式关系
    for pattern, rel_type, g1, g2 in TEXT_PATTERNS:
        for m in re.finditer(pattern, text):
            p1 = m.group(g1).split('|')[0].strip()
            p2 = m.group(g2).split('|')[0].strip()
            full = m.group(0)
            # 误配守卫：
            # a) "X…子…Y"且Y后紧跟"男" → Y是母（"王夫人男"=王夫人之子），X父Y不成立
            if rel_type == '父子' and text[m.end():m.end() + 1] == '男':
                continue
            # b) "X…妻…"且妻后紧跟病/死/困等 → "X之妻生病/去世"，Y与夫妻关系无关
            if re.search(r'妻[病死困疾卒丧]', full):
                continue
            if p1 and p2 and p1 != p2 and valid_person(p1) and valid_person(p2):
                relations.append({
                    'type': rel_type, 'p1': p1, 'p2': p2,
                    'para': para, 'chapter': juan_title, 'context': text
                })

    # 2. 动词关系：动词前最近人名(主语) + 动词后最近人名/邦国(宾语)
    for vm in VERB_RE.finditer(text):
        vtype, vcontent = vm.group(1), vm.group(2).strip()
        vstart, vend = vm.start(), vm.end()

        # 动词前最近的人名（主语）
        subj = None
        for disp, s, e in persons:
            if e <= vstart and vstart - e <= 30:
                subj = disp
                break

        # 动词后最近的人名（宾语）
        obj_person = None
        for disp, s, e in persons:
            if s >= vend and s - vend <= 30:
                obj_person = disp
                break

        # 动词后最近的邦国/势力（宾语）
        obj_state = None
        for m in NOUN_RE.finditer(text):
            if m.group(1) in ('◆', '&') and m.start() >= vend and m.start() - vend <= 30:
                obj_state = m.group(2).split('|')[0].strip()
                break

        # 封赏：主语 封/立/拜 宾语(人名)
        if vcontent in FENGSHANG_VERBS and subj and obj_person and subj != obj_person:
            relations.append({
                'type': '封赏', 'p1': subj, 'p2': obj_person,
                'para': para, 'chapter': juan_title, 'context': text
            })

        # 敌对：主语 击/杀/攻 宾语(人名或邦国)
        if vcontent in DIDUI_VERBS and subj:
            obj = obj_person or obj_state
            if obj and subj != obj:
                relations.append({
                    'type': '敌对', 'p1': subj, 'p2': obj,
                    'para': para, 'chapter': juan_title, 'context': text
                })

        # 背叛：主语 反/谋反/叛 → 背叛朝廷
        # p2 优先取动词后人名/邦国；否则取 context 中出现的朝廷标识(汉/新)；都没有则跳过
        if vcontent in BEIPAN_VERBS and subj:
            p2 = obj_person or obj_state
            if not p2:
                if '汉' in text:
                    p2 = '汉'
                elif '新' in text:
                    p2 = '新'
                else:
                    # 找段内邦国标识
                    for nm in NOUN_RE.finditer(text):
                        if nm.group(1) in ('◆', '&'):
                            cand = nm.group(2).split('|')[0].strip()
                            if cand:
                                p2 = cand
                                break
            if p2 and p2 in text and subj != p2:
                relations.append({
                    'type': '背叛', 'p1': subj, 'p2': p2,
                    'para': para, 'chapter': juan_title, 'context': text
                })

    # 3. 君臣关系：帝王(alias)与同段其他臣子
    ruler_in_para = [p for p, s, e in persons if p in ruler_aliases]
    if ruler_in_para:
        chenzi = [p for p, s, e in persons if p not in ruler_aliases]
        seen_ruler = set()
        for ruler in ruler_in_para:
            if ruler in seen_ruler:
                continue
            seen_ruler.add(ruler)
            seen_chen = set()
            for chen in chenzi:
                if chen in seen_chen or chen == ruler:
                    continue
                seen_chen.add(chen)
                relations.append({
                    'type': '君臣', 'p1': ruler, 'p2': chen,
                    'para': para, 'chapter': juan_title, 'context': text
                })

    return relations


def extract_cooccurrence_from_para(text, para, juan_title, ruler_aliases):
    """共现关系：同段人名两两配对（保留供分析用）"""
    persons = parse_persons(text)
    co_rels = []
    seen = set()
    # 取前6个人名，避免过多
    top = [p for p, s, e in persons[:6]]
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            if top[i] != top[j]:
                key = (top[i], top[j])
                if key not in seen:
                    seen.add(key)
                    co_rels.append({
                        'type': '共现', 'p1': top[i], 'p2': top[j],
                        'para': para, 'chapter': juan_title, 'context': text[:120]
                    })
    return co_rels


def main():
    print("=== 关系重构 v2：去共现水分 + 扩充语义关系 ===")
    juan_titles = get_juan_titles()
    ruler_aliases = load_ruler_aliases()
    print(f"帝王alias数: {len(ruler_aliases)}")

    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    print(f"标注文件数: {len(ann_files)}")

    # 按关系类型收集
    all_relations = defaultdict(list)
    all_cooccurrence = []
    chapter_stats = {}

    for filepath in ann_files:
        juan_short = extract_juan_short(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        ch_rels = 0
        ch_co = 0
        # 去重键：(p1, p2, para) → 保留优先级最高的关系类型
        para_dedup = {}

        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para = m.group(1)
            para_text = line[m.end():]
            if not para_text.strip():
                continue

            # 提取语义关系
            rels = extract_relations_from_para(para_text, para, juan_short, juan_title, ruler_aliases)
            for r in rels:
                key = (r['p1'], r['p2'], para)
                prio = REL_PRIORITY.get(r['type'], 99)
                if key not in para_dedup or prio < para_dedup[key][0]:
                    para_dedup[key] = (prio, r)

            # 提取共现关系
            co_rels = extract_cooccurrence_from_para(para_text, para, juan_title, ruler_aliases)
            all_cooccurrence.extend(co_rels)
            ch_co += len(co_rels)

        # 收集去重后的关系
        for prio, r in para_dedup.values():
            all_relations[r['type']].append(r)
            ch_rels += 1

        chapter_stats[juan_short] = {'title': juan_title, 'relations': ch_rels, 'cooccurrence': ch_co}

    total_rels = sum(len(v) for v in all_relations.values())
    total_co = len(all_cooccurrence)
    print(f"\n语义关系: {total_rels} 条 ({len(all_relations)} 种类型)")
    for k in sorted(all_relations.keys(), key=lambda x: -len(all_relations[x])):
        print(f"  {k}: {len(all_relations[k])}")
    print(f"共现关系: {total_co} 条")

    # 输出 all_relations.json（只含语义关系）
    rel_data = {
        'metadata': {
            'total_relations': total_rels,
            'relation_types': list(all_relations.keys()),
            'source': f'{len(ann_files)}个已标注汉书章节',
            'note': '语义关系（已去除共现水分）；共现关系见 co_occurrence.json',
        },
        'relations': {k: v for k, v in all_relations.items()},
    }
    with open(REL_DIR / "all_relations.json", 'w', encoding='utf-8') as f:
        json.dump(rel_data, f, ensure_ascii=False, indent=2)

    # 输出 co_occurrence.json
    co_data = {
        'metadata': {
            'total_relations': total_co,
            'relation_types': ['共现'],
            'source': f'{len(ann_files)}个已标注汉书章节',
            'note': '共现关系（同段人名两两配对），供分析用，不计入语义关系总数',
        },
        'relations': {'共现': all_cooccurrence},
    }
    with open(REL_DIR / "co_occurrence.json", 'w', encoding='utf-8') as f:
        json.dump(co_data, f, ensure_ascii=False, indent=2)

    # 输出各类型分文件 .md
    type_names = {
        '父子': '01_家庭关系_父子', '母子': '02_家庭关系_母子', '兄弟': '03_家庭关系_兄弟',
        '夫妻': '04_家庭关系_夫妻', '祖孙': '05_家庭关系_祖孙', '叔侄': '06_家庭关系_叔侄',
        '君臣': '11_政治关系_君臣', '推荐': '12_政治关系_推荐', '封赏': '13_政治关系_封赏',
        '辅佐': '14_政治关系_辅佐', '献策': '15_政治关系_献策', '背叛': '16_政治关系_背叛',
        '出使': '17_政治关系_出使', '师徒': '21_社会关系_师徒', '朋友': '22_社会关系_朋友',
        '敌对': '31_对立关系_敌对', '联盟': '32_对立关系_联盟',
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
            ctx = r.get('context', '')[:80].replace('|', '\\|').replace('\n', ' ')
            lines.append(f"| {i} | {r['p1']} | {r['p2']} | {r['chapter']} | {r['para']} | {ctx} |")
        with open(REL_DIR / f"{fname}.md", 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    # 共现关系 md
    lines = [
        "# 汉书共现关系",
        "",
        f"共 **{total_co}** 条共现关系（同段人名两两配对，供分析用）",
        "",
        "| 序号 | 人物1 | 人物2 | 章节 | 段落 | 上下文 |",
        "|------|-------|-------|------|------|--------|",
    ]
    for i, r in enumerate(all_cooccurrence[:500], 1):
        ctx = r.get('context', '')[:80].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {i} | {r['p1']} | {r['p2']} | {r['chapter']} | {r['para']} | {ctx} |")
    with open(REL_DIR / "00_共现关系.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n=== 完成 ===")
    print(f"语义关系: {total_rels} 条 → all_relations.json")
    print(f"共现关系: {total_co} 条 → co_occurrence.json")
    return total_rels, total_co


if __name__ == '__main__':
    main()
