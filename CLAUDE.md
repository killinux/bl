# Blender Remote Bridge

本项目通过 Relay 中转实现 AWS 上的 Claude Code 远程控制公司内网 Mac 上的 Blender。

## 连接 Blender

确保 AWS Relay 和 Mac Bridge 已启动（见下方"启动"），然后直接使用 CLI：

```bash
cd /opt/mywork/mytest/bl
BLENDER_RELAY_API_KEY=mysecretkey python cli/cli.py exec "print(bpy.data.objects.keys())"
BLENDER_RELAY_API_KEY=mysecretkey python cli/cli.py screenshot
BLENDER_RELAY_API_KEY=mysecretkey python cli/cli.py logs
```

## 启动

AWS 端：
```bash
conda activate blender-relay
cd /opt/mywork/mytest/bl
sh aws_server.sh start
```

Mac 端：
Blender 里 N 面板 → BlenderMCP → Start MCP Server，然后终端跑
```bash
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh
conda activate blender
sh mac.sh
```

## 架构

```
Claude CLI → Relay Server (:8080) ← Bridge (Mac 轮询) → blender-mcp 插件 (:9876 TCP Socket)
```

## 关键文件

- `relay/server.py` — FastAPI 中继服务器
- `bridge/bridge.py` — Mac 端轮询代理，TCP Socket 连接 blender-mcp
- `cli/cli.py` — CLI 工具（exec/screenshot/logs/push）
- `mcp/blender_mcp_server.py` — MCP Server 封装（自然语言控制）
- `aws_server.sh` — AWS 启动脚本（start/stop/status/log）
- `mac.sh` — Mac 启动脚本

## 代码修改流程

- **所有代码修改都在 AWS 端进行**，修改完 commit + push
- Mac 端通过 `git pull` 同步，**不要直接在 Mac 上改代码**
- 仓库路径：
  - bl: AWS `/opt/mywork/mytest/bl/` ↔ Mac `/Users/bytedance/work/mytest/bl/`
  - 插件: AWS `/opt/mywork/mytest/Convert_to_MMD_claude/` ↔ Mac `/Users/bytedance/Library/Application Support/Blender/3.6/scripts/addons/Convert_to_MMD_claude/`

## XPS→PMX 转换注意事项

- **不要轻易切权重**。遇到肩/肘/手臂姿态偏差时，优先检查 rest pose 对齐（`align_arms_to_reference`、`fix_forearm_bend`），而不是直接修改顶点权重。直接改权重容易引入新问题且难以回退。

### 姿态偏差排查顺序

遇到转换后模型与目标姿态不一致时，严格按以下顺序排查，**不要跳步**：

1. **方向偏差？** → 查 rest pose bone direction（`bone.matrix_local` 的 Y/Z 轴对比），用 `align_arms_to_reference` / `align_fingers_to_reference` 对齐
2. **旋转行为不对？**（如能大幅自由旋转、不受约束）→ 查 `pose_bone.lock_rotation`、`constraints`，对比目标模型的约束设置
3. **控制范围不对？**（旋转时影响的皮肤区域和目标不同）→ 查 vertex group 顶点数对比，看是否挂反（如腕.L ↔ 腕捩.L 交换问题）或缺失
4. **以上都排除后才考虑权重问题** → 且优先用数学方法（梯度分配 `split_twist_weights`），不手动调整单个顶点权重

注意：`Bone.roll` 只能在 Edit Mode 下访问（`EditBone.roll`），Object/Pose Mode 下用 `bone.matrix_local.to_3x3().col[2]`（Z 轴）代替。

## 通用行为准则 (Karpathy Guidelines)

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

Source: https://github.com/forrestchang/andrej-karpathy-skills
