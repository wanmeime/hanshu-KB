#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复汉书KB事件数据：改进事件名、填充verb/verb_type/time、改进type。"""
import json, re, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(ROOT, 'kg/events/data/all_events.json')
SUMMARY_FILE = os.path.join(ROOT, 'kg/events/events_summary.json')
YEAR_MAP_FILE = os.path.join(ROOT, 'kg/chronology/data/year_ce_map.json')
MD_DIR = os.path.join(ROOT, 'kg/events/data')

# ---- 标记处理 ----
MARK_RE = re.compile(r'〖([@=&;◆%$\?\+#:•!\{~\^\[_\x20])([^〗\|]*)(\|[^〗]*)?〗')
VERB_MARK_RE = re.compile(r'⟦([○◈◉])([^⟧]*)⟧')
TIME_MARK_RE = re.compile(r'〖%([^〗]+)〗')
PERSON_MARK_RE = re.compile(r'〖@([^〗\|]+)(\|[^〗]*)?〗')
PLACE_MARK_RE = re.compile(r'〖=([^〗]+)〗')

def strip_marks(txt):
    """去除所有标注标记，返回纯文本。"""
    txt = MARK_RE.sub(r'\2', txt)
    txt = VERB_MARK_RE.sub(r'\2', txt)
    return txt

def extract_verb(text):
    """从标注文本提取第一个⟦⟧动词。返回 (verb, verb_type) 或 ('', '')."""
    m = VERB_MARK_RE.search(text)
    if not m:
        return '', ''
    vtype_char = m.group(1)
    verb = m.group(2)
    if vtype_char == '○':
        return verb, '正面'
    elif vtype_char == '◈':
        return verb, '反叛'
    elif vtype_char == '◉':
        return verb, '诛杀'
    return verb, ''

def extract_time(text):
    """从标注文本提取第一个〖%X〗时间标注。"""
    m = TIME_MARK_RE.search(text)
    if m:
        return m.group(1)
    return ''

def extract_persons_ordered(text):
    """从标注文本按出现顺序提取人名（取|前主名）。"""
    return [m.group(1) for m in PERSON_MARK_RE.finditer(text)]

def extract_places_ordered(text):
    """从标注文本按出现顺序提取地名。"""
    return [m.group(1) for m in PLACE_MARK_RE.finditer(text)]

# ---- 事件类型判定 ----
# 纪类卷 卷001-卷012, 表类卷 卷013-卷020, 志类卷 卷021-卷030, 传类卷 卷031+
def get_chapter_category(ch_key, title):
    """返回卷类别: '纪'/'表'/'志'/'传'."""
    num = re.match(r'卷(\d+)', ch_key)
    if not num:
        return '传'
    n = int(num.group(1))
    if n <= 12:
        return '纪'
    elif n <= 20:
        return '表'
    elif n <= 30:
        return '志'
    else:
        return '传'

FENG_VERBS = {'封', '立', '嗣', '绍封', '拜', '赐', '命', '策'}
SANG_VERBS = {'薨', '卒', '崩', '死', '殂'}
FEI_VERBS = {'徙', '废', '罢', '免', '迁', '贬', '黜', '退'}
FU_VERBS = {'复', '起', '绍封'}

def determine_type(verb, verb_type, category, plain):
    """根据动词、卷类别、内容确定事件类型。"""
    if verb:
        if verb in FENG_VERBS:
            return '封拜'
        if verb in SANG_VERBS:
            return '薨卒'
        if verb in FEI_VERBS:
            return '废徙'
        if verb in FU_VERBS:
            return '复任'
        if verb_type == '反叛':
            return '反叛'
        if verb_type == '诛杀':
            return '刑杀'
        # 其他正面动词归封拜
        if verb_type == '正面':
            return '封拜'
    # 无动词
    if category == '纪':
        return '纪事'
    if category == '志':
        return '制度'
    if category == '表':
        return '表文'
    if category == '传':
        return '生平'
    return '叙事'

