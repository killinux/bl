---
description: Connect to remote Blender and verify the connection is working
---

Check if the Blender remote bridge is connected and working. Do the following steps:

1. Check if the Relay server is running:
```bash
sh $PROJECT_ROOT/aws_server.sh status
```

2. If not running, start it:
```bash
sh $PROJECT_ROOT/aws_server.sh start
```

3. Test the connection by executing a simple command in Blender:
```bash
cd $PROJECT_ROOT/cli
BLENDER_RELAY_API_KEY=mysecretkey python cli.py exec "print('Connection OK:', bpy.app.version_string)"
```

4. Report the result to the user. If it fails, remind them to:
   - Start Blender on Mac with blender-mcp addon (N panel → BlenderMCP → Start MCP Server)
   - Run the bridge on Mac: `cd ~/bl && sh mac.sh`
