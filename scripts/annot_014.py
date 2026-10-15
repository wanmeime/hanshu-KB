#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卷014 诸侯王表第二 标注器
序言段[0]-[5]：列传v2口径
表格段[r1]-[r?]：表类口径（王侯世系表）
铁律：去标记后与底本逐字全等。
"""
import re, sys

BASE = "data/chapter_numbered/卷014_诸侯王表第二.txt"
OUT  = "kg/entities/标注/卷014_标注.txt"

with open(BASE, encoding="utf-8") as f:
    text = f.read()

# 保护：把 ｜ (U+FF5C 全角竖线，表格列分隔) 临时替换，避免被规则误伤
SEP = "\ue000"   # PUA占位
text_work = text.replace("｜", SEP)

# ---------- 序言段名词规则 ----------
PERSONS = ["周公","康叔","太公","高祖","孝惠","高后","文帝","景帝","武帝","王莽",
           "贾生","鼌错","主父","王赧"]
IDENT = ["皇帝","庶人","天子","共主"]
POLITY = ["周","秦","汉","齐","赵","燕","代","梁","楚","荆吴","淮南","长沙","山东"]
INST = ["二等之爵","推恩之令","左官之律","附益之法","五等"]
BOOK = ["诗"]
QUANT = ["八百余年","三十余年","五十有余","数十","十五郡","百余邑","十余城",
         "八百","数百里","三垂"]

def anno_seq(seg):
    """序言段名词+动词标注"""
    for v in ["立","嗣","薨","诛","反","废","徙","绍封","篡位","削","分","谋反"]:
        seg = re.sub(rf'(?<!〖[@=;&#%^~•!?+◆{{:_$◈◉○◇\w]){v}(?![\w〗])', f'⟦○{v}⟧', seg)
    for w in sorted(PERSONS+IDENT+POLITY+INST+BOOK+QUANT, key=len, reverse=True):
        if w in IDENT: sym = "#"
        elif w in PERSONS: sym = "@"
        elif w in POLITY: sym = "◆"
        elif w in INST: sym = "^"
        elif w in BOOK: sym = "{"
        else: sym = "$"
        seg = re.sub(rf'(?<!〖[{re.escape("@=;&#%^~•!?+◆{:_$")}]){re.escape(w)}(?![\w〗])',
                     f'〖{sym}{w}〗', seg)
    return seg

# ---------- 表格段规则 ----------
def anno_table(seg):
    """表格段标注"""
    # 世系身份说明
    seg = re.sub(r'(高帝弟|高帝子|高帝兄|高帝从父|王子|宗室)', r'〖#\1〗', seg)
    # 王侯号+人名（行首常见）
    seg = re.sub(r'(楚元王交|代王喜|齐悼惠王肥|城阳景王章|济北王兴居|济北王志|济北王辟光|菑川王志|菑川王贤|胶西王卬|吴王濞|淮南王长|赵王遂|衡山王赐|梁王立|燕王旦)',
                 r'〖@\1〗', seg)
    # X王/X侯 泛指
    seg = re.sub(r'([一-鿿]{1,4}王)(?=[。，、]|立|嗣|薨|反|诛)', r'〖@\1〗', seg)
    seg = re.sub(r'([一-鿿]{1,4}侯)(?=[。，、]|立|嗣|绍封)', r'〖;\1〗', seg)
    # 时间：年号年
    seg = re.sub(r'(\d+年)(?=[，。]|薨|立|嗣)', r'〖%\1〗', seg)
    # 月份
    seg = re.sub(r'(正月|二月|三月|四月|五月|六月|七月|八月|九月|十月|十一月|十二月)', r'〖%\1〗', seg)
    # 动词（表格：立/嗣/薨/诛/反/废/徙/绍封 等，后面是逗号句号或列分隔）
    for v in ["绍封","篡位","谋反","自归","弃国","立","嗣","薨","诛","反","废","徙","攻"]:
        seg = re.sub(rf'({v})(?=[，。、]|{SEP}|$|\n)', rf'⟦○\1⟧', seg)
    # 数字
    seg = re.sub(r'(\d+)(?=[人城邑所年诸侯侯王馀])', r'〖$\1〗', seg)
    return seg

# ---------- 主流程 ----------
lines = text_work.split("\n")
out = []
for ln in lines:
    m = re.match(r'\[(r?)(\d*)\]', ln)
    if m and m.group(1) == 'r':
        out.append(anno_table(ln))
    elif m and m.group(1) == '' and m.group(2).isdigit() and int(m.group(2)) <= 5:
        out.append(anno_seq(ln))
    else:
        out.append(ln)

result = "\n".join(out).replace(SEP, "｜")

with open(OUT, "w", encoding="utf-8") as f:
    f.write(result)

print(f"已写入 {OUT}")
print(f"名词标记 {result.count('〖')}  动词标记 {result.count('⟦')}")
