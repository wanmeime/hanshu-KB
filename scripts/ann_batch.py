#!/usr/bin/env python3
"""批量标注：读 JSON {tag: annotated}，逐段校验后写入标注文件"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from annotate_station_local import chapter_file, parse_paras, strip_markers, load_done, ann_file, TYPE_CHARS

def main(juan, json_path):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    chf = chapter_file(juan)
    src = chf.read_text(encoding="utf-8")
    paras = dict(parse_paras(src))
    ok, fail = 0, []
    for tag, annotated in data.items():
        if tag not in paras:
            fail.append((tag, f"标号不存在")); continue
        stripped = strip_markers(annotated).rstrip()
        core = paras[tag].rstrip()
        if stripped != core:
            for i, (a, b) in enumerate(zip(stripped, core)):
                if a != b:
                    fail.append((tag, f"第{i}字: 标[{a}]vs底[{b}] ctx:{core[max(0,i-8):i+8]}")); break
            else:
                fail.append((tag, f"长度: 标{len(stripped)}vs底{len(core)} ctx尾:{core[-12:]}")); continue
        ok += 1
        data[tag] = annotated.rstrip() + paras[tag][len(core):]
    if fail:
        for t, e in fail: print(f"FAIL {t}: {e}")
        print(f"{ok} 段合格，{len(fail)} 段失败，未写入")
        sys.exit(1)
    done = load_done(juan)
    done.update(data)
    allp = parse_paras(src)
    out = [done.get(t, p) for t, p in allp]
    ann_file(juan).write_text("".join(out), encoding="utf-8")
    print(f"{juan}: 批量写入 {len(data)} 段，全部校验通过")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
