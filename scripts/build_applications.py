#!/usr/bin/env python3
"""M6-1/2/3/4: 语法高亮 + 语义搜索索引 + 历史地图 + 信息图可视化
生成应用层产出：HTML着色阅读器 + 搜索索引 + 地图数据 + 时间线/网络图
"""
import json, os, re, html
from pathlib import Path
from collections import defaultdict

BASE = Path(os.environ.get("HSKB_BASE", "/home/jiaoduan/shared/project/hanshu-KB"))
ANN_DIR = BASE / "kg" / "entities" / "标注"
APP_DIR = BASE / "kg" / "applications"
APP_DIR.mkdir(parents=True, exist_ok=True)

NOUN_RE = re.compile(r'〖([@=;%&~•!?+{:[_◆$^#])([^〗]*)〗')
VERB_RE = re.compile(r'⟦([○◈◉◇])([^⟧]*)⟧')
PARA_RE = re.compile(r'^\[(\d+(?:\.\d+)?)\]\s')

# 实体类型颜色映射（CSS颜色）
TYPE_COLORS = {
    '@': '#E74C3C',  # 人名-红
    '=': '#27AE60',  # 地名-绿
    ';': '#2980B9',  # 官职-蓝
    '#': '#8E44AD',  # 身份-紫
    '%': '#E67E22',  # 时间-橙
    '&': '#16A085',  # 朝代-青
    '◆': '#C0392B',  # 邦国-深红
    '^': '#34495E',  # 制度-深灰
    '~': '#D35400',  # 族群-深橙
    '•': '#7F8C8D',  # 器物-灰
    '!': '#F1C40F',  # 天文-黄
    '?': '#9B59B6',  # 神话-浅紫
    '+': '#2ECC71',  # 生物-浅绿
    '{': '#1ABC9C',  # 典籍-青绿
    ':': '#3498DB',  # 礼仪-浅蓝
    '[': '#E74C3C',  # 刑法-红
    '_': '#95A5A6',  # 思想-浅灰
    '$': '#F39C12',  # 数量-金
}

TYPE_NAMES = {
    '@': '人名', '=': '地名', ';': '官职', '#': '身份', '%': '时间',
    '&': '朝代', '◆': '邦国', '^': '制度', '~': '族群', '•': '器物',
    '!': '天文', '?': '神话', '+': '生物', '{': '典籍', ':': '礼仪',
    '[': '刑法', '_': '思想', '$': '数量',
}

VERB_COLORS = {
    '○': '#2980B9',  # 政治-蓝
    '◈': '#E74C3C',  # 军事-红
    '◉': '#C0392B',  # 刑罚-深红
    '◇': '#F39C12',  # 经济-金
}

VERB_NAMES = {
    '○': '政治', '◈': '军事', '◉': '刑罚', '◇': '经济',
}

def get_juan_titles():
    titles = {}
    src_dir = BASE / "data" / "chapter_numbered"
    for f in sorted(src_dir.glob("卷*.txt")):
        m = re.match(r'(卷\d+[a-z]?)_(.+)\.txt', f.name)
        if m:
            titles[m.group(1)] = m.group(2)
    return titles

def extract_juan_short(filename):
    m = re.match(r'(卷\d+[a-z]?)_标注\.txt', filename)
    return m.group(1) if m else filename.replace('_标注.txt', '')

def render_text_to_html(text):
    """将标注文本渲染为带颜色的HTML"""
    result = []
    pos = 0
    
    # 合并名词和动词标记
    marks = []
    for m in NOUN_RE.finditer(text):
        marks.append(('noun', m))
    for m in VERB_RE.finditer(text):
        marks.append(('verb', m))
    marks.sort(key=lambda x: x[1].start())
    
    for mark_type, m in marks:
        # 添加标记前的文本
        if m.start() > pos:
            result.append(html.escape(text[pos:m.start()]))
        
        if mark_type == 'noun':
            symbol = m.group(1)
            raw = m.group(2)
            color = TYPE_COLORS.get(symbol, '#000000')
            type_name = TYPE_NAMES.get(symbol, '未知')
            
            if '|' in raw:
                display, canonical = raw.split('|', 1)
            else:
                display = canonical = raw
            
            # 生成带颜色的span
            title = f"{type_name}"
            if canonical != display:
                title += f" → {canonical}"
            
            result.append(
                f'<span class="entity" style="color:{color}" title="{html.escape(title)}">'
                f'{html.escape(display)}</span>'
            )
        else:
            vtype = m.group(1)
            vcontent = m.group(2)
            color = VERB_COLORS.get(vtype, '#000000')
            type_name = VERB_NAMES.get(vtype, '未知')
            
            result.append(
                f'<span class="verb" style="color:{color};font-weight:bold" title="{type_name}动词">'
                f'{html.escape(vcontent)}</span>'
            )
        
        pos = m.end()
    
    # 添加最后一段文本
    if pos < len(text):
        result.append(html.escape(text[pos:]))
    
    return ''.join(result)

