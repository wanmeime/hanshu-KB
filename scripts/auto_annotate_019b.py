#!/usr/bin/env python3
"""Auto-annotate 卷019b 百官公卿表第七下 — year table format."""
import re
from pathlib import Path

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
SRC = BASE / "data/chapter_numbered/卷019b_百官公卿表第七下.txt"
DST = BASE / "kg/entities/标注/卷019b_标注.txt"

NUM = r'[一二三四五六七八九十百千万亖]+'
STEM = r'[甲乙丙丁戊己庚辛壬癸]'
BRANCH = r'[子丑寅卯辰巳午未申酉戌亥]'

# Official titles in the year table (sorted by length desc)
OFFICIALS = sorted([
    "御史大夫", "左冯翊", "右扶风", "京兆尹", "水衡都尉", "中尉执金吾",
    "大司徒", "大司空", "大司马", "大司农", "大鸿胪", "大行令",
    "治粟内史", "少府", "主爵都尉", "右内史", "左内史",
    "太师", "太傅", "太保", "太常", "太仆", "太祝",
    "光禄勲", "光禄勋", "中大夫令", "大理", "宗正", "宗伯",
    "奉常", "郎中令", "卫尉", "衞尉", "廷尉", "典客",
    "相国", "丞相", "太尉", "将军", "列将军",
    "前将军", "后将军", "左将军", "右将军",
    "车骑将军", "票骑将军", "票骑大将军", "衞将军", "卫将军",
    "步兵将军", "复土将军", "护军将军", "将作大匠",
    "中尉", "执金吾", "长史", "丞相长史",
    "太子太傅", "太子少傅", "少傅",
    "博士", "中郎将", "郎中", "中郎",
    "谒者", "给事中", "侍中", "常侍", "散骑",
    "尚书令", "尚书", "光禄大夫",
    "行内史", "内史", "守", "相",
    "令", "尉", "正",
    "司直", "司隶", "刺史",
    "城门校尉", "越骑校尉", "护军都尉",
    "左辅都尉", "右辅都尉", "中地守",
    "长乐衞尉", "长乐少府", "长乐卫尉",
    "詹事", "宗伯", "奉车都尉", "驸马都尉", "驸马都尉",
    "左曹中郎将", "诸吏散骑光禄勋", "诸吏散骑光禄大夫",
    "诸吏光禄大夫", "特进",
    "冀州牧", "复土将军",
    "大司马司直", "大司徒司直",
    "中谒者", "中书谒者",
    "符玺御史", "符玺御史",
    "军正", "职志",
    "骑都尉", "骑将", "骑郎将",
    "连嚮", "连嚻", "都尉",
    "关内矦", "关内侯",
    "庶人", "城旦", "隷臣",
    "上造", "大夫", "公乘", "公士", "簪褭", "士伍",
    "不更", "左更", "右更", "中更",
    "五大夫", "左庶长", "右庶长", "驷车庶长", "大庶长",
    "大良造", "客卿", "正卿",
    "左内史", "右内史", "中内史",
    "郡守", "太守", "都尉",
    "河南太守", "河内太守", "沛郡都尉", "上党都尉",
    "定襄太守", "东郡太守", "渤海太守",
    "颍川太守", "南阳太守", "陈留太守",
    "代相", "赵相", "齐相", "楚相", "代守", "赵守",
    "沛相", "滕令", "汝阴令",
    "燕王", "赵王", "齐王", "楚王",
    "太子", "皇后", "皇太子",
    "鲁元公主", "馆陶公主",
    "复土将军", "将作大匠",
    "护军都尉", "护军",
    "大司马车骑将军", "大司马衞将军", "大司马票骑大将军",
    "票骑将军", "车骑将军",
    "执金吾", "中尉执金吾",
    "光禄勋", "光禄勲",
    "卫尉", "衞尉",
    "太仆", "太常", "太祝", "太史", "太卜", "太医", "太乐", "太宰",
    "宗正", "宗伯",
    "典客", "大鸿胪", "大行令",
    "治粟内史", "大司农",
    "少府", "水衡都尉",
    "主爵都尉", "右内史", "左内史", "中内史",
    "左冯翊", "右扶风", "京兆尹",
    "奉常", "郎中令", "光禄勲", "光禄勋", "中大夫令",
    "廷尉", "大理",
    "御史大夫", "御史中丞", "侍御史",
    "丞相", "相国", "大司徒", "大司空",
    "太尉", "大司马",
    "太师", "太傅", "太保",
    "将军", "列将军", "前将军", "后将军", "左将军", "右将军",
    "车骑将军", "票骑将军", "衞将军", "卫将军",
    "步兵将军", "复土将军", "护军将军",
    "中郎将", "左曹中郎将",
    "光禄大夫", "诸吏光禄大夫", "诸吏散骑光禄大夫", "诸吏散骑光禄勋",
    "尚书令", "尚书",
    "给事中", "侍中", "常侍", "散骑",
    "谒者", "奉车都尉", "驸马都尉", "驸马都尉",
    "城门校尉", "越骑校尉", "护军都尉",
    "左辅都尉", "右辅都尉",
    "长乐衞尉", "长乐少府", "长乐卫尉",
    "詹事", "将作大匠",
    "大司马司直", "大司徒司直",
    "符玺御史", "军正", "职志",
    "骑都尉", "骑将", "骑郎将",
    "连嚮", "连嚻", "都尉",
    "关内矦", "关内侯",
    "庶人", "城旦", "隷臣",
    "上造", "大夫", "公乘", "公士", "簪褭", "士伍",
    "不更", "左更", "右更", "中更",
    "五大夫", "左庶长", "右庶长", "驷车庶长", "大庶长",
    "大良造", "客卿", "正卿",
    "郡守", "太守",
    "河南太守", "河内太守", "沛郡都尉", "上党都尉",
    "定襄太守", "东郡太守", "渤海太守",
    "颍川太守", "南阳太守", "陈留太守",
    "代相", "赵相", "齐相", "楚相", "代守", "赵守",
    "沛相", "滕令", "汝阴令",
    "太子太傅", "太子少傅", "少傅",
    "博士", "中郎", "郎中",
    "内史",
], key=len, reverse=True)

