#!/usr/bin/env python3
"""Auto-annotate 卷020 古今人表第八."""
import re
from pathlib import Path

BASE = Path("/home/jiaoduan/shared/project/hanshu-KB")
SRC = BASE / "data/chapter_numbered/卷020_古今人表第八.txt"
DST = BASE / "kg/entities/标注/卷020_标注.txt"

def annotate_preface(text):
    """Annotate the preface paragraph."""
    # Person names in the preface
    persons = sorted([
        "孔子", "尧舜", "禹", "稷", "禼", "鮌", "讙兜", "桀纣", "龙逢", "比干",
        "于莘", "崇侯", "齐桓公", "管仲", "竖貂", "唐虞", "宓羲", "神农", "黄帝",
        "少昊", "颛顼", "帝喾", "帝尧", "帝舜",
    ], key=len, reverse=True)
    
    # Book names
    books = ["书契"]
    
    anns = []
    used = set()
    
    # Annotate person names
    for person in persons:
        for m in re.finditer(re.escape(person), text):
            s, e = m.start(), m.end()
            if not any(a <= s < b or a < e <= b for a, b in used):
                anns.append((s, e, f'〖@{person}〗'))
                used.add((s, e))
    
    # Sort and apply
    anns.sort(key=lambda x: x[0])
    result = text
    for s, e, r in reversed(anns):
        result = result[:s] + r + result[e:]
    return result

def annotate_row(content):
    """Annotate a data row - wrap each non-empty cell in 〖@X〗."""
    parts = content.split('｜')
    for i in range(len(parts)):
        stripped = parts[i].strip()
        if stripped:
            leading = parts[i][:len(parts[i]) - len(parts[i].lstrip())]
            trailing = parts[i][len(parts[i].rstrip()):]
            parts[i] = f'{leading}〖@{stripped}〗{trailing}'
    return '｜'.join(parts)

def main():
    lines = SRC.read_text(encoding='utf-8').split('\n')
    output = []
    
    for line in lines:
        # Match [rN] pattern
        m = re.match(r'^(\[r\d+\])(.*)$', line)
        if m:
            prefix = m.group(1)
            content = m.group(2)
            # Skip column headers [r1] and category labels [r2]
            rnum = int(re.search(r'\d+', prefix).group())
            if rnum <= 2:
                output.append(line)
                continue
            annotated = annotate_row(content)
            output.append(f'{prefix}{annotated}')
        elif line.startswith('[1]'):
            # Annotate preface
            content = line[3:]
            annotated = annotate_preface(content)
            output.append(f'[1]{annotated}')
        else:
            output.append(line)
    
    DST.write_text('\n'.join(output), encoding='utf-8')
    print(f"Written to {DST}")

if __name__ == '__main__':
    main()
