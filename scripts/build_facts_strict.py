#!/usr/bin/env python3
"""重新生成SPO事实三元组，严格约束：主宾必须在原文text字段中出现。

核心修复：
1. 主语必须是动词【前】最近的人名/国名（旧脚本用abs()不区分前后，导致主宾颠倒）
2. 宾语必须是动词【后】最近的官职/地名/国名/人名
3. text字段使用整段标注原文，主宾一定在其中
4. 每个事实必须有ctx（time或place至少一个非空）
5. 验证主宾都在去标记后的纯文本中出现
"""
import re, json, os
from pathlib import Path

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
ANN_DIR = BASE / "kg" / "entities" / "标注"
FACTS_DATA = BASE / "kg" / "facts" / "data"
SRC_DIR = BASE / "data" / "chapter_numbered"

NOUN_RE = re.compile(r'〖([@=;&%^~•!?+◆{:[_$#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')


def strip_markers(text):
    text = re.sub(r'〖([^〗]*?)〗', lambda m: m.group(1).split('|')[0], text)
    text = re.sub(r'⟦([^⟧]*?)⟧', lambda m: m.group(1).split('|')[0], text)
    text = re.sub(r'〘([^〙]*?)〙', lambda m: m.group(1).split('|')[0], text)
    return text


def get_juan_titles():
    titles = {}
    for f in sorted(SRC_DIR.glob("卷*.txt")):
        m = re.match(r'(卷\d+[a-z]?)_(.+)\.txt', f.name)
        if m:
            titles[m.group(1)] = m.group(2)
    return titles


def parse_entities(text):
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
        })
    return entities


def parse_verbs(text):
    verbs = []
    for m in VERB_RE.finditer(text):
        verbs.append({
            'type': m.group(1),
            'content': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })
    return verbs


# 不及物动词（无宾语，主语为承受者）
INTRANSITIVE = {
    '自杀', '要斩', '弃市', '下狱死', '伏诛', '刭', '伏法', '薨', '崩', '卒',
    '反', '谋反', '叛', '即位', '死', '发病', '呕血', '恚', '怒',
    '走', '逃', '亡', '归', '还', '至', '如', '入', '出', '上', '下',
    '降', '降汉', '降楚', '降赵', '降魏', '降齐', '降燕', '降韩',
    '赦', '灾', '坐', '免', '罢', '废', '退', '老', '告归', '谢',
    '病', '疾', '崩', '夢', '梦', '悔', '惧', '恐', '喜', '怒', '笑', '泣', '哭',
    '称制', '听政', '临朝', '居丧', '服丧',
}

# 动词→宾语符号优先级
def obj_priority(verb_type, verb_content):
    if verb_content in INTRANSITIVE:
        return []
    if verb_type == '○':
        if verb_content in ('立', '封', '拜', '嗣', '绍封', '复', '代', '绍', '袭'):
            return [';', '◆', '@', '=']
        if verb_content in ('徙', '迁', '都', '徙至', '迁至'):
            return ['=', '◆', ';', '@']
        if verb_content in ('击', '攻', '破', '围', '救', '伐', '讨'):
            return ['@', '◆', '=', ';']
        return [';', '=', '◆', '@']
    if verb_type == '◈':
        if verb_content in ('杀', '击', '攻', '破', '围', '斩', '屠', '虏', '禽',
                            '灭', '讨', '侵', '寇', '灌', '烧', '坑', '劫', '略'):
            return ['@', '◆', '=', ';']
        return ['@', '◆', '=', ';']
    if verb_type == '◉':
        if verb_content in ('诛', '灭', '族', '杀', '斩', '赦', '免', '废', '罢'):
            return ['@', '◆', '=']
        return []
    return ['@', '◆', '=', ';']


def find_subject(entities, vstart, plain, max_dist=80):
    """找动词前最近的人名/国名作为主语"""
    subj = None
    for e in entities:
        if e['symbol'] in ('@', '◆') and e['end'] <= vstart and (vstart - e['end']) <= max_dist:
            subj = e
    if not subj:
        return None
    s = subj['display']
    if not s or s not in plain:
        return None
    return s


def find_object(para_text, entities, vend, vt, vc, s, plain, max_dist=60):
    """找动词后最近的宾语"""
    priority = obj_priority(vt, vc)
    if not priority:
        return ''

    # 对于立/封/拜/嗣，优先匹配 "为〖;X〗" 模式
    if vc in ('立', '封', '拜', '嗣', '绍封', '复', '代', '绍', '袭', '徙', '迁'):
        after = para_text[vend:vend + 40]
        m = re.search(r'为\s*〖;([^〗]+)〗', after)
        if m:
            o = m.group(1).split('|')[0].strip()
            if o and o != s and o in plain:
                return o
        # 也匹配 "为〖◆X〗" 或 "为〖@X〗"
        m = re.search(r'为\s*〖([◆@])([^〗]+)〗', after)
        if m:
            o = m.group(2).split('|')[0].strip()
            if o and o != s and o in plain:
                return o

    # 按优先级顺序找动词后最近的实体
    for sym in priority:
        candidates = [e for e in entities
                      if e['symbol'] == sym and e['start'] >= vend and (e['start'] - vend) <= max_dist]
        if candidates:
            best = min(candidates, key=lambda x: x['start'])
            o = best['display']
            if o and o != s and o in plain:
                return o
    return ''


