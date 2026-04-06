# Blender Remote Bridge

本项目通过 Relay 中转实现 AWS 上的 Claude Code 远程控制公司内网 Mac 上的 Blender。

## 连接 Blender

确保 AWS Relay 和 Mac Bridge 已启动（见下方"启动"），然后直接使用 CLI：

```bash
cd /opt/workspace/bl/cli
BLENDER_RELAY_API_KEY=mysecretkey python cli.py exec "print(bpy.data.objects.keys())"
BLENDER_RELAY_API_KEY=mysecretkey python cli.py screenshot
BLENDER_RELAY_API_KEY=mysecretkey python cli.py logs
```

## 启动

AWS 端：
```bash
conda activate blender-relay
cd /opt/workspace/bl
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
