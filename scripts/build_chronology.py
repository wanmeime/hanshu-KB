#!/usr/bin/env python3
"""M4-2: 汉代年号映射 — 生成 reign_periods.json + year_ce_map.json + year_state_map.json + 汉书编年表.md
覆盖西汉全朝：高祖(前206) → 王莽新朝(公元23) → 更始帝(公元25)
"""
import json, os
from pathlib import Path

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
CHRON_DIR = BASE / "kg" / "chronology" / "data"
CHRON_DIR.mkdir(parents=True, exist_ok=True)

# 西汉帝王世系（含新朝和更始）
RULERS = [
    {"name": "汉高祖", "alias": ["高祖", "刘邦", "沛公"], "state": "汉", "start_bce": -206, "end_bce": -195, "era": None, "note": "前206年封汉王，前202年称帝"},
    {"name": "汉惠帝", "alias": ["惠帝", "孝惠帝", "刘盈"], "state": "汉", "start_bce": -195, "end_bce": -188, "era": None},
    {"name": "高后", "alias": ["吕后", "吕太后", "高后"], "state": "汉", "start_bce": -188, "end_bce": -180, "era": None, "note": "临朝称制"},
    {"name": "汉文帝", "alias": ["文帝", "孝文帝", "刘恒"], "state": "汉", "start_bce": -180, "end_bce": -157, "era": None},
    {"name": "汉景帝", "alias": ["景帝", "孝景帝", "刘启"], "state": "汉", "start_bce": -157, "end_bce": -141, "era": None},
    # 武帝开始有年号
    {"name": "汉武帝", "alias": ["武帝", "孝武帝", "刘彻"], "state": "汉", "start_bce": -141, "end_bce": -87, "era": "建元"},
    {"name": "汉昭帝", "alias": ["昭帝", "孝昭帝", "刘弗陵"], "state": "汉", "start_bce": -87, "end_bce": -74, "era": "始元"},
    {"name": "汉宣帝", "alias": ["宣帝", "孝宣帝", "刘询"], "state": "汉", "start_bce": -74, "end_bce": -49, "era": "本始"},
    {"name": "汉元帝", "alias": ["元帝", "孝元帝", "刘奭"], "state": "汉", "start_bce": -49, "end_bce": -33, "era": "初元"},
    {"name": "汉成帝", "alias": ["成帝", "孝成帝", "刘骜"], "state": "汉", "start_bce": -33, "end_bce": -7, "era": "建始"},
    {"name": "汉哀帝", "alias": ["哀帝", "孝哀帝", "刘欣"], "state": "汉", "start_bce": -7, "end_bce": -1, "era": "建平"},
    {"name": "汉平帝", "alias": ["平帝", "孝平帝", "刘衎"], "state": "汉", "start_bce": -1, "end_bce": 5, "era": "元始"},
    {"name": "孺子婴", "alias": ["孺子", "婴"], "state": "汉", "start_bce": 6, "end_bce": 8, "era": "居摄", "note": "王莽摄政"},
    {"name": "王莽", "alias": ["王莽", "新莽"], "state": "新", "start_bce": 9, "end_bce": 23, "era": "始建国", "note": "新朝"},
    {"name": "更始帝", "alias": ["更始", "刘玄"], "state": "汉", "start_bce": 23, "end_bce": 25, "era": None, "note": "更始政权"},
]

# 年号表：(年号名, 起始公元年, 结束公元年, 帝王)
ERAS = [
    # 武帝
    ("建元", -140, -135, "汉武帝"),
    ("元光", -134, -129, "汉武帝"),
    ("元朔", -128, -123, "汉武帝"),
    ("元狩", -122, -117, "汉武帝"),
    ("元鼎", -116, -111, "汉武帝"),
    ("元封", -110, -105, "汉武帝"),
    ("太初", -104, -101, "汉武帝"),
    ("天汉", -100, -97, "汉武帝"),
    ("太始", -96, -93, "汉武帝"),
    ("征和", -92, -89, "汉武帝"),
    ("后元", -88, -87, "汉武帝"),
    # 昭帝
    ("始元", -86, -81, "汉昭帝"),
    ("元凤", -80, -75, "汉昭帝"),
    ("元平", -74, -74, "汉昭帝"),
    # 宣帝
    ("本始", -73, -70, "汉宣帝"),
    ("地节", -69, -66, "汉宣帝"),
    ("元康", -65, -62, "汉宣帝"),
    ("神爵", -61, -58, "汉宣帝"),
    ("五凤", -57, -54, "汉宣帝"),
    ("甘露", -53, -50, "汉宣帝"),
    ("黄龙", -49, -49, "汉宣帝"),
    # 元帝
    ("初元", -48, -44, "汉元帝"),
    ("永光", -43, -39, "汉元帝"),
    ("建昭", -38, -34, "汉元帝"),
    ("竟宁", -33, -33, "汉元帝"),
    # 成帝
    ("建始", -32, -29, "汉成帝"),
    ("河平", -28, -25, "汉成帝"),
    ("阳朔", -24, -21, "汉成帝"),
    ("鸿嘉", -20, -17, "汉成帝"),
    ("永始", -16, -13, "汉成帝"),
    ("元延", -12, -9, "汉成帝"),
    ("绥和", -8, -7, "汉成帝"),
    # 哀帝
    ("建平", -6, -3, "汉哀帝"),
    ("元寿", -2, -1, "汉哀帝"),
    # 平帝
    ("元始", 1, 5, "汉平帝"),
    # 孺子婴（王莽摄政）
    ("居摄", 6, 8, "孺子婴"),
    ("初始", 8, 8, "孺子婴"),
    # 王莽新朝
    ("始建国", 9, 13, "王莽"),
    ("天凤", 14, 19, "王莽"),
    ("地皇", 20, 23, "王莽"),
    # 更始
    ("更始", 23, 25, "更始帝"),
]