def extract_facts_from_para(para_text, para, juan_short, juan_title, curr_time=None):
    facts = []
    entities = parse_entities(para_text)
    verbs = parse_verbs(para_text)
    plain = strip_markers(para_text)

    if not plain.strip():
        return []

    # 提取同段时间和地点；时间可从前段继承
    times = [e['display'] for e in entities if e['symbol'] == '%']
    places = [e['display'] for e in entities if e['symbol'] == '=']
    time = times[0] if times else curr_time
    place = places[0] if places else None

    # 验收标准4：每个事实都有ctx（time或place至少一个非空）
    if not time and not place:
        return []

    for verb in verbs:
        vc = verb['content']
        vt = verb['type']
        vstart = verb['start']
        vend = verb['end']

        if not vc:
            continue

        s = find_subject(entities, vstart, plain)
        if not s:
            continue

        o = find_object(para_text, entities, vend, vt, vc, s, plain)

        facts.append({
            'pn': f"{juan_short}-{para}",
            's': s,
            'p': vc,
            'o': o,
            'ctx': {'time': time, 'place': place},
            'src': f"{juan_short}_{juan_title}",
            'text': para_text,
        })

    return facts


def main():
    print("=== 严格约束重新生成SPO事实三元组 ===")
    juan_titles = get_juan_titles()
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    print(f"标注文件: {len(ann_files)} 个")

    all_facts = []
    fact_id = 0
    seen = set()
    stats = {'paras': 0, 'paras_with_ctx': 0, 'paras_no_ctx': 0, 'verbs': 0, 'verbs_no_subj': 0}

    for filepath in ann_files:
        m = re.match(r'(卷\d+[a-z]?)_标注\.txt', filepath.name)
        juan_short = m.group(1) if m else filepath.stem
        juan_title = juan_titles.get(juan_short, juan_short)

        content = filepath.read_text(encoding='utf-8')

        curr_time = None  # 每卷开始重置时间继承
        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para = m.group(1)
            para_text = line[m.end():]
            if not para_text.strip():
                continue
            stats['paras'] += 1

            verbs = parse_verbs(para_text)
            stats['verbs'] += len(verbs)

            # 更新继承的时间：本段若显式标注时间则更新 curr_time
            para_entities = parse_entities(para_text)
            para_times = [e['display'] for e in para_entities if e['symbol'] == '%']
            if para_times:
                curr_time = para_times[0]

            facts = extract_facts_from_para(para_text, para, juan_short, juan_title, curr_time)
            if facts:
                stats['paras_with_ctx'] += 1
            else:
                stats['paras_no_ctx'] += 1

            for f in facts:
                key = (f['pn'], f['s'], f['p'], f['o'])
                if key in seen:
                    continue
                seen.add(key)
                fact_id += 1
                f_with_id = {
                    'id': f"f{fact_id:05d}",
                    'pn': f['pn'],
                    's': f['s'],
                    'p': f['p'],
                    'o': f['o'],
                    'ctx': f['ctx'],
                    'src': f['src'],
                    'text': f['text'],
                    'conf': 'high',
                }
                all_facts.append(f_with_id)

    print(f"段落总数: {stats['paras']}")
    print(f"有ctx的段落: {stats['paras_with_ctx']}，无ctx跳过: {stats['paras_no_ctx']}")
    print(f"动词总数: {stats['verbs']}")
    print(f"生成事实数: {len(all_facts)}")

    # 写入
    with open(FACTS_DATA / "all_facts.json", 'w', encoding='utf-8') as f:
        json.dump(all_facts, f, ensure_ascii=False, indent=2)
    print(f"已写入: {FACTS_DATA / 'all_facts.json'}")

    # 验证
    bad = 0
    bad_no_ctx = 0
    bad_no_p = 0
    for f in all_facts:
        plain = strip_markers(f['text'])
        if f['s'] not in plain:
            bad += 1
            continue
        if f['o'] and f['o'] not in plain:
            bad += 1
            continue
        if not f['p']:
            bad_no_p += 1
            continue
        if not f['ctx'].get('time') and not f['ctx'].get('place'):
            bad_no_ctx += 1

    total = len(all_facts)
    print(f"\n=== 验证结果 ===")
    print(f"总事实: {total}")
    print(f"主宾不在text中: {bad} 条 ({bad/total*100:.2f}%)")
    print(f"无p: {bad_no_p} 条")
    print(f"无ctx: {bad_no_ctx} 条")
    print(f"准确率(主宾在原文): {(total-bad)/total*100:.2f}%")

    # 抽样展示
    import random
    random.seed(42)
    print(f"\n=== 抽样10条 ===")
    for f in random.sample(all_facts, min(10, total)):
        plain = strip_markers(f['text'])
        ok = f['s'] in plain and (not f['o'] or f['o'] in plain)
        print(f"  [{'OK' if ok else 'BAD'}] {f['id']} {f['s']} --{f['p']}--> {f['o'] or '∅'}  ctx={f['ctx']}")


if __name__ == '__main__':
    main()
