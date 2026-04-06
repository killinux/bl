#!/bin/sh
BLENDER_RELAY_API_KEY=mysecretkey python cli/cli.py exec "print(bpy.data.objects.keys())"
