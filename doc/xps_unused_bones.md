# XPS Unused 骨骼去向追踪

XPS 源模型 (Inase) 共 109 根骨骼，其中 13 根以 `unused` 开头。本文档追踪每根 unused 骨的处理方式和当前状态。

## 已处理 (11/13)

### rename 为标准 MMD 骨 (1 根)

| XPS 名称 | parent | 顶点 | 转换后 | 处理阶段 |
|----------|--------|------|--------|----------|
| `unused bip001 pelvis` | root hips | 6892 | **下半身** | Step 1 rename_to_mmd |

### rename 为 twist 系列 (8 根)

| XPS 名称 | parent | 顶点 | 转换后 | 处理阶段 |
|----------|--------|------|--------|----------|
| `unused bip001 xtra07pp` | arm left shoulder 2 | 679 | **腕捩.L** | Step 2.1 complete_twist_bones |
| `unused bip001 xtra07` | arm right shoulder 2 | 485 | **腕捩.R** | Step 2.1 |
| `unused bip001 l foretwist1` | l foretwist | 370 | **手捩.L** | Step 2.1 |
| `unused bip001 l foretwist` | arm left elbow | 324 | **手捩1.L** | Step 2.1 |
| `unused bip001 r foretwist1` | r foretwist | 1189 | **手捩.R** | Step 2.1 |
| `unused bip001 r foretwist` | arm right elbow | 1144 | **手捩1.R** | Step 2.1 |
| `unused muscle_elbow_l` | arm left shoulder 2 | 36 | **手捩2.L** | Step 2.1 |
| `unused muscle_elbow_r` | arm right shoulder 2 | 35 | **手捩2.R** | Step 2.1 |

### 权重合并到足D (2 根) — commit 562076c

| XPS 名称 | parent | 顶点 | 转换后 | 处理阶段 |
|----------|--------|------|--------|----------|
| `unused bip001 xtra04` | leg left thigh | 853 | 权重 → **足.L** → **足D.L** | Step 5.1 merge + Step 5.2 D转移 |
| `unused bip001 xtra02` | leg right thigh | 850 | 权重 → **足.R** → **足D.R** | Step 5.1 merge + Step 5.2 D转移 |

之前这两根被 PRESERVE_HELPER_KEYWORDS 保留为 hidden deform 骨，导致足D权重占比只有 2.7%（目标 15.1%）。移除 PRESERVE 后权重正常合并到足D。

## 未处理 (2/13)

| XPS 名称 | parent | 顶点 | 当前状态 | 说明 |
|----------|--------|------|----------|------|
| `unused bip001 xtra08` | pelvis (下半身) | 1082 | 保留 hidden, deform=True | 臀部/大腿外侧辅助骨。跨臀部+大腿两个区域，已有 SPLIT_BONES 按顶点拆分逻辑但被 PRESERVE 挡住未执行 |
| `unused bip001 xtra08opp` | pelvis (下半身) | 1228 | 保留 hidden, deform=True | 同上，对称侧 |

### xtra08/xtra08opp 可能的处理方案

- **方案 A**: 从 PRESERVE 移除，让 SPLIT_BONES 生效，按顶点位置拆分到 下半身 / 足.L / 足.R
- **方案 B**: 保持现状（hidden deform 骨），权重通过父链 (下半身) 继承旋转
- **当前选择**: 方案 B（保持现状），因为权重量较小 (123/126w)，影响不大

## 非 unused 的未处理骨骼 (6 根)

这些不是 unused 开头，但也是 XPS 源独有、未 rename 的骨骼：

| XPS 名称 | parent | 当前状态 | 说明 |
|----------|--------|----------|------|
| `boob left 2` | 乳奶.L | visible, deform | 胸部第 2 节，保留 |
| `boob right 2` | 乳奶.R | visible, deform | 同上 |
| `hair c` | 頭 | hidden, deform | 头发中间骨，保留做物理用 |
| `hair l` | 頭 | hidden, deform | 头发左侧骨 |
| `hair r` | 頭 | hidden, deform | 头发右侧骨 |
| `head hair front right 1~4` | 頭 | visible, deform | 前发骨 (4 根) |
| `head hair left 1~2` | 頭 | visible, deform | 侧发骨 (2 根) |

## 修改历史

- **2026-04-12 commit 562076c**: xtra02/xtra04 从 PRESERVE 移除，权重合并到足D
- **2026-04-12 commit 9dfd629**: 下半身 layer 修复（从 layer 1 拉回 layer 0）