# ---- 事件名生成 ----
# 明确动作动词集合（古汉语）
ACTION_VERBS_DEATH = ['薨', '崩', '卒', '死', '殂', '弑']
ACTION_VERBS_KILL = ['杀', '诛', '斩', '刺', '害', '族', '灭', '屠', '坑', '夷', '磔', '枭', '戮']
ACTION_VERBS_ATTACK = ['攻', '击', '伐', '破', '围', '救', '战', '拔', '拒', '距', '守', '备', '击破']
ACTION_VERBS_MOVE = ['入', '如', '至', '归', '降', '起', '反', '叛', '畔', '奔', '逃', '亡', '还', '进', '出', '之', '如', '适', '过']
ACTION_VERBS_POLITICAL = ['奏', '谏', '废', '罢', '免', '徙', '迁', '封', '立', '嗣', '赦', '赐', '赏', '即位', '称帝', '称王', '自立', '即']
ACTION_VERBS_RITUAL = ['祠', '祭', '朝', '会', '盟', '幸', '聘', '觐']
ACTION_VERBS_BUILD = ['筑', '作', '治', '置', '建', '营', '修']

ALL_ACTION_VERBS = set(
    ACTION_VERBS_DEATH + ACTION_VERBS_KILL + ACTION_VERBS_ATTACK +
    ACTION_VERBS_MOVE + ACTION_VERBS_POLITICAL + ACTION_VERBS_RITUAL + ACTION_VERBS_BUILD
)

def truncate_name(name, max_len=20):
    """截断事件名到合理长度。"""
    name = name.strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name

def generate_name(ev, ch_key, title, plain, persons_in_order, places_in_order):
    """为机械名事件生成有意义的名字。"""
    text = ev.get('text', '')
    if not plain:
        plain = strip_marks(text)

    # 去除引号内容中的子句优先用段首
    head = plain[:40]

    # ---- 优先级1: 高准确率句式匹配 ----
    # 死亡: 段首 人名+薨/崩/卒/死
    for p in persons_in_order[:3]:
        for v in ACTION_VERBS_DEATH:
            if head.startswith(p + v) or head.startswith(p) and head[len(p):len(p)+1] in ('薨','崩','卒','死','殂'):
                idx = len(p)
                if idx < len(head) and head[idx] in ('薨','崩','卒','死','殂'):
                    return truncate_name(p + head[idx])

    # 籍贯: X，Y人也
    m = re.match(r'^(.{1,8})，(.{1,8})人也[，。]', head)
    if m:
        s, place = m.group(1), m.group(2)
        if any(p in s for p in persons_in_order[:3]) or len(s) <= 4:
            return truncate_name(s + '籍贯' + place[:6])

    # 世系: X，Y...孙/子也
    m = re.match(r'^(.{1,8})，(.{1,12})(孙|子|弟|兄|父|母|女|后)也', head)
    if m:
        s = m.group(1)
        return truncate_name(s + '世系')

    # 即位/称帝
    m = re.match(r'^(.{1,8})(即位|即皇帝位|即帝位|即天子位|称帝|称王|自立为.{1,4})', head)
    if m:
        return truncate_name(m.group(0)[:15])

    # ---- 优先级2: 人名+动词+对象 ----
    # 在段首前25字中，找人名+动作动词+宾语
    search_zone = head[:25]
    best = None
    for p in persons_in_order[:4]:
        idx = search_zone.find(p)
        if idx < 0:
            continue
        after_p = search_zone[idx + len(p):]
        # 跳过逗号、空格
        after_p_strip = after_p.lstrip('，。、 ')
        # 在人名后6字内找单字动词
        for i in range(min(6, len(after_p_strip))):
            ch = after_p_strip[i]
            if ch in ALL_ACTION_VERBS and ch not in ('之', '适', '过', '即'):
                verb = ch
                after_v = after_p_strip[i + 1:]
                # 找宾语: 人名或地名
                obj = ''
                for p2 in persons_in_order[:6]:
                    if p2 != p and after_v.startswith(p2):
                        obj = p2
                        break
                if not obj:
                    for pl in places_in_order[:4]:
                        if after_v.startswith(pl):
                            obj = pl
                            break
                if obj:
                    cand = p + verb + obj
                else:
                    cand = p + verb
                if best is None or len(cand) > len(best):
                    best = cand
                break
    if best:
        return truncate_name(best)

    # ---- 优先级3: 段首内容摘要 ----
    return head_summary(plain)