def build_reign_periods():
    """生成帝王在位数据"""
    rulers = {}
    for r in RULERS:
        rulers[r["name"]] = {
            "state": r["state"],
            "start_bce": r["start_bce"],
            "end_bce": r["end_bce"],
            "alias": r.get("alias", []),
        }
        if "note" in r:
            rulers[r["name"]]["note"] = r["note"]
        if r.get("era"):
            rulers[r["name"]]["first_era"] = r["era"]
    
    data = {"rulers": rulers}
    with open(CHRON_DIR / "reign_periods.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(rulers)

def build_year_ce_map():
    """生成年号→公元映射"""
    year_map = {}
    for era_name, start_ce, end_ce, ruler in ERAS:
        for year_num in range(1, end_ce - start_ce + 2):
            ce_year = start_ce + year_num - 1
            year_key = f"{era_name}{num_to_chinese(year_num)}年"
            year_map[year_key] = {
                "ruler": ruler,
                "ce_year": ce_year,
                "era": era_name,
                "era_year": year_num,
            }
        # 元年
        year_map[f"{era_name}元年"] = {
            "ruler": ruler,
            "ce_year": start_ce,
            "era": era_name,
            "era_year": 1,
        }
    
    with open(CHRON_DIR / "year_ce_map.json", 'w', encoding='utf-8') as f:
        json.dump(year_map, f, ensure_ascii=False, indent=2)
    return len(year_map)

def build_year_state_map():
    """生成年号→朝代映射"""
    state_map = {}
    for era_name, start_ce, end_ce, ruler in ERAS:
        state = "新" if ruler == "王莽" else "汉"
        state_map[era_name] = {
            "ruler": ruler,
            "state": state,
            "start_ce": start_ce,
            "end_ce": end_ce,
            "duration": end_ce - start_ce + 1,
        }
    
    with open(CHRON_DIR / "year_state_map.json", 'w', encoding='utf-8') as f:
        json.dump(state_map, f, ensure_ascii=False, indent=2)
    return len(state_map)

def num_to_chinese(n):
    """数字转中文"""
    digits = "零一二三四五六七八九"
    if n <= 9:
        return digits[n]
    if n < 20:
        return "十" + (digits[n-10] if n > 10 else "")
    if n < 100:
        tens = n // 10
        ones = n % 10
        return digits[tens] + "十" + (digits[ones] if ones else "")
    return str(n)

def build_chronology_md():
    """生成汉书编年表.md"""
    lines = [
        "# 汉书编年表",
        "",
        f"> 西汉全朝纪年：前206年（高祖元年）→ 公元25年（更始三年）",
        f"> 共 {len(RULERS)} 位帝王/摄政者，{len(ERAS)} 个年号",
        "",
        "## 帝王世系",
        "",
        "| 序号 | 帝王 | 朝代 | 在位起（BCE/CE） | 在位止 | 在位年数 | 首个年号 | 备注 |",
        "|------|------|------|-----------------|--------|---------|---------|------|",
    ]
    
    for i, r in enumerate(RULERS, 1):
        start = r["start_bce"]
        end = r["end_bce"]
        duration = end - start + 1
        start_str = f"前{-start}年" if start < 0 else f"公元{start}年"
        end_str = f"前{-end}年" if end < 0 else f"公元{end}年"
        era_str = r.get("era", "—") or "—"
        note_str = r.get("note", "")
        lines.append(f"| {i} | {r['name']} | {r['state']} | {start_str} | {end_str} | {duration} | {era_str} | {note_str} |")
    
    lines.extend([
        "",
        "## 年号表",
        "",
        "| 序号 | 年号 | 帝王 | 起始年 | 终止年 | 年数 |",
        "|------|------|------|--------|--------|------|",
    ])
    
    for i, (era, start, end, ruler) in enumerate(ERAS, 1):
        start_str = f"前{-start}年" if start < 0 else f"公元{start}年"
        end_str = f"前{-end}年" if end < 0 else f"公元{end}年"
        duration = end - start + 1
        lines.append(f"| {i} | {era} | {ruler} | {start_str} | {end_str} | {duration} |")
    
    lines.extend([
        "",
        "## 年号→公元换算速查",
        "",
    ])
    
    for era_name, start_ce, end_ce, ruler in ERAS:
        lines.append(f"### {era_name}（{ruler}）")
        lines.append("")
        lines.append("| 年号纪年 | 公元年 |")
        lines.append("|---------|--------|")
        for year_num in range(1, end_ce - start_ce + 2):
            ce = start_ce + year_num - 1
            ce_str = f"前{-ce}年" if ce < 0 else f"公元{ce}年"
            year_str = f"{era_name}{num_to_chinese(year_num)}年"
            lines.append(f"| {year_str} | {ce_str} |")
        lines.append("")
    
    with open(CHRON_DIR / "汉书编年表.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    print("=== M4-2: 汉代年号映射 ===")
    n_rulers = build_reign_periods()
    n_years = build_year_ce_map()
    n_eras = build_year_state_map()
    build_chronology_md()
    
    print(f"  reign_periods.json: {n_rulers} 位帝王")
    print(f"  year_ce_map.json: {n_years} 个年号纪年")
    print(f"  year_state_map.json: {n_eras} 个年号")
    print(f"  汉书编年表.md: 已生成")
    print(f"\n=== M4-2 完成 ===")

if __name__ == '__main__':
    main()
