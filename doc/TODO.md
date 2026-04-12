# TODO

## 待做

- [ ] **补全脚趾细分骨** — XPS 源模型没有脚趾细分骨（lBigToe/lSmallToe 等 20 根），目标 PMX 有。需要在 `complete_missing_bones` 中新增创建逻辑，在 `つま先.L/R` 下创建子骨。

## 已完成

- [x] **足先EX is_tip 修复** — `leg_operator.py` 不再对 足先EX 设 is_tip=True，和目标 PMX 一致。(commit 9dfd629)
- [x] **下半身 layer 修复** — `bone_operator.py` rename 时自动把 unused 骨从 layer 1 拉回 layer 0。(commit 9dfd629)
- [x] **手臂/手指对齐** — 测试流程加入 Step 0.5: align_arms_to_reference + align_fingers_to_reference + fix_forearm_bend。
- [x] **共有骨骼属性全对齐** — 160 根共有骨骼的 hide/use_deform/lock/name_j/is_tip/transform_order/layers 全部与目标一致，0 差异。
