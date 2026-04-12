# XPS 骨骼完整去向追踪

XPS 源模型 (Inase) 共 **109 根骨骼**，按前缀分类如下。本文档追踪每根骨的转换去向和当前状态。

## 统计总览

| 前缀 | 数量 | 去向 |
|------|------|------|
| `arm*` | 38 | 全部 rename → MMD 标准骨（肩/腕/ひじ/手首/手指） |
| `head*` | 38 | 2 根 rename（首/頭），6 根 hair 保留，2 根 eyeball rename（目），28 根面部骨清理删除 |
| `unused*` | 13 | 1 根 rename 下半身，8 根 rename twist，4 根 PRESERVE 保留 |
| `leg*` | 8 | 全部 rename → MMD 标准骨（足/ひざ/足首/つま先） |
| `boob*` | 4 | 2 根 rename（乳奶.L/R），2 根保留原名 |
| `spine*` | 3 | 全部 rename → MMD 标准骨（上半身/上半身1/上半身2） |
| `root*` | 2 | 全部 rename → MMD 标准骨（全ての親/センター） |
| `hair*` | 3 | 全部保留原名（hidden deform） |
| **合计** | **109** | **rename 68 + twist 8 + 面部删除 28 + 保留 5** |

## arm* (38 根) → 全部 rename

| XPS 名称 | 转换后 | 处理阶段 |
|----------|--------|----------|
| `arm left/right shoulder 1` | 肩.L/R | Step 1 rename |
| `arm left/right shoulder 2` | 腕.L/R | Step 1 rename |
| `arm left/right elbow` | ひじ.L/R | Step 1 rename |
| `arm left/right wrist` | 手首.L/R | Step 1 rename |
| `arm left/right finger 1a~1c` | 親指０~２.L/R | Step 1 rename |
| `arm left/right finger 2a~2c` | 人指１~３.L/R | Step 1 rename |
| `arm left/right finger 3a~3c` | 中指１~３.L/R | Step 1 rename |
| `arm left/right finger 4a~4c` | 薬指１~３.L/R | Step 1 rename |
| `arm left/right finger 5a~5c` | 小指１~３.L/R | Step 1 rename |

## head* (38 根)

### rename (4 根)

| XPS 名称 | 转换后 | 处理阶段 |
|----------|--------|----------|
| `head neck lower` | 首 | Step 1 rename |
| `head neck upper` | 頭 | Step 1 rename |
| `head eyeball left` | 目.L | Step 1 rename |
| `head eyeball right` | 目.R | Step 1 rename |

### 保留原名 (6 根 hair)

| XPS 名称 | parent | 当前状态 |
|----------|--------|----------|
| `head hair front right 1~4` | 頭 | visible, deform |
| `head hair left 1~2` | 頭 | visible, deform |

### 面部清理删除 (28 根) → 权重合并到頭

Step 4.5 cleanup_face_bones 删除，4839 个顶点权重合并到頭骨。

包含：cheek (2), eyebrow (8), eyelid (4), jaw (1), lip (6), mouth corner (2), nose nostril (2), tongue (3)

## unused* (13 根)

### rename 为标准 MMD 骨 (1 根)

| XPS 名称 | 顶点 | 转换后 | 处理阶段 |
|----------|------|--------|----------|
| `unused bip001 pelvis` | 6892 | **下半身** | Step 1 rename + layer 0 修复 |

### rename 为 twist 系列 (8 根)

