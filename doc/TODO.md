# TODO

## 待做

- [ ] **补全脚趾细分骨** — XPS 源模型没有脚趾细分骨（lBigToe/lSmallToe 等 20 根），目标 PMX 有。需要在 `complete_missing_bones` 中新增创建逻辑，在 `つま先.L/R` 下创建子骨。

## 已知差异（非 bug，不修）

- 位置/长度/方向差异 — 两个模型体型不同导致，非 pipeline bug
- 腕捩 fixed_axis Z 轴差 ~0.003 — 手臂对齐浮点误差，不影响效果
- name_e 未映射的骨骼保持为空 — hair/unused 等非标准骨无对应英文名

## 已完成

- [x] **name_e 英文名设置** — `preset_operator.py` step 8 加入标准 MMD 骨骼英文名映射。(commit ff606f7)
- [x] **足IK親 parent 修复** — `ik_operator.py` 足IK親.L/R parent 从 None 改为 全ての親。(commit ff606f7)
- [x] **足先EX is_tip 修复** — `leg_operator.py` 不再对 足先EX 设 is_tip=True，和目标 PMX 一致。(commit 9dfd629)
- [x] **下半身 layer 修复** — `bone_operator.py` rename 时自动把 unused 骨从 layer 1 拉回 layer 0。(commit 9dfd629)
- [x] **手臂/手指对齐** — 测试流程加入 Step 0.5: align_arms_to_reference + align_fingers_to_reference + fix_forearm_bend。
- [x] **共有骨骼属性全对齐** — 160 根共有骨骼的 hide/use_deform/lock/name_j/is_tip/transform_order/layers 全部与目标一致，0 差异。