# Place names (2+ chars)
PLACES = sorted([
    "长安", "霸上", "荥阳", "杜陵", "茂陵", "长陵", "霸陵", "安陵",
    "阳陵", "平棘", "隆虑", "襄城", "故安", "武阳", "平曲",
    "堂邑", "沛郡", "河内", "河南", "东郡", "上党", "定襄",
    "渤海", "颍川", "南阳", "陈留", "沛", "寿春",
    "方与", "废丘", "彭城", "好畤", "襄国", "池阳", "平阴",
    "上林", "鸿沟", "代郡", "鴈门", "雁门",
    "武关", "峣关", "关中", "蜀",
    "栎阳", "栒邑", "泥阳", "高陵",
    "安国", "安平", "平原", "阳都", "魏其",
    "南皮", "昌平", "即墨",
    "广平", "博阳", "广严", "舞阳", "曲逆", "射阳",
    "汾阴", "平阳", "信武", "汝阴",
    "筑阳", "龙额", "按道", "清安",
    "营陵", "辟阳", "䣙成", "安丘",
    "谷阳", "谷阳", "期思", "戚圉",
    "下相", "高陵", "龙阳", "平严",
    "阳夏", "阳信", "阳都", "阳平",
    "安平", "安城", "安陵", "安国",
    "信成", "信都", "信平", "信阳",
    "建成", "建平", "建阳", "建陵",
    "将陵", "将梁", "朱虚",
    "广陵", "广阳", "广宗", "广武", "广乡",
    "定陶", "定陵", "定安", "定平", "定国", "定阳", "定胡", "定襄",
    "长安", "长陵", "长修", "长乐", "长罗",
    "涿郡", "东海", "东城",
    "清河", "河间",
    "南奅", "南阳",
    "左冯翊", "右扶风", "京兆尹",
    "长修", "辟阳", "广平", "曲逆", "安国", "营陵",
    "士军", "殷内", "汲", "绛", "沛",
    "平阳", "信武", "汝阴", "博阳", "广严",
    "筑阳", "龙额", "按道", "清安", "武阳",
    "期思", "戚圉", "下相", "高陵", "龙阳", "平严",
    "阳夏", "阳信", "阳都",
    "建成", "建平", "建陵",
    "安平", "安陵",
    "定陶", "定陵", "定安",
    "谷阳", "安丘", "䣙成",
    "朱虚", "将陵", "将梁",
    "广陵", "广阳", "广宗", "广武",
    "长安", "长陵", "长乐", "长罗",
    "杜陵", "茂陵", "霸陵", "安陵", "阳陵",
    "寿春", "沛郡",
], key=len, reverse=True)

# States for 〖◆X〗
STATES = sorted(["匈奴", "淮南王", "淮阴", "项籍", "项羽", "项梁"], key=len, reverse=True)

