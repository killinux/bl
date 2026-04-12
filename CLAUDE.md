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

Mac 端：Blender 里 N 面板 → BlenderMCP → Start MCP Server，然后终端跑 `sh mac.sh`。

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
- Convert-to-MMD-claude 插件路径：
  - AWS: `/opt/mywork/mytest/Convert-to-MMD-claude/`
  - Mac: `/Users/bytedance/Library/Application Support/Blender/3.6/scripts/addons/Convert_to_MMD_claude/`

## XPS→PMX 转换注意事项

- **不要轻易切权重**。遇到肩/肘/手臂姿态偏差时，优先检查 rest pose 对齐（`align_arms_to_reference`、`fix_forearm_bend`），而不是直接修改顶点权重。直接改权重容易引入新问题且难以回退。

### 姿态偏差排查顺序

遇到转换后模型与目标姿态不一致时，严格按以下顺序排查，**不要跳步**：

1. **方向偏差？** → 查 rest pose bone direction（`bone.matrix_local` 的 Y/Z 轴对比），用 `align_arms_to_reference` / `align_fingers_to_reference` 对齐
2. **旋转行为不对？**（如能大幅自由旋转、不受约束）→ 查 `pose_bone.lock_rotation`、`constraints`，对比目标模型的约束设置
3. **控制范围不对？**（旋转时影响的皮肤区域和目标不同）→ 查 vertex group 顶点数对比，看是否挂反（如腕.L ↔ 腕捩.L 交换问题）或缺失
4. **以上都排除后才考虑权重问题** → 且优先用数学方法（梯度分配 `split_twist_weights`），不手动调整单个顶点权重

注意：`Bone.roll` 只能在 Edit Mode 下访问（`EditBone.roll`），Object/Pose Mode 下用 `bone.matrix_local.to_3x3().col[2]`（Z 轴）代替。
