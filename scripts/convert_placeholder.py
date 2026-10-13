#!/usr/bin/env python3
"""把 ASCII 占位符标注稿转成正式标注符号：
  [[X...]]  -> 〖X...〗        ((V...))  ->  ⟦V...⟧
  X: a=@ b=; c=# d=% e=& f=~ g=◆ h=• i=! j=? k=+ l={ m=: n=[ o=_ p=$
  V: A=◈ B=◉ C=○ D=◇
用法: python3 scripts/convert_placeholder.py <输入> <输出>
"""
import sys

TYPE = {'a': '@', 'b': ';', 'c': '#', 'd': '%', 'e': '&', 'f': '~', 'g': '◆',
        'h': '•', 'i': '!', 'j': '?', 'k': '+', 'l': '{', 'm': ':', 'n': '[',
        'o': '_', 'p': '$', 'q': '^', 'r': '='}
VERB = {'A': '◈', 'B': '◉', 'C': '○', 'D': '◇'}


def convert(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith('[[', i) and i + 2 < n and text[i + 2] in TYPE:
            out.append('〖' + TYPE[text[i + 2]]); i += 3
        elif text.startswith(']]', i):
            out.append('〗'); i += 2
        elif text.startswith('((', i) and i + 2 < n and text[i + 2] in VERB:
            out.append('⟦' + VERB[text[i + 2]]); i += 3
        elif text.startswith('))', i):
            out.append('⟧'); i += 2
        else:
            out.append(text[i]); i += 1
    return ''.join(out)


def main(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    conv = []
    for ln in lines:
        if '\t' in ln or (ln and not ln.strip()):
            idx, _, text = ln.partition('\t')
            conv.append(idx + '\t' + convert(text))
        else:
            conv.append(convert(ln))
    open(dst, 'w', encoding='utf-8').write('\n'.join(conv))
    print(f'OK {dst}  ({len(conv)} 行)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