def head_summary(plain, min_len=5, max_len=15):
    """取段首摘要：在标点处截断。"""
    if not plain:
        return '佚名事件'
    # 取第一个句子（到句号/问号/叹号/分号）
    m = re.match(r'^([^。？！；：\n]{%d,20})' % min_len, plain)
    if m:
        s = m.group(1)
        # 在逗号处适当截断
        if len(s) > max_len:
            # 尝试在逗号处截断
            comma_pos = s.find('，')
            if 5 <= comma_pos <= max_len:
                s = s[:comma_pos]
            else:
                s = s[:max_len]
        return s.strip()
    # 太短，取到任意标点
    m2 = re.match(r'^([^。？！；：\n，]{1,20})', plain)
    if m2:
        return m2.group(1).strip()
    return plain[:max_len].strip()

# ---- 主处理 ----
def is_mechanical_name(name):
    return '相关记载' in name or '相关事件' in name

def process():
    with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(YEAR_MAP_FILE, 'r', encoding='utf-8') as f:
        year_map = json.load(f)

    stats = {
        'total': 0, 'mech_before': 0, 'mech_after': 0,
        'verb_filled': 0, 'verb_was_empty': 0,
        'time_filled': 0, 'time_was_empty': 0,
        'name_too_long': 0, 'name_empty': 0,
    }

    for ch_key, ch_data in data.items():
        title = ch_data.get('title', '')
        category = get_chapter_category(ch_key, title)
        events = ch_data.get('events', [])
        for ev in events:
            stats['total'] += 1
            text = ev.get('text', '')
            plain = strip_marks(text)
            persons_ord = extract_persons_ordered(text)
            places_ord = extract_places_ordered(text)

            # 1. 填充 verb / verb_type
            old_verb = ev.get('verb', '')
            if not old_verb:
                stats['verb_was_empty'] += 1
                verb, vtype = extract_verb(text)
                if verb:
                    ev['verb'] = verb
                    ev['verb_type'] = vtype
                    stats['verb_filled'] += 1
                else:
                    ev['verb'] = ''
                    ev['verb_type'] = '叙事'
            else:
                # 已有verb，确保verb_type有值
                if not ev.get('verb_type', ''):
                    # 根据标注推断
                    _, vt = extract_verb(text)
                    ev['verb_type'] = vt or '正面'

            # 2. 填充 time
            old_time = ev.get('time', '')
            if not old_time:
                stats['time_was_empty'] += 1
                t = extract_time(text)
                if t:
                    ev['time'] = t
                    stats['time_filled'] += 1

            # 3. 改进 type
            ev['type'] = determine_type(ev.get('verb', ''), ev.get('verb_type', ''), category, plain)

            # 4. 改进 name（仅机械名）
            name = ev.get('name', '')
            if is_mechanical_name(name):
                stats['mech_before'] += 1
                new_name = generate_name(ev, ch_key, title, plain, persons_ord, places_ord)
                new_name = truncate_name(new_name, 20)
                if not new_name:
                    new_name = '史事纪略'
                    stats['name_empty'] += 1
                if len(new_name) > 30:
                    new_name = new_name[:20]
                    stats['name_too_long'] += 1
                ev['name'] = new_name
                if is_mechanical_name(new_name):
                    stats['mech_after'] += 1
            else:
                # 非机械名也检查长度
                if len(name) > 30:
                    ev['name'] = name[:20]
                    stats['name_too_long'] += 1

        ch_data['count'] = len(events)

    return data, stats