def build_syntax_highlighter():
    """M6-1: 语法高亮辅助阅读"""
    print("=== M6-1: 语法高亮辅助阅读 ===")
    
    juan_titles = get_juan_titles()
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    output_dir = APP_DIR / "syntax_highlight"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成图例
    legend_items = []
    for symbol, color in TYPE_COLORS.items():
        name = TYPE_NAMES.get(symbol, '')
        legend_items.append(f'<span style="color:{color}">■</span> {name}')
    for vtype, color in VERB_COLORS.items():
        name = VERB_NAMES.get(vtype, '')
        legend_items.append(f'<span style="color:{color};font-weight:bold">■</span> {name}动词')
    
    # 为每卷生成HTML
    for filepath in ann_files:
        juan_short = extract_juan_short(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="UTF-8">',
            f'<title>{juan_short}_{juan_title}</title>',
            '<style>',
            'body { font-family: "Noto Serif CJK SC", serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.8; }',
            '.entity { cursor: help; border-bottom: 1px dotted currentColor; }',
            '.verb { cursor: help; }',
            '.paragraph { margin: 10px 0; text-indent: 2em; }',
            '.para-id { color: #999; font-size: 0.8em; margin-right: 10px; }',
            '.legend { background: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 20px; }',
            '.legend span { margin-right: 15px; }',
            'h1 { text-align: center; }',
            '</style>',
            '</head>',
            '<body>',
            f'<h1>{juan_short}《{juan_title}》</h1>',
            '<div class="legend">',
            '<strong>实体类型图例：</strong> ',
            ' '.join(legend_items),
            '</div>',
        ]
        
        for line in content.split('\n'):
            m = PARA_RE.match(line)
            if not m:
                continue
            para_id = m.group(1)
            para_text = line[m.end():]
            if not para_text.strip():
                continue
            
            html_text = render_text_to_html(para_text)
            html_parts.append(f'<div class="paragraph"><span class="para-id">[{para_id}]</span>{html_text}</div>')
        
        html_parts.extend(['</body>', '</html>'])
        
        with open(output_dir / f"{juan_short}.html", 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))
    
    # 生成索引页
    index_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head><meta charset="UTF-8"><title>汉书KB - 语法高亮阅读</title>',
        '<style>body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px}a{display:block;padding:5px;color:#2980B9;text-decoration:none}a:hover{background:#f5f5f5}</style>',
        '</head><body>',
        '<h1>汉书知识库 - 语法高亮辅助阅读</h1>',
        f'<p>共 {len(ann_files)} 卷</p>',
    ]
    
    for filepath in ann_files:
        juan_short = extract_juan_short(filepath.name)
        juan_title = juan_titles.get(juan_short, juan_short)
        index_parts.append(f'<a href="{juan_short}.html">{juan_short}《{juan_title}》</a>')
    
    index_parts.append('</body></html>')
    with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write('\n'.join(index_parts))
    
    print(f"  生成 {len(ann_files)} 个HTML文件 + 索引页")
    return len(ann_files)

