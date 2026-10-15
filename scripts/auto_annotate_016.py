#!/usr/bin/env python3
"""Auto-annotate 卷016 高惠高后文功臣表第四 — conservative version."""
import re
from pathlib import Path

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
SRC = BASE / "data/chapter_numbered/卷016_高惠高后文功臣表第四.txt"
DST = BASE / "kg/entities/标注/卷016_标注.txt"

NUM = r'[一二三四五六七八九十百千万亖]+'
STEM = r'[甲乙丙丁戊己庚辛壬癸]'
BRANCH = r'[子丑寅卯辰巳午未申酉戌亥]'

# Year name prefixes (sorted by length desc to match longest first)
YEAR_NAMES = sorted([
    "孝文后", "孝景前", "孝景中", "孝景后", "孝文前",
    "高后", "孝惠", "孝文", "孝景", "孝武", "孝昭", "孝宣", "孝元", "孝成", "孝哀", "孝平",
    "元光", "元朔", "元鼎", "元狩", "元封", "太初", "延和", "建元", "征和", "元康", "元始", "元寿",
    "建武", "甘露", "永始", "绥和", "建国", "地节", "鸿嘉", "五凤", "延光", "竟宁",
    "初元", "永光", "建昭", "河平", "阳朔", "元延", "建平", "居摄", "天凤", "地皇",
    "神爵", "永平", "永元", "建初", "永宁", "太安", "永和", "汉安", "建康",
    "延熹", "建宁", "熹平", "光和", "中平", "建安", "初平", "兴平",
    "中二", "中三", "中五", "中六", "中元", "中四", "中一",
    "后二", "后三", "后五", "后七", "后元", "后一", "后四", "后六",
    "前二", "前三", "前五", "前元", "前一", "前四", "前六",
    "建武中", "延平", "永初", "元初", "阳嘉", "永建", "永嘉",
], key=len, reverse=True)

# Year name prefixes that need a number after them
YEAR_PREFIXES_NEED_NUM = sorted([
    "孝文后", "孝景前", "孝景中", "孝景后", "孝文前",
    "高后", "孝惠", "孝文", "孝景", "孝武", "孝昭", "孝宣", "孝元", "孝成", "孝哀", "孝平",
    "元光", "元朔", "元鼎", "元狩", "元封", "太初", "延和", "建元", "征和", "元康", "元始", "元寿",
    "建武", "甘露", "永始", "绥和", "建国", "地节", "鸿嘉", "五凤", "延光", "竟宁",
    "初元", "永光", "建昭", "河平", "阳朔", "元延", "建平", "居摄", "天凤", "地皇",
    "神爵", "永平", "永元", "建初", "永宁", "太安", "永和", "汉安", "建康",
    "延熹", "建宁", "熹平", "光和", "中平", "建安", "初平", "兴平",
    "建武中", "延平", "永初", "元初", "阳嘉", "永建", "永嘉",
], key=len, reverse=True)

# Year names that already include the number (just need 年 after)
YEAR_NAMES_COMPLETE = sorted([
    "中二", "中三", "中五", "中六", "中元", "中四", "中一",
    "后二", "后三", "后五", "后七", "后元", "后一", "后四", "后六",
    "前二", "前三", "前五", "前元", "前一", "前四", "前六",
], key=len, reverse=True)

YEAR_PREFIX_RE = '(?:' + '|'.join(YEAR_PREFIXES_NEED_NUM) + ')'
YEAR_COMPLETE_RE = '(?:' + '|'.join(YEAR_NAMES_COMPLETE) + ')'

# Verbs
VERBS_PUN = sorted(["要斩", "弃市", "自杀", "下狱死", "诛", "斩"], key=len, reverse=True)
VERBS_NEG = sorted(["谋反", "反"], key=len, reverse=True)
VERBS_POS = sorted(["绍封", "复封", "更封", "封", "薨", "嗣", "免", "复"], key=len, reverse=True)

