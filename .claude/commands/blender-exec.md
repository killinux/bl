---
description: Execute Python code in Blender
---

Execute the provided Python code inside the remote Blender instance.

The code has full access to `bpy` and the Blender Python API.

$ARGUMENTS

Run:
```bash
cd $PROJECT_ROOT/cli
BLENDER_RELAY_API_KEY=mysecretkey python cli.py exec "$ARGUMENTS"
```

If the argument is a .py file path, the CLI will read and execute its contents.
If the argument is a code string, it will be executed directly.