# Year name prefixes
YEAR_PREFIXES_NEED_NUM = sorted([
    "孝文后", "孝景前", "孝景中", "孝景后", "孝文前",
    "高后", "孝惠", "孝文", "孝景", "孝武", "孝昭", "孝宣", "孝元", "孝成", "孝哀", "孝平",
    "元光", "元朔", "元鼎", "元狩", "元封", "太初", "延和", "建元", "征和", "元康", "元始", "元寿",
    "建武", "甘露", "永始", "绥和", "建国", "地节", "鸿嘉", "五凤", "延光", "竟宁",
    "初元", "永光", "建昭", "河平", "阳朔", "元延", "建平", "居摄", "天凤", "地皇",
    "神爵", "永平", "永元", "建初", "永宁", "太安", "永和", "汉安", "建康",
    "延熹", "建宁", "熹平", "光和", "中平", "建安", "初平", "兴平",
    "建武中", "延平", "永初", "元初", "阳嘉", "永建", "永嘉",
    "黄龙", "本始", "地节", "神爵", "五凤", "甘露", "黄龙",
    "建始", "河平", "阳朔", "鸿嘉", "永始", "元延", "绥和",
    "建平", "元寿", "元始", "居摄", "建国", "天凤", "地皇",
    "更始",
], key=len, reverse=True)

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
VERBS_POS = sorted(["绍封", "复封", "更封", "封", "薨", "嗣", "免", "复", "徙", "废", "立"], key=len, reverse=True)