# Official titles (sorted by length desc)
OFFICIALS = sorted([
    "假左丞相", "右丞相", "左丞相", "丞相", "骑都尉", "骑将", "骑郎将",
    "太仆", "令史", "舍人", "中涓", "连嚮", "连嚻", "都尉", "护军中尉",
    "太常", "内史", "太守", "太傅", "中尉", "江都相",
    "赵相", "楚相", "楚太傅", "赵内史", "九江太守", "淮阳守",
    "横海将军", "卫将军", "车骑将军", "博士弟子", "关内矦",
    "城旦", "隷臣", "庶人", "上造", "大夫", "公乘", "公士", "簪褭", "士伍",
    "千人", "中郎", "将军", "左令尹", "柱国", "校尉",
    "光禄勋", "大将军", "右将军", "左将军",
    "掖庭令", "御史", "御史大夫", "尚书", "尚书令",
    "给事中", "侍中", "常侍", "散骑", "中书",
], key=len, reverse=True)

# States for 〖◆X〗
STATES = sorted(["匈奴", "淮南王", "淮阴", "项籍", "项羽"], key=len, reverse=True)

# Place names for 〖=X〗 (2+ chars only, to avoid false matches)
PLACES = sorted([
    "长安", "霸上", "宛朐", "横阳", "修武", "下邳", "武关", "峣关",
    "泗水", "东海", "陇西", "江汉", "豫章", "浙江", "东阳", "荥阳",
    "甬道", "鸿门", "关中", "杜陵", "茂陵", "长陵", "霸陵", "安陵",
    "阳陵", "平棘", "隆虑", "营陵", "龙额", "按道", "清安", "葛绎",
    "筑阳", "武阳", "平曲", "堂邑", "襄城", "故安", "周阳", "氏丘",
    "营平", "阳虚", "杨丘", "安都", "平昌", "武成", "白石", "阜陵",
    "安阳", "阳周", "东城", "涿郡", "内黄", "节氏", "清河", "河间",
    "广平", "博阳", "广严", "舞阳", "曲逆", "射阳", "汾阴", "平阳",
    "信武", "汝阴", "广都", "成都", "广汉", "槐里", "栒邑", "泥阳",
    "高陵", "安平", "安国", "观津", "观阳", "平原", "阳都", "魏其",
    "南皮", "昌平", "即墨", "平度", "平国", "平城", "平皋", "信成",
    "信都", "信平", "信阳", "建成", "建平", "建阳", "建陵", "建乡",
    "建昌", "将陵", "将梁", "将乐", "朱虚", "阿武", "阿陵", "胡孰",
    "胡苏", "剧阳", "般阳", "般陵", "肥如", "肥城", "封斯", "封阳",
    "封陵", "浮丘", "浮阳", "高京", "高胡", "高昌", "高平", "高宛",
    "高郭", "高密", "高都", "高乡", "高柴", "南阳", "南陵", "南城",
    "南乡", "平恩", "平干", "平于", "平氏", "平林", "平都", "平乡",
    "平寿", "平望", "平陆", "平舆", "期思", "期城", "祁阳", "祁乡",
    "千乘", "清阳", "清陵", "汝阳", "汝南", "山阳", "山都", "商陵",
    "商市", "上邽", "上谷", "上兰", "上明", "上平", "上曲", "上殷",
    "上原", "石山", "石城", "思成", "思平", "泗阳", "松滋", "松柏",
    "遂平", "遂城", "台陵", "桃阳", "桃乡", "荼陵", "土军", "土翕",
    "宛平", "宛阳", "魏县", "温阳", "武安", "武始", "武遂", "武强",
    "武州", "武威", "武都", "西平", "西华", "西陵", "西阳", "西乡",
    "下邽", "下相", "下蔡", "下城", "下隽", "下盐", "咸阳", "湘乡",
    "湘南", "襄平", "襄邑", "襄陵", "新阳", "新郪", "新都", "新乡",
    "新市", "行唐", "行榆", "修市", "修故", "徐乡", "玄菟", "玄氏",
    "衍氏", "阳信", "阳平", "阳城", "阳乐", "阳翟", "阳丘", "阳阿",
    "阳武", "阳邑", "阳泉", "阳里", "义阳", "宜春", "宜城", "宜禾",
    "宜陵", "阴平", "阴曼", "应乡", "雍丘", "雍奴", "舆平", "原阳",
    "原都", "远乡", "乐成", "乐平", "乐陵", "乐都", "乐乡", "乐昌",
    "乐阳", "乐浪", "乐安", "留舒", "栎阳", "涿阳", "淄川", "资中",
    "资阳", "子干", "子乡", "邹平", "筑乡", "庄原", "庄卢", "观津",
    "赞乡", "臧马", "章武", "章乡", "长平", "长修", "长乐", "长罗",
    "长伯", "长信", "长社", "长沙", "轵道", "中水", "中山", "中都",
    "中乡", "中丘", "中阳", "重平", "重合", "重乡", "朱轸", "株陵",
    "株梧", "甾丘", "甾川", "菑川", "菑丘", "睢陵", "睢阳", "煮枣",
    "煮侯", "柱天", "柱国", "祝阿", "祝兹", "赘其", "赘侯", "酂乡",
    "左乡", "左邑", "左冯翊", "左辅", "南奅", "广陵", "广阳", "广宗",
    "广武", "广乡", "定陶", "定陵", "定安", "定平", "定国", "定阳",
    "定胡", "定襄", "平州", "平的", "平邑", "平皋", "广野", "广望",
    "广信", "广德", "广饶", "广乡", "广成", "广武", "广宗", "广平",
    "安平", "安阳", "安都", "安陵", "安国", "安城", "安风", "安众",
    "安乡", "安平", "安阳", "安都", "安陵", "安国", "安城",
    "武乡", "武阳", "武关", "武平", "武强", "武遂", "武始",
    "城旦", "城阳", "城都", "城平", "城阳", "城都", "城平",
    "高京", "高胡", "高昌", "高平", "高宛", "高郭", "高密", "高都",
    "高乡", "高柴", "高陵", "高阳", "高城", "高乡", "高武", "高柴",
    "平恩", "平干", "平于", "平氏", "平林", "平都", "平乡",
    "平州", "平的", "平国", "平邑", "平城", "平皋",
    "平寿", "平望", "平陆", "平阳", "平舆",
    "期思", "期城", "祁阳", "祁乡", "千乘",
    "清河", "清安", "清阳", "清陵", "汝阳", "汝阴", "汝南",
    "山阳", "山都", "山州", "商陵", "商市",
    "上邽", "上谷", "上兰", "上明", "上平", "上曲", "上殷", "上原",
    "石山", "石城", "思成", "思平", "泗水", "泗阳", "松滋", "松柏",
    "遂平", "遂城", "台陵", "桃阳", "桃乡", "荼陵", "土军", "土翕",
    "宛平", "宛阳", "魏其", "魏县", "温阳",
    "武安", "武城", "武始", "武遂", "武强", "武乡", "武阳",
    "武州", "武平", "武威", "武都", "武关",
    "西平", "西华", "西陵", "西阳", "西乡",
    "下邽", "下相", "下蔡", "下城", "下隽", "下盐",
    "咸阳", "湘乡", "湘南", "襄平", "襄邑", "襄陵",
    "新阳", "新郪", "新都", "新乡", "新市",
    "信成", "信都", "信平", "信武", "信阳",
    "行唐", "行榆", "修市", "修武", "修故",
    "徐乡", "玄菟", "玄氏", "衍氏",
    "阳信", "阳平", "阳城", "阳乐", "阳翟", "阳陵", "阳丘",
    "阳阿", "阳武", "阳邑", "阳都", "阳泉", "阳里",
    "义阳", "宜春", "宜城", "宜禾", "宜陵",
    "阴平", "阴曼", "应乡", "雍丘", "雍奴", "舆平",
    "原阳", "原都", "远乡", "乐成", "乐平", "乐陵", "乐都",
    "乐乡", "乐昌", "乐阳", "乐浪", "乐安",
    "留舒", "栎阳", "栒邑", "涿郡", "涿阳", "淄川", "资中", "资阳",
    "子干", "子乡", "邹平", "筑阳", "筑乡", "庄原", "庄卢",
    "观津", "观阳", "赞乡", "臧马", "章武", "章乡",
    "长平", "长安", "长陵", "长修", "长乐", "长罗", "长伯",
    "长信", "长社", "长沙", "轵道",
    "中水", "中山", "中都", "中乡", "中丘", "中阳",
    "重平", "重合", "重乡", "朱虚", "朱轸", "株陵", "株梧",
    "甾丘", "甾川", "菑川", "菑丘", "睢陵", "睢阳",
    "煮枣", "煮侯", "柱天", "柱国", "祝阿", "祝兹", "赘其", "赘侯",
    "酂乡", "左乡", "左邑", "左冯翊", "左辅",
], key=len, reverse=True)

