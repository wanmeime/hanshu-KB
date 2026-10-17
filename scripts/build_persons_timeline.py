#!/usr/bin/env python3
"""人物一生轨迹时间线页生成器（对标 shiji-kb SKILL_W10y_时间线页建设）。

W10y 触发条件：一个人物有 ≥3 个事件，且跨越 ≥3 年 → 建时间线页。
输出：kg/applications/persons_timeline/<人名>.md + 索引 + 统计。

数据源：
- kg/events/data/all_events.json   事件（ attrs: id/para/type/time/persons/places/text ）
- kg/entities/entity_index.json    显示名→规范名（@ 类）
- kg/chronology/data/reign_periods.json 年号/君主纪年起始
- kg/chronology/data/year_ce_map.json  年号纪年→公元年
- kg/chronology/data/person_lifespan_events.json 生卒年（已知+推断）
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
KG = BASE / "kg"
OUT_DIR = KG / "applications" / "persons_timeline"

MIN_EVENTS = 3   # W10y 触发条件：≥3 个事件页
MIN_YEARS = 3    # 且跨越 ≥3 年

CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def cn_to_int(s):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == '元':
        return 1
    # 简单中文数字: 十一/二十/三十四
    if s == '十':
        return 10
    if '十' in s:
        parts = s.split('十')
        if len(parts) == 2:
            a = CN_NUM.get(parts[0], 1 if parts[0] == '' else None)
            b = CN_NUM.get(parts[1], 0 if parts[1] == '' else None)
            if a is not None and b is not None:
                return a * 10 + b
    if s == '初':
        return 1
    return CN_NUM.get(s)


SYM_CHARS = '@=;&%~•!?+◆{:[$#○◈◉◇]'


# 同指别名合并（标注定名分裂 → 正名页）
NAME_MERGE = {
    '骞': '张骞', '凤': '王凤', '王太后': '王政君', '许后': '许皇后',
    '郅支': '郅支单于',
}


def ruler_canonical(person):
    """残留帝王谥号简称/泛称 → reign 君主正名（高帝/高皇帝/孝文皇帝 等）。"""
    if re.match(r'^孝?(高帝|高皇帝)$', person):
        return '汉高祖'
    m = re.match(r'^孝?(惠|文|景|武|昭|宣|元|成|哀|平)(帝|皇帝)$', person)
    if m:
        return f"汉{m.group(1)}帝"
    return None

# 泛指/虚称停用（不建页）：非具体人物或跨多代君主
GENERIC_STOP = {'先帝', '君王', '长公主', '五帝', '文王', '武王', '周公',
                '燕王', '淮南王', '昌邑王', '齐王', '楚王', '赵王', '梁王',
                '定陶共王'}


def strip_markers(text):
    text = re.sub(r'〖([^〗]*?)〗', lambda m: m.group(1).split('|')[0].lstrip(SYM_CHARS), text)
    text = re.sub(r'⟦([^⟧]*?)⟧', lambda m: m.group(1).split('|')[0].strip('⟦⟧○◈◉◇' + SYM_CHARS), text)
    text = re.sub(r'〘([^〙]*?)〙', lambda m: m.group(1).split('|')[0].lstrip(SYM_CHARS), text)
    return text


def ce_year_label(ce):
    if ce is None:
        return '时间不详'
    if ce < 0:
        return f"前{-ce}年"
    return f"公元{ce}年"


class TimeResolver:
    """把 事件.time（如 秦二世元年/建元一年/汉十二年）解析为公元年。"""

    def __init__(self):
        self.ymap = json.loads((KG / "chronology/data/year_ce_map.json").read_text('utf-8'))
        rp = json.loads((KG / "chronology/data/reign_periods.json").read_text('utf-8'))
        self.rulers = rp['rulers']
        self.eras = rp['eras']
        self.alias = rp['aliases']
        # era → (start_bce, ruler)
        self.era_start = {e: (d['start_bce'], d.get('ruler', '')) for e, d in self.eras.items()}
        # 人物名 → ruler
        self.ruler_by_alias = {}
        for r, d in self.rulers.items():
            self.ruler_by_alias[r] = r
            for a in d.get('alias', []):
                self.ruler_by_alias[a] = r
        # 汉朝纪年（无年号时期）基准：汉高祖前206
        self.han_start = -206
        self.unresolved = Counter()

    def resolve(self, t):
        t = t.strip()
        if not t:
            return None, None
        if t in self.ymap:
            d = self.ymap[t]
            return d['ce_year'], t
        m = re.match(r'^(.+?)(元|[一二三四五六七八九十百]+|[\d]+)年$', t)
        if not m:
            self.unresolved[t] += 1
            return None, t
        token, num = m.group(1), cn_to_int(m.group(2))
        if num is None:
            self.unresolved[t] += 1
            return None, t
        # 年号纪年：token 是年号名
        if token in self.era_start:
            start, _ = self.era_start[token]
            return start + (num - 1), t
        # 君主纪年：token 是君主/别名（汉/秦/新/后/中…均常见）
        if token in self.ruler_by_alias:
            r = self.ruler_by_alias[token]
            d = self.rulers[r]
            return d['start_bce'] + (num - 1), t
        # 剥一层：token 尾部含 '帝/王/世' 前缀组合，如 秦二世
        m2 = re.match(r'^(秦|新|汉)?(.*?(?:世|帝|公|王))?$', token)
        base = self.ruler_by_alias.get(token)
        if base:
            d = self.rulers[base]
            return d['start_bce'] + (num - 1), t
        # token 为空（"即皇帝位元年"）或 汉朝默认纪年
        if token in ('汉', '', '汉高帝', '高帝'):
            return self.han_start + (num - 1), t
        self.unresolved[t] += 1
        return None, t


def pick_stage_name(name, text, subject):
    """节标题阶段名：优先动词名，跳过'X相关记载'式占位名，回退原文截句。"""
    if name and not name.endswith('相关记载') and not re.match(r'^(赦|杀|诛|击|伐|议事)$', name) :
        return name
    plain = strip_markers(text)
    snippet = re.split(r'[，。；！？]', plain)[0]
    snippet = re.sub(r'^是\S{0,2}[，]', '', snippet)
    return snippet[:12] or (name or '相关事件')


def main():
    events_data = json.loads((KG / "events/data/all_events.json").read_text('utf-8'))
    eidx = json.loads((KG / "entities/entity_index.json").read_text('utf-8'))
    canon = {k[1:]: v['canonical'] for k, v in eidx.items() if k.startswith('@')}
    lifespan = json.loads((KG / "chronology/data/person_lifespan_events.json").read_text('utf-8'))

    resolver = TimeResolver()
    title_of = {juan: d['title'] for juan, d in events_data.items()}

    # 展开：事件扁平列表（卷来源、解析年份）
    flat = []
    for juan, j in events_data.items():
        for ev in j['events']:
            t = ev.get('time', '').strip()
            if t:
                ce, label = resolver.resolve(t)
            else:
                ce, label = None, '时间不详'
            for p in ev.get('persons', []):
                flat.append({
                    'person': canon.get(p, p),
                    'display': p,
                    'juan': juan,
                    'title': j['title'],
                    'id': ev['id'],
                    'name': ev.get('name', ''),
                    'type': ev.get('type', ''),
                    'time': ev.get('time', ''),
                    'ce': ce,
                    'label': ce_year_label(ce) if ce is not None else label,
                    'places': ev.get('places', []),
                    'text': ev.get('text', ''),
                })

    # 按人物聚组（同人同事件只计一次：persons 字段可能含重复名）
    # 帝王类规格名统一：canon/alias → reign_periods 君主名（刘邦/沛公/高祖 → 汉高祖）
    by_person = defaultdict(list)
    seen_pe = set()
    for r in flat:
        person = r['person']
        person = resolver.ruler_by_alias.get(person, person)
        rc = ruler_canonical(person)
        if rc:
            person = rc
        if person in NAME_MERGE:
            person = NAME_MERGE[person]
        if person in GENERIC_STOP:
            continue
        key = (person, r['id'])
        if key in seen_pe:
            continue
        seen_pe.add(key)
        by_person[person].append(r)

    qualified = {}
    for person, recs in by_person.items():
        recs = sorted(recs, key=lambda r: (r['ce'] if r['ce'] is not None else 10 ** 9))
        years = {r['ce'] for r in recs if r['ce'] is not None}
        if len(recs) >= MIN_EVENTS and len(years) >= MIN_YEARS:
            qualified[person] = recs

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 清理旧生成文件
    for f in OUT_DIR.glob('*'):
        f.unlink() if f.name.endswith(('.md', '.json')) else None

    cn_ord = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
              '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
              '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十']

    pages = []
    for person in sorted(qualified, key=lambda p: -len(qualified[p])):
        recs = qualified[person]
        # 生卒年（仅采用已知历史事实口径）
        life = lifespan['known_lifespans'].get(person)
        life_note = ''
        if life and life.get('birth') is not None and life.get('death') is not None:
            b, d_ = life['birth'], life['death']
            life_note = f"\n> 生卒年：{ce_year_label(b).replace('年', '')} — {ce_year_label(d_).replace('年', '')}（{life.get('confidence', 'high')}）\n"

        time_range = [recs[0]['label'], next((r['label'] for r in reversed(recs) if r['ce'] is not None), recs[-1]['label'])]
        sources = sorted({r['title'] for r in recs})
        safe_name = person.replace('/', '_').replace(':', '_')
        pid = f"{safe_name}一生轨迹"

        lines = [
            "---",
            f'id: "{pid}"',
            "type: timeline",
            f"title: {pid}",
            f"subject: {person}",
            "subject_type: person",
            f'time_range: ["{time_range[0]}", "{time_range[1]}"]',
            f"sources: {json.dumps(sources, ensure_ascii=False)}",
            f"description: {person}跨越{len({r['ce'] for r in recs})}年、{len(recs)}个事件的汉书一生轨迹",
            "tags: [汉书, 时间线, 一生轨迹]",
            "quality: basic",
            "---",
            "",
            f"# {pid}",
            life_note,
            f"共 **{len(recs)}** 个事件（事件覆盖年数 {len({r['ce'] for r in recs if r['ce'] is not None})}），数据来源：{len(sources)} 篇章节。",
            "",
        ]
        # 按年聚合（同年事件合并为一个时间段；未解析时间的排最后）
        years_grouped = defaultdict(list)
        for r in recs:
            years_grouped[r['ce']].append(r)
        ordered = sorted(years_grouped.items(), key=lambda kv: (kv[0] is None, kv[0] if kv[0] is not None else 10 ** 9))

        ord_i = 0
        for ce, group in ordered:
            ord_i += 1
            ordn = cn_ord[ord_i - 1] if ord_i <= len(cn_ord) else str(ord_i)
            year_label = group[0]['label']
            stage = next((pick_stage_name(r['name'], r['text'], person)
                          for r in group if r['name'] and not r['name'].endswith('相关记载')),
                         pick_stage_name(group[0]['name'], group[0]['text'], person))
            lines.append(f"## {ordn}、{year_label} · {stage}")
            lines.append("")
            lines.append("| 事件 | 章节 | 类型 | 人物 | 地点 | 原文摘录 |")
            lines.append("|------|------|------|------|------|----------|")
            seen_ids = set()
            for r in sorted(group, key=lambda x: x['id']):
                if r['id'] in seen_ids:
                    continue
                seen_ids.add(r['id'])
                txt = strip_markers(r['text'])
                if len(txt) > 50:
                    txt = txt[:50] + '…'
                txt = txt.replace('|', '\\|')
                places = '、'.join(r['places'][:3]) if r['places'] else '—'
                lines.append(
                    f"[`{r['id']}`] | [[{r['title']}]] | {r['type'] or '—'} | {r['display']} | {places} | {txt or '—'} |")
            lines.append("")
        body = '\n'.join(lines)
        (OUT_DIR / f"{safe_name}.md").write_text(body + "\n", encoding='utf-8')
        pages.append({
            'person': person, 'file': f"{safe_name}.md", 'events': len(recs),
            'years': sorted({r['ce'] for r in recs if r['ce'] is not None}),
            'sources': sources,
            'lifespan_known': bool(life),
        })

    # 索引页
    lines = [
        "# 汉书人物一生轨迹索引",
        "",
        f"> 共 **{len(pages)}** 位人物达成 W10y 建设条件（≥{MIN_EVENTS} 个事件 且 跨越 ≥{MIN_YEARS} 年）",
        "",
        "| 人物 | 事件数 | 年代跨度 | 生卒年 | 主要来源 | 页面 |",
        "|------|--------|----------|--------|----------|------|",
    ]
    for p in pages:
        span = f"{ce_year_label(p['years'][0])}—{ce_year_label(p['years'][-1])}" if p['years'] else '时间不详'
        life = lifespan['known_lifespans'].get(p['person'])
        life_s = f"{ce_year_label(life['birth'])}—{ce_year_label(life['death'])}" if life else ''
        src = '、'.join(p['sources'][:2]) + (' 等' if len(p['sources']) > 2 else '')
        lines.append(f"| {p['person']} | {p['events']} | {span} | {life_s} | {src} | [[{p['file'].replace('.md', '')}]] |")
    (OUT_DIR / "_index.md").write_text('\n'.join(lines) + "\n", encoding='utf-8')

    stats = {
        'spec': 'SKILL_W10y_时间线页建设',
        'trigger': f'events>={MIN_EVENTS} and years>={MIN_YEARS}',
        'persons_total_in_events': len(by_person),
        'persons_qualified': len(pages),
        'events_total': sum(p['events'] for p in pages),
        'lifespan_annotated': sum(1 for p in pages if p['lifespan_known']),
        'time_unresolved_tokens': dict(resolver.unresolved.most_common(30)),
        'files': len(pages) + 1,
    }
    (OUT_DIR / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"事件总数: {sum(len(j['events']) for j in events_data.values())}")
    print(f"涉及人物(规范名): {len(by_person)}")
    print(f"达标人物(W10y): {len(pages)}")
    top5 = [(p['person'], p['events']) for p in pages[:5]]
    print("Top5:", top5)
    print("输出目录:", OUT_DIR)


if __name__ == '__main__':
    main()