def build_search_index():
    """M6-2: 语义搜索索引"""
    print("=== M6-2: 语义搜索索引 ===")
    
    entity_index = json.load(open(BASE / "kg" / "entities" / "entity_index.json", 'r', encoding='utf-8'))
    
    # 构建搜索索引
    search_index = []
    for key, entity in entity_index.items():
        entry = {
            'key': key,
            'type': entity['type'],
            'display': entity['display'],
            'canonical': entity.get('canonical', ''),
            'count': entity['count'],
            'chapters': entity['chapters'],
        }
        # 添加搜索文本（显示名 + 规范名）
        search_text = entity['display']
        if entity.get('canonical') and entity['canonical'] != entity['display']:
            search_text += ' ' + entity['canonical']
        entry['search_text'] = search_text
        search_index.append(entry)
    
    # 按出现次数排序
    search_index.sort(key=lambda x: -x['count'])
    
    # 生成索引JSON
    output_dir = APP_DIR / "semantic_search"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "search_index.json", 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    
    # 生成搜索页面
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head><meta charset="UTF-8"><title>汉书KB - 语义搜索</title>',
        '<style>',
        'body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px}',
        '#search-box{width:100%;padding:10px;font-size:16px;margin-bottom:20px}',
        '.result{padding:10px;border-bottom:1px solid #eee}',
        '.result .type{color:#999;font-size:0.8em}',
        '.result .display{font-size:1.2em;font-weight:bold}',
        '.result .count{color:#666}',
        '</style>',
        '</head><body>',
        '<h1>汉书知识库 - 语义搜索</h1>',
        '<input type="text" id="search-box" placeholder="输入人名、地名、官职等..." onkeyup="search()">',
        f'<p>共 {len(search_index)} 个实体</p>',
        '<div id="results"></div>',
        '<script>',
        f'const index = {json.dumps(search_index[:5000], ensure_ascii=False)};',
        '''function search() {
            const q = document.getElementById('search-box').value.toLowerCase();
            const results = document.getElementById('results');
            if (!q) { results.innerHTML = ''; return; }
            const matched = index.filter(e => 
                e.display.toLowerCase().includes(q) || 
                (e.canonical && e.canonical.toLowerCase().includes(q)) ||
                e.type.includes(q)
            ).slice(0, 100);
            results.innerHTML = matched.map(e => 
                `<div class="result"><span class="type">${e.type}</span> <span class="display">${e.display}</span>` +
                (e.canonical && e.canonical !== e.display ? ` → ${e.canonical}` : '') +
                ` <span class="count">(${e.count}次)</span></div>`
            ).join('');
        }''',
        '</script></body></html>',
    ]
    
    with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    
    print(f"  搜索索引：{len(search_index)} 个实体")
    return len(search_index)

