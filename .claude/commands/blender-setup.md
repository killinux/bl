---
description: First-time setup guide for Blender Remote Bridge
---

Walk the user through the complete first-time setup of the Blender Remote Bridge system.

## Step 1: AWS Setup (this machine)

1. Create conda environment:
```bash
conda create -n blender-relay python=3.12 -y
conda activate blender-relay
pip install fastapi uvicorn pydantic requests mcp --root-user-action=ignore
```

2. Start the Relay server:
```bash
sh $PROJECT_ROOT/aws_server.sh start
```

3. Verify:
```bash
curl http://localhost:8080/health
```

4. Remind the user to open AWS security group port 8080.

## Step 2: Mac Setup (tell the user to do this)

Tell the user to run these commands on their Mac:

```bash
# Clone the repo
git clone git@github.com:killinux/bl.git
cd bl

# Install blender-mcp addon in Blender:
# 1. Download addon.py from github.com/ahujasid/blender-mcp
# 2. Blender → Edit → Preferences → Add-ons → Install → select addon.py → Enable
# 3. In 3D viewport press N → BlenderMCP panel → Start MCP Server

# Install dependencies and start Bridge
pip install requests
RELAY_URL=http://AWS_PUBLIC_IP:8080 BLENDER_RELAY_API_KEY=mysecretkey python bridge/bridge.py
```

Replace AWS_PUBLIC_IP with the actual public IP of this AWS instance.

## Step 3: Verify Connection

After the user confirms Mac is ready, test:
```bash
cd $PROJECT_ROOT/cli
BLENDER_RELAY_API_KEY=mysecretkey python cli.py exec "print('Connected! Blender', bpy.app.version_string)"
```

If successful, tell the user they can now use:
- `/blender-connect` — check connection status
- `/blender-screenshot` — capture Blender viewport
- `/blender-exec <code>` — run Python in Blender
- `/blender-push <file>` — send file to Mac
