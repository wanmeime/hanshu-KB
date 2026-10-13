# OpenCode 进度台账 · 五行志5卷标注

## 本批次完成情况

| 篇目 | 状态 | 校验 | 标记量 |
|------|------|------|--------|
| 卷027 五行志第七上 | ✅ 落盘 | PASS | 1499 名词 + 192 动词 |
| 卷027b 五行志第七中之上 | ✅ 落盘 | PASS | 1940 名词 + 250 动词 |
| 卷027c 五行志第七中之下 | ✅ 落盘 | PASS | 948 名词 + 196 动词 |
| 卷027d 五行志第七下之上 | ✅ 落盘 | PASS | 1139 名词 + 222 动词 |
| 卷027e 五行志第七下之下 | ✅ 落盘 | PASS | 1417 名词 + 332 动词 |

校验命令（每篇收尾必跑，退出码 0 方可落盘）：

```
python3 scripts/verify_annotation.py data/chapter_numbered/卷027_五行志第七上.txt   kg/entities/标注/卷027_标注.txt
python3 scripts/verify_annotation.py data/chapter_numbered/卷027b_五行志第七中之上.txt kg/entities/标注/卷027b_标注.txt
python3 scripts/verify_annotation.py data/chapter_numbered/卷027c_五行志第七中之下.txt kg/entities/标注/卷027c_标注.txt
python3 scripts/verify_annotation.py data/chapter_numbered/卷027d_五行志第七下之上.txt kg/entities/标注/卷027d_标注.txt
python3 scripts/verify_annotation.py data/chapter_numbered/卷027e_五行志第七下之下.txt kg/entities/标注/卷027e_标注.txt
```

## 五行志标注口径（承 M3 口径，规范 v2 派生）

- 五行德运与理论词（金木水火土／阴阳／咎征／彝伦／庶征／五事／皇极／三统／五纪）→ `〖_〗`
- 卦名与乐律名（乾坤坎离巽兑震剥鼎恒奥等已成词者）→ `〖^〗`
- 灾异类别名（服妖／龟孽／鸡祸／青眚／草妖／蠃虫之孽／日食／星孛／地震／山崩／大水／亡冰）→ `〖!〗`
- 神祇（太一／后土／上帝／五帝／西王母／鬼神／百神）→ `〖?〗`
- 传说帝王（虙羲／神农／黄帝／尧／舜／禹／契／鲧／汤／文武／周公／伊尹）→ `〖@〗`，受祭场景亦 `〖@〗`
- 虫豸草木禽兽（螟螣／蝗／蝝／蜮／雉／鼷鼠／牛／羊／豕／龙蛇／桑穀／李梅）→ `〖+〗`
- 兵器车驾器物（斧钺／旄／鼎／彝器／玺／印绶／圭璧／楛矢）→ `〖•〗`
- 春秋君名单字与省称一律按规则15强制消歧：`〖@桓公|鲁桓公〗`、`〖@齐桓|齐桓公〗`、`〖@宣|鲁宣公〗`
- 讹字照录并给规范名：刘韵→刘歆、字公→鲁定公、促舒→董仲舒
- 志书特有 BUG：`公 ˂ ˃ 侯` 类佚字段（如卷027d [1]/[4]/[5]）照录，不标

## 说明

- 未执行任何 `git commit` / `git push`。
- 每篇落盘后立即跑校验，全部一次通过；完整性（去标记后与底本逐字全等）零差异。