# Single-char states/kingdoms
STATE_CHARS = set("燕赵齐楚秦汉魏韩吴梁代鲁")

def collect_annotations(text, col_num):
    """Collect all (start, end, replacement) tuples for a column."""
    anns = []
    
    def add(start, end, replacement):
        anns.append((start, end, replacement))
    
    def overlaps(s, e):
        return any(a <= s < b or a < e <= b for a, b, _ in anns)
    
    # 1. Household counts: 〖$X户〗
    for m in re.finditer(NUM + r'户', text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖${m.group()}〗')
    
    # Also "户X万X千" patterns
    for m in re.finditer(r'户' + NUM + r'千', text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖${m.group()}〗')
    
    # 2. Year-name time markers: prefix+number+年 (+ optional month+day)
    # Process BEFORE full dates to avoid partial matches
    # Also handle 元年 (元 means "first")
    # Pattern A: prefix needs number (e.g., 高后+二年)
    for m in re.finditer(YEAR_PREFIX_RE + r'(?:元|' + NUM + r')年(?:' + NUM + r'月' + STEM + BRANCH + r')?', text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    # Pattern B: complete year name (e.g., 中三+年)
    for m in re.finditer(YEAR_COMPLETE_RE + r'年(?:' + NUM + r'月' + STEM + BRANCH + r')?', text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 3. Full dates: number+年+month+stem+branch → 〖%X〗 (not already matched by year-name)
    for m in re.finditer(NUM + r'年' + NUM + r'月' + STEM + BRANCH, text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 3b. Month+day only: (正|number)+月+stem+branch → 〖%X〗
    for m in re.finditer(r'(?:正|' + NUM + r')月' + STEM + BRANCH, text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 4. Month+day only: number+月+stem+branch → 〖%X〗
    for m in re.finditer(NUM + r'月' + STEM + BRANCH, text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 5. Duration: number+年 followed by 薨/卒/免/有罪/坐/亡
    # Must NOT be preceded by a year name character
    for m in re.finditer(NUM + r'年', text):
        s, e = m.start(), m.end()
        if overlaps(s, e):
            continue
        # Check if already part of a time marker
        before = text[:s]
        after = text[e:]
        # Skip if preceded by year name (already handled above)
        if re.search(YEAR_PREFIX_RE + r'$', before):
            continue
        # Skip if preceded by 年 (part of a larger number)
        if before.endswith('年'):
            continue
        # Check what follows
        if re.match(r'[，。；]|薨|卒|免|有罪|坐|亡', after):
            add(s, e, f'〖%{m.group()}|时长〗')
        elif re.match(r'，' + NUM + r'月', after):
            # Followed by month/day → this is a time marker for a date event
            # But without year name, it's ambiguous. Treat as time marker if followed by person.
            pass
    
    # 6. Official titles: 〖;X〗
    for title in OFFICIALS:
        for m in re.finditer(re.escape(title), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖;{title}〗')
    
    # 7. States: 〖◆X〗
    for state in STATES:
        for m in re.finditer(re.escape(state), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖◆{state}〗')
    
    # 7a. Single-char state names in context: 〖◆X〗
    # Only annotate when preceded by verbs/punctuation like 击/定/入/从/起/降/攻/破/灭/属/都/、
    state_chars = "燕赵齐楚秦汉魏韩吴梁代鲁"
    for m in re.finditer(r'(?<=[击定入从起降攻破灭属都至击别复、])[' + state_chars + r']', text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖◆{m.group()}〗')
    
    # 7b. Place names: 〖=X〗
    for place in PLACES:
        for m in re.finditer(re.escape(place), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖={place}〗')
    
    # 8. Person names in columns 5+: 〖@X〗
    # Pattern: optional title + 矦 + 1-2 name chars, followed by verb/punctuation
    if col_num >= 5:
        title_chars = r'(?:[节靖简夷共哀孝文景武昭宣元成平烈顷戴怀质思炀安厘考信康敬肃懿恭惠顺怀穆隐庄戴端坚勇严壮毅威烈桓文穆共肃考厘康敬信])?'
        lookahead = r'(?=嗣|封|薨|免|复|绍|以|，|。|为|坐|有|亡|卒|之|更|益|入|出|不|得|诏|家|后|前|；|｜|与|赎|益|更|坐|举|子|弟|今|来|所)'
        # Try 1-char name first (most common)
        person_re1 = title_chars + r'矦[\u4e00-\u9fff]' + lookahead
        for m in re.finditer(person_re1, text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖@{m.group()}〗')
        # Then try 2-char name (for names like "本始")
        person_re2 = title_chars + r'矦[\u4e00-\u9fff]{2}' + lookahead
        for m in re.finditer(person_re2, text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖@{m.group()}〗')
    
    # 9. Punishment verbs: ⟦◉X⟧
    for verb in VERBS_PUN:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦◉{verb}⟧')
    
    # 10. Negative verbs: ⟦◈X⟧
    for verb in VERBS_NEG:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦◈{verb}⟧')
    
    # 11. Positive verbs: ⟦○X⟧
    for verb in VERBS_POS:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦○{verb}⟧')
    
    # 12. Crimes: 〖:X〗
    for m in re.finditer(r'酎金', text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖:{m.group()}〗')
    
    # Sort and remove overlaps (keep longer matches)
    anns.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered = []
    last_end = -1
    for s, e, r in anns:
        if s >= last_end:
            filtered.append((s, e, r))
            last_end = e
    
    return filtered

def apply_annotations(text, anns):
    """Apply annotations from right to left."""
    result = text
    for s, e, r in reversed(anns):
        result = result[:s] + r + result[e:]
    return result

def annotate_row(content):
    parts = content.split('｜')
    if not parts:
        return content
    
    # Column 1: person name (strip spaces, keep them outside marker)
    stripped = parts[0].strip()
    if stripped:
        leading = parts[0][:len(parts[0]) - len(parts[0].lstrip())]
        trailing = parts[0][len(parts[0].rstrip()):]
        parts[0] = f'{leading}〖@{stripped}〗{trailing}'
    
    # Columns 2-8
    for i in range(1, len(parts)):
        anns = collect_annotations(parts[i], i + 1)
        parts[i] = apply_annotations(parts[i], anns)
    
    return '｜'.join(parts)

def main():
    lines = SRC.read_text(encoding='utf-8').split('\n')
    output = []
    
    for line in lines:
        m = re.match(r'^(\[r\d+\])(.*)$', line)
        if m:
            prefix = m.group(1)
            content = m.group(2)
            if prefix == '[r1]':
                output.append(line)
                continue
            annotated = annotate_row(content)
            output.append(f'{prefix}{annotated}')
        else:
            output.append(line)
    
    DST.write_text('\n'.join(output), encoding='utf-8')
    print(f"Written to {DST}")

if __name__ == '__main__':
    main()