| XPS 名称 | parent | 顶点 | 转换后 | 处理阶段 |
|----------|--------|------|--------|----------|
| `unused bip001 xtra07pp` | arm left shoulder 2 | 679 | **腕捩.L** | Step 2.1 |
| `unused bip001 xtra07` | arm right shoulder 2 | 485 | **腕捩.R** | Step 2.1 |
| `unused bip001 l foretwist1` | l foretwist | 370 | **手捩.L** | Step 2.1 |
| `unused bip001 l foretwist` | arm left elbow | 324 | **手捩1.L** | Step 2.1 |
| `unused bip001 r foretwist1` | r foretwist | 1189 | **手捩.R** | Step 2.1 |
| `unused bip001 r foretwist` | arm right elbow | 1144 | **手捩1.R** | Step 2.1 |
| `unused muscle_elbow_l` | arm left shoulder 2 | 36 | **手捩2.L** | Step 2.1 |
| `unused muscle_elbow_r` | arm right shoulder 2 | 35 | **手捩2.R** | Step 2.1 |

### 保留为辅助 deform 骨 (4 根) — PRESERVE

按 CLAUDE.md "不要轻易切权重" 原则，保留 XPS 原始权重，通过父链继承旋转。

| XPS 名称 | parent | 顶点 | 当前状态 | 说明 |
|----------|--------|------|----------|------|
| `unused bip001 xtra04` | leg left thigh (足.L) | 853 | hidden, deform | 胯部/大腿内侧辅助 |
| `unused bip001 xtra02` | leg right thigh (足.R) | 850 | hidden, deform | 同上, 对称侧 |
| `unused bip001 xtra08` | pelvis (下半身) | 1082 | hidden, deform | 臀部/大腿外侧辅助 |
| `unused bip001 xtra08opp` | pelvis (下半身) | 1228 | hidden, deform | 同上, 对称侧 |

足D 权重占比 (2.7%) 低于目标 (15.1%) 是 mesh 密度差异 (5 万 vs 17 万顶点)，不是 bug。

历史：PRESERVE 保留(初版) → 整体合并到足D(562076c, 足D 权重恢复但胯部变形) → 按顶点拆分(9687975, 修复变形但违反不切权重原则) → **恢复 PRESERVE(2c64f80, 最终方案)**。

## leg* (8 根) → 全部 rename

| XPS 名称 | 转换后 |
|----------|--------|
| `leg left/right thigh` | 足.L/R |
| `leg left/right knee` | ひざ.L/R |
| `leg left/right ankle` | 足首.L/R |
| `leg left/right toes` | つま先.L/R |

## boob* (4 根)

| XPS 名称 | 转换后 | 状态 |
|----------|--------|------|
| `boob left 1` | **乳奶.L** (rename) | Step 1 |
| `boob right 1` | **乳奶.R** (rename) | Step 1 |
| `boob left 2` | 保留原名 | visible, deform, parent=乳奶.L |
| `boob right 2` | 保留原名 | visible, deform, parent=乳奶.R |

## spine* (3 根) → 全部 rename

| XPS 名称 | 转换后 |
|----------|--------|
| `spine lower` | 上半身 |
| `spine middle` | 上半身1 |
| `spine upper` | 上半身2 |

## root* (2 根) → 全部 rename

| XPS 名称 | 转换后 |
|----------|--------|
| `root ground` | 全ての親 |
| `root hips` | センター |

## hair* (3 根) → 保留原名

| XPS 名称 | parent | 当前状态 |
|----------|--------|----------|
| `hair c` | 頭 | hidden, deform |
| `hair l` | 頭 | hidden, deform |
| `hair r` | 頭 | hidden, deform |

## 修改历史

- **2026-04-12 commit 2c64f80**: 恢复全部 4 根 xtra 骨为 PRESERVE（不切权重原则）
- **2026-04-12 commit 9687975**: xtra 改为 SPLIT 按顶点拆分（修复胯部变形但违反不切权重原则，已被 2c64f80 回退）
- **2026-04-12 commit 562076c**: xtra02/04 整体合并到足D（导致胯部变形，已回退）
- **2026-04-12 commit 9dfd629**: 下半身 layer 修复（从 layer 1 拉回 layer 0）
- **2026-04-12 初版文档**: 建立全部 109 根骨的去向追踪

## 当前状态：13 根 unused 骨 — 9 根 rename + 4 根 PRESERVE 保留