def build_historical_map():
    """M6-3: 历史地图数据"""
    print("=== M6-3: 历史地图数据 ===")
    
    # 西汉主要地名→经纬度（已知地理数据）
    place_coords = {
        "长安": (108.91, 34.27), "洛阳": (112.45, 34.62), "咸阳": (108.72, 34.33),
        "沛": (116.92, 34.72), "丰": (116.92, 34.72), "彭城": (117.18, 34.27),
        "邯郸": (114.54, 36.62), "临淄": (118.67, 36.81), "蓟": (116.37, 39.91),
        "荥阳": (113.38, 34.76), "成皋": (113.38, 34.76), "函谷关": (110.87, 34.57),
        "南阳": (112.53, 33.00), "汉中": (107.03, 33.07), "蜀": (104.07, 30.67),
        "代": (112.73, 39.33), "淮南": (117.02, 32.63), "长沙": (112.94, 28.23),
        "会稽": (120.58, 30.00), "九江": (116.50, 29.85), "东海": (118.77, 34.60),
        "琅邪": (119.10, 35.35), "上党": (112.87, 36.50), "太原": (112.55, 37.87),
        "云中": (111.65, 40.75), "雁门": (112.73, 39.33), "代郡": (114.88, 40.42),
        "定襄": (111.55, 40.87), "五原": (109.77, 40.77), "朔方": (106.87, 40.72),
        "北地": (107.92, 35.77), "上郡": (109.47, 38.27), "西河": (110.58, 37.77),
        "陇西": (104.63, 35.07), "天水": (105.57, 34.58), "金城": (103.82, 36.07),
        "武威": (102.63, 37.93), "张掖": (100.47, 38.93), "酒泉": (98.50, 39.73),
        "敦煌": (94.67, 40.13), "安定": (106.67, 35.47), "右北平": (119.27, 41.27),
        "辽西": (120.83, 41.77), "辽东": (123.17, 41.83), "玄菟": (125.33, 42.87),
        "乐浪": (126.97, 39.77), "真定": (114.50, 38.05), "中山": (114.50, 38.05),
        "河间": (116.37, 38.37), "广平": (114.47, 36.77), "平原": (116.57, 37.10),
        "济南": (117.00, 36.67), "齐郡": (118.67, 36.81), "千乘": (118.17, 37.17),
        "北海": (119.17, 36.77), "东莱": (120.17, 37.50), "琅邪郡": (119.10, 35.35),
        "城阳": (118.47, 35.67), "胶东": (120.33, 36.77), "高密": (119.77, 36.38),
        "楚国": (117.18, 34.27), "鲁国": (116.83, 35.53), "魏郡": (114.50, 36.27),
        "巨鹿": (115.00, 37.22), "清河": (115.67, 37.07), "广阳": (116.37, 39.91),
        "渤海": (117.17, 38.27), "涿郡": (115.97, 39.47), "上谷": (115.17, 40.47),
        "渔阳": (117.17, 40.37), "右北平郡": (119.27, 41.27),
        "南郡": (112.23, 30.35), "江夏": (114.32, 30.53), "桂阳": (112.73, 25.77),
        "武陵": (111.68, 29.03), "零陵": (111.58, 26.23), "豫章": (115.92, 28.68),
        "丹阳": (119.17, 31.77), "会稽郡": (120.58, 30.00), "庐江": (117.27, 31.33),
        "六安": (116.50, 31.77), "九江郡": (116.50, 29.85),
        "巴郡": (106.55, 29.57), "蜀郡": (104.07, 30.67), "广汉": (104.17, 31.13),
        "犍为": (104.37, 29.77), "越巂": (102.27, 28.77), "益州": (102.72, 25.03),
        "牂柯": (106.72, 26.58), "武都": (104.93, 33.40),
        "并州": (112.55, 37.87), "凉州": (102.63, 37.93), "益州刺史部": (104.07, 30.67),
        "幽州": (116.37, 39.91), "朔方刺史部": (106.87, 40.72), "交趾": (108.37, 21.87),
    }
    
    # 从标注文件提取地名频率
    place_freq = defaultdict(int)
    ann_files = sorted(ANN_DIR.glob("卷*_标注.txt"))
    
    for filepath in ann_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        for m in NOUN_RE.finditer(content):
            if m.group(1) == '=':
                place = m.group(2).split('|')[0].strip()
                if place:
                    place_freq[place] += 1
    
    # 生成地图数据
    map_data = []
    for place, freq in sorted(place_freq.items(), key=lambda x: -x[1]):
        coords = place_coords.get(place)
        entry = {
            'name': place,
            'frequency': freq,
            'has_coords': coords is not None,
        }
        if coords:
            entry['lng'] = coords[0]
            entry['lat'] = coords[1]
        map_data.append(entry)
    
    output_dir = APP_DIR / "historical_map"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "place_data.json", 'w', encoding='utf-8') as f:
        json.dump(map_data, f, ensure_ascii=False, indent=2)
    
    # 生成地图HTML
    mapped_count = sum(1 for d in map_data if d['has_coords'])
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head><meta charset="UTF-8"><title>汉书KB - 历史地图</title>',
        '<style>body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px}table{width:100%}td{padding:5px;border-bottom:1px solid #eee}</style>',
        '</head><body>',
        '<h1>汉书知识库 - 历史地图数据</h1>',
        f'<p>共 {len(map_data)} 个地名，其中 {mapped_count} 个有经纬度坐标</p>',
        '<table><tr><th>地名</th><th>出现次数</th><th>经度</th><th>纬度</th></tr>',
    ]
    
    for d in map_data[:200]:
        if d['has_coords']:
            html_parts.append(f'<tr><td>{d["name"]}</td><td>{d["frequency"]}</td><td>{d["lng"]}</td><td>{d["lat"]}</td></tr>')
    
    html_parts.extend(['</table></body></html>'])
    with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    
    print(f"  地名：{len(map_data)} 个，有坐标：{mapped_count} 个")
    return len(map_data), mapped_count

