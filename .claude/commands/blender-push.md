---
description: Push a file to the Mac running Blender
---

Push a local file to the Mac where Blender is running.

$ARGUMENTS

Parse the arguments to get the file path and optional destination:
- First argument: local file path
- Optional --dest flag: destination path on Mac (default: ~/blender_plugins/<filename>)

```bash
cd $PROJECT_ROOT/cli
BLENDER_RELAY_API_KEY=mysecretkey python cli.py push $ARGUMENTS
```