def write_summary(data, stats):
    """写 events_summary.json"""
    total = sum(ch['count'] for ch in data.values())
    summary = {
        'metadata': {
            'total_events': total,
            'total_chapters': len(data),
            'source': '120个已标注汉书章节',
            'mechanical_names_after': stats['mech_after'],
            'mechanical_ratio': round(stats['mech_after'] / total * 100, 2),
        },
        'chapters': {k: {'title': v['title'], 'count': v['count']} for k, v in data.items()}
    }
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

def write_md_files(data):
    """写120卷事件索引.md"""
    for ch_key, ch_data in data.items():
        title = ch_data.get('title', '')
        events = ch_data.get('events', [])
        verb_count = sum(1 for e in events if e.get('verb', ''))
        time_count = sum(1 for e in events if e.get('time', ''))
        fname = f'{ch_key}_{title}_事件索引.md'
        fpath = os.path.join(MD_DIR, fname)
        lines = []
        lines.append(f'# {ch_key}_{title} 事件索引\n')
        lines.append('')
        lines.append('## 统计')
        lines.append(f'- 事件总数：{len(events)}')
        lines.append(f'- 有动词事件：{verb_count}')
        lines.append(f'- 有时间事件：{time_count}')
        lines.append('')
        lines.append('## 事件列表')
        lines.append('')
        lines.append('| ID | 段号 | 事件名 | 类型 | 时间 | 动词 | 人物 |')
        lines.append('|----|------|--------|------|------|------|------|')
        for ev in events:
            eid = ev.get('id', '')
            para = ev.get('para', '')
            name = ev.get('name', '').replace('|', '/')
            etype = ev.get('type', '')
            t = ev.get('time', '').replace('|', '/')
            verb = ev.get('verb', '')
            persons = ','.join(ev.get('persons', [])[:4])
            lines.append(f'| {eid} | {para} | {name} | {etype} | {t} | {verb} | {persons} |')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def main():
    print('加载并处理事件数据...')
    data, stats = process()
    print(f"总事件: {stats['total']}")
    print(f"机械名: {stats['mech_before']} -> {stats['mech_after']}")
    print(f"verb填充: {stats['verb_filled']}/{stats['verb_was_empty']}空")
    print(f"time填充: {stats['time_filled']}/{stats['time_was_empty']}空")
    print(f"名字超长: {stats['name_too_long']}, 空: {stats['name_empty']}")

    # 写 all_events.json
    with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('已写 all_events.json')

    # 写 events_summary.json
    write_summary(data, stats)
    print('已写 events_summary.json')

    # 写 120卷 md
    write_md_files(data)
    print('已写 120卷事件索引.md')

    # 验收统计
    total = stats['total']
    mech = stats['mech_after']
    verb_n = sum(1 for ch in data.values() for e in ch['events'] if e.get('verb', ''))
    time_n = sum(1 for ch in data.values() for e in ch['events'] if e.get('time', ''))
    print('\n===== 验收标准 =====')
    print(f"1. 机械名占比: {mech/total*100:.2f}% (要求<5%) {'✓' if mech/total*100<5 else '✗'}")
    print(f"2. 有动词事件占比: {verb_n/total*100:.2f}% (要求>40%) {'✓' if verb_n/total*100>40 else '✗'}")
    print(f"3. 有时间事件占比: {time_n/total*100:.2f}% (要求>30%) {'✓' if time_n/total*100>30 else '✗'}")
    print(f"4. 事件总数: {total} (要求10000+) {'✓' if total>=10000 else '✗'}")
    long_n = sum(1 for ch in data.values() for e in ch['events'] if len(e.get('name',''))>=30 or not e.get('name',''))
    print(f"5. 名字非空且<30字: 违规{long_n}个 {'✓' if long_n==0 else '✗'}")

if __name__ == '__main__':
    main()
