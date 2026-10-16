#!/bin/bash
# 卷015整卷标注：一次性MiMo调用+校验卡关
export PATH="/home/jiaoduan/.opencode/bin:$PATH"
cd /home/jiaoduan/shared/project/hanshu-KB

PROMPT=$(cat <<'EOF'
标注汉书卷015_王子侯表第三上，写入 kg/entities/标注/卷015_标注.txt。

步骤：
1. Read data/chapter_numbered/卷015_王子侯表第三上.txt 全文
2. 序言段[0]-[6]按列传口径；表格段[r1]-[r233]按表类口径标注
3. 写入 kg/entities/标注/卷015_标注.txt
4. 跑校验 python3 scripts/verify_annotation.py data/chapter_numbered/卷015_王子侯表第三上.txt kg/entities/标注/卷015_标注.txt
5. 只有PASS(退出码0)才算成功；非0则读报错修正重跑直到PASS

表格口径：
- 侯号+人名(羮颉侯信/合阳侯喜/上邳侯郢客) →〖@侯号人名〗
- 身份(帝兄子/齐悼惠王子/楚元王子/高帝弟) →〖#...〗(句末句号在标记外)
- 谥号王侯+人名(夷王郢客/顷侯通/康侯龁) →〖@谥号王侯人名〗
- 官爵(关内侯/列侯/丞相/大夫/公乘/司寇) →〖;...〗
- 时间(孝景三年/元康四年/五月甲寅/六年正月丙午) →〖%...〗；紧跟立嗣的N年 →〖%N年|时长〗
- 动词：立/嗣/薨/废/徙/绍封/封 →⟦○⟧；诛/自杀/要斩 →⟦◉⟧；反/谋反 →⟦◈⟧
- 数字(千户/一级/万家/百世) →〖$...〗
- 邦国(齐/楚/吴/淮南/中山) →〖◆...〗；地名 →〖=...〗
- 表头行[r1/r6/r10 号谥名开头]和[0]标题不标；[2]-[6]右X分段标记不标

铁律：
- PN编号[rN][0-6]和列分隔｜原样保留，一字不改不增不删
- 去标记后与底本逐字全等
- 稀有字PUA逐字复制，禁打同形字
- 行数空行结构与底本一致
- 禁凭记忆编造，每行对照底本
- 不grep研究，直接读底本标注校验修正到PASS
EOF
)

opencode run -m opencode/mimo-v2.6-flash-free "$PROMPT" 2>&1