def collect_annotations(text, col_num):
    """Collect all (start, end, replacement) tuples for a column."""
    anns = []
    
    def add(start, end, replacement):
        anns.append((start, end, replacement))
    
    def overlaps(s, e):
        return any(a <= s < b or a < e <= b for a, b, _ in anns)
    
    # 1. Year-name time markers
    for m in re.finditer(YEAR_PREFIX_RE + r'(?:元|' + NUM + r')年(?:' + NUM + r'月' + STEM + BRANCH + r')?', text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    for m in re.finditer(YEAR_COMPLETE_RE + r'年(?:' + NUM + r'月' + STEM + BRANCH + r')?', text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 2. Full dates: number+年+month+stem+branch
    for m in re.finditer(NUM + r'年' + NUM + r'月' + STEM + BRANCH, text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 3. Month+day: (正|number)+月+stem+branch
    for m in re.finditer(r'(?:正|' + NUM + r')月' + STEM + BRANCH, text):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), f'〖%{m.group()}〗')
    
    # 4. Duration: number+年 followed by 薨/卒/免/有罪/坐/亡/迁/贬/徙
    for m in re.finditer(NUM + r'年', text):
        s, e = m.start(), m.end()
        if overlaps(s, e):
            continue
        before = text[:s]
        after = text[e:]
        if re.search(YEAR_PREFIX_RE + r'$', before):
            continue
        if before.endswith('年'):
            continue
        if re.match(r'[，。；]|薨|卒|免|有罪|坐|亡|迁|贬|徙|归|赐', after):
            add(s, e, f'〖%{m.group()}|时长〗')
    
    # 5. Duration: number+月 (without year) followed by verb/punctuation
    for m in re.finditer(NUM + r'月(?![' + STEM + r'])', text):
        s, e = m.start(), m.end()
        if overlaps(s, e):
            continue
        after = text[e:]
        if re.match(r'[，。；]|薨|卒|免|迁|贬|徙|归|赐|。', after):
            add(s, e, f'〖%{m.group()}|时长〗')
    
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
    
    # 7a. Single-char state names in context
    state_chars = "燕赵齐楚秦汉魏韩吴梁代鲁"
    for m in re.finditer(r'(?<=[击定入从起降攻破灭属都至击别复、为])[' + state_chars + r']', text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖◆{m.group()}〗')
    
    # 8. Place names: 〖=X〗
    for place in PLACES:
        for m in re.finditer(re.escape(place), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖={place}〗')
    
    # 9. Person names: 〖@X〗
    person_lookahead = r'(?=为|薨|迁|徙|免|卒|贬|归|赐|复|更|卒|。|，|；|｜|下|坐|有|病|死)'
    
    # 9a. Compound surnames FIRST (before 侯/矦 to avoid splitting)
    compound_surnames = r'(?:夏矦|夏侯|公上|毋将|申屠|叔孙|公孙)'
    for m in re.finditer(compound_surnames + r'[\u4e00-\u9fff]{1,2}' + person_lookahead, text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖@{m.group()}〗')
    
    # 9b. 侯/矦 + name (try shorter first)
    for nlen in [1, 2, 3]:
        for m in re.finditer(r'[矦侯][\u4e00-\u9fff]{%d}' % nlen + person_lookahead, text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖@{m.group()}〗')
    
    # 9b. Person name after 为 (appointment): 为 + title + person + verb
    # Skip - too ambiguous
    
    # 9c. Known person names that appear frequently
    known_persons = sorted([
        "萧何", "曹参", "周苛", "周昌", "周勃", "陈平", "王陵", "夏矦婴", "夏侯婴",
        "叔孙通", "郦商", "卢绾", "杜恬", "宣义", "赵尧", "王恬启", "义渠",
        "薛欧", "阳咸延", "丙猜", "戚鳃", "公上不害", "审食其", "刘泽",
        "张苍", "灌婴", "傅宽", "靳歙", "周灶", "丁复", "吕青", "鄂秋",
        "申屠嘉", "周亚夫", "田蚡", "公孙贺", "公孙弘", "李广", "卫青",
        "霍去病", "霍光", "张安世", "张禹", "史高", "王凤", "王商",
        "王音", "王根", "王莽", "师丹", "孔光", "王崇", "贾延",
        "公孙禄", "峤望", "方赏", "赵昌", "魏章", "毋将隆", "左威",
        "董恭", "龚胜", "申屠博", "耿丰", "孙云", "弘谭", "沛弘谭",
        "南夏常", "翟萌", "韦赏", "董贤", "王舜", "甄丰", "甄邯",
        "黄辅", "韩容", "孙建", "毕由", "梁相", "马宫", "丙昌",
        "杜业", "张宏", "钟元", "刘岑", "尹赏", "幸成", "武襄",
        "邓冯", "郝党", "赵恢", "金钦", "张嘉", "孙信", "谢尧",
        "钟义", "平晏", "王骏", "宗伯", "任岑", "赵昌",
    ], key=len, reverse=True)
    for person in known_persons:
        for m in re.finditer(re.escape(person), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'〖@{person}〗')
    
    # 10. Punishment verbs: ⟦◉X⟧
    for verb in VERBS_PUN:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦◉{verb}⟧')
    
    # 11. Negative verbs: ⟦◈X⟧
    for verb in VERBS_NEG:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦◈{verb}⟧')
    
    # 12. Positive verbs: ⟦○X⟧
    for verb in VERBS_POS:
        for m in re.finditer(re.escape(verb), text):
            s, e = m.start(), m.end()
            if not overlaps(s, e):
                add(s, e, f'⟦○{verb}⟧')
    
    # 13. Crimes: 〖:X〗
    for m in re.finditer(r'酎金', text):
        s, e = m.start(), m.end()
        if not overlaps(s, e):
            add(s, e, f'〖:{m.group()}〗')
    
    # Sort and remove overlaps
    anns.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered = []
    last_end = -1
    for s, e, r in anns:
        if s >= last_end:
            filtered.append((s, e, r))
            last_end = e
    
    return filtered

def apply_annotations(text, anns):
    result = text
    for s, e, r in reversed(anns):
        result = result[:s] + r + result[e:]
    return result

def annotate_row(content):
    parts = content.split('｜')
    if not parts:
        return content
    
    # Column 1: year (annotate as time marker if not just a number)
    if parts[0].strip():
        stripped = parts[0].strip()
        leading = parts[0][:len(parts[0]) - len(parts[0].lstrip())]
        trailing = parts[0][len(parts[0].rstrip()):]
        # Check if it's a year name or just a number
        if re.match(YEAR_PREFIX_RE + r'(?:元|' + NUM + r')年', stripped) or re.match(YEAR_COMPLETE_RE + r'年', stripped):
            parts[0] = f'{leading}〖%{stripped}〗{trailing}'
        elif re.match(r'元年', stripped):
            parts[0] = f'{leading}〖%{stripped}〗{trailing}'
    
    # Columns 2-14
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
            # Skip column headers [r1]-[r7]
            rnum = int(re.search(r'\d+', prefix).group())
            if rnum <= 7:
                output.append(line)
                continue
            annotated = annotate_row(content)
            output.append(f'{prefix}{annotated}')
        else:
            # Section headers and other lines: keep as-is
            output.append(line)
    
    DST.write_text('\n'.join(output), encoding='utf-8')
    print(f"Written to {DST}")

if __name__ == '__main__':
    main()