def build_visualization():
    """M6-4: 信息图与可视化（时间线 + 关系网络图数据）"""
    print("=== M6-4: 信息图与可视化 ===")
    
    output_dir = APP_DIR / "visualization"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 帝王时间线
    gen_data = json.load(open(BASE / "kg" / "genealogy" / "imperial_genealogy.json", 'r', encoding='utf-8'))
    
    timeline_data = []
    for emp in gen_data['emperors']:
        timeline_data.append({
            'name': emp['name'],
            'alias': emp['alias'],
            'start': emp['start_bce'],
            'end': emp['end_bce'],
            'reign': emp['reign'],
            'father': emp['father'],
        })
    
    with open(output_dir / "emperor_timeline.json", 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=2)
    
    # 2. 关系网络图数据（取高频人物的关系）
    rel_data = json.load(open(BASE / "kg" / "relations" / "all_relations.json", 'r', encoding='utf-8'))
    entity_index = json.load(open(BASE / "kg" / "entities" / "entity_index.json", 'r', encoding='utf-8'))
    
    # 取前100高频人物
    top_persons = sorted(
        [e for e in entity_index.values() if e['symbol'] == '@'],
        key=lambda x: -x['count']
    )[:100]
    top_names = {e['display'] for e in top_persons}
    
    # 构建网络图
    nodes = [{'id': e['display'], 'label': e['display'], 'count': e['count']} for e in top_persons]
    edges = []
    
    for rel_type, rels in rel_data['relations'].items():
        if rel_type == '共现':
            continue  # 跳过共现关系，太多
        for r in rels:
            if r['p1'] in top_names and r['p2'] in top_names and r['p1'] != r['p2']:
                edges.append({
                    'source': r['p1'],
                    'target': r['p2'],
                    'type': rel_type,
                })
    
    network_data = {'nodes': nodes, 'edges': edges[:500]}  # 限制边数
    
    with open(output_dir / "relation_network.json", 'w', encoding='utf-8') as f:
        json.dump(network_data, f, ensure_ascii=False, indent=2)
    
    # 3. 事件时间分布
    events_data = json.load(open(BASE / "kg" / "events" / "data" / "all_events.json", 'r', encoding='utf-8'))
    
    # 按卷统计事件数
    chapter_event_counts = []
    for juan, data in events_data.items():
        chapter_event_counts.append({
            'chapter': juan,
            'title': data['title'],
            'count': data['count'],
        })
    chapter_event_counts.sort(key=lambda x: x['count'], reverse=True)
    
    with open(output_dir / "event_distribution.json", 'w', encoding='utf-8') as f:
        json.dump(chapter_event_counts, f, ensure_ascii=False, indent=2)
    
    # 生成可视化HTML
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head><meta charset="UTF-8"><title>汉书KB - 可视化</title>',
        '<style>body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px}</style>',
        '</head><body>',
        '<h1>汉书知识库 - 可视化数据</h1>',
        '<h2>帝王时间线</h2>',
        '<table border="1" style="width:100%"><tr><th>帝王</th><th>在位起</th><th>在位止</th><th>年数</th></tr>',
    ]
    
    for emp in timeline_data:
        start_s = f"前{-emp['start']}年" if emp['start'] < 0 else f"公元{emp['start']}年"
        end_s = f"前{-emp['end']}年" if emp['end'] < 0 else f"公元{emp['end']}年"
        html_parts.append(f'<tr><td>{emp["name"]}({emp["alias"]})</td><td>{start_s}</td><td>{end_s}</td><td>{emp["reign"]}</td></tr>')
    
    html_parts.extend([
        '</table>',
        f'<h2>关系网络图</h2><p>{len(nodes)} 个节点，{len(edges[:500])} 条边</p>',
        f'<h2>事件分布</h2><p>共 {sum(c["count"] for c in chapter_event_counts)} 个事件</p>',
        '</body></html>',
    ])
    
    with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    
    print(f"  时间线：{len(timeline_data)} 帝王")
    print(f"  网络图：{len(nodes)} 节点，{len(edges[:500])} 边")
    print(f"  事件分布：{len(chapter_event_counts)} 卷")
    
    return len(nodes), len(edges[:500])

def main():
    print("=== M6: 应用构造 ===")
    
    n_html = build_syntax_highlighter()
    n_search = build_search_index()
    n_places, n_mapped = build_historical_map()
    n_nodes, n_edges = build_visualization()
    
    print(f"\n=== M6 完成 ===")
    print(f"语法高亮：{n_html} HTML文件")
    print(f"搜索索引：{n_search} 实体")
    print(f"历史地图：{n_places} 地名（{n_mapped} 有坐标）")
    print(f"可视化：{n_nodes} 节点 + {n_edges} 边")

if __name__ == '__main__':
    main()
