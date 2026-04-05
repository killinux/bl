#!/usr/bin/env python3
"""
MCP Server for Blender Remote Bridge.

Wraps the Relay API as MCP tools so Claude Code can natively call
blender_screenshot, blender_exec, blender_logs, blender_push.
"""

import os
import sys
import time
import base64
import json

import requests
from mcp.server.fastmcp import FastMCP

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8080")
API_KEY = os.environ.get("BLENDER_RELAY_API_KEY", "dev-key-change-me")

session = requests.Session()
session.headers["X-API-Key"] = API_KEY

mcp = FastMCP("blender-remote")


def _create_task(task_type: str, payload: dict) -> str:
    resp = session.post(f"{RELAY_URL}/tasks", json={"type": task_type, "payload": payload})
    resp.raise_for_status()
    return resp.json()["id"]


def _wait_for_result(task_id: str, timeout: int = 30) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        wait_time = min(10, int(deadline - time.time()))
        resp = session.get(
            f"{RELAY_URL}/tasks/{task_id}/result",
            params={"wait": wait_time},
        )
        if resp.status_code == 200:
            return resp.json().get("result", {})
    return {"status": "error", "error": f"Task {task_id} timed out after {timeout}s"}


@mcp.tool()
def blender_screenshot() -> str:
    """Capture a screenshot of the Blender viewport. Returns the file path of the saved PNG."""
    task_id = _create_task("screenshot", {})
    result = _wait_for_result(task_id, timeout=15)

    if result.get("status") == "ok" and "image" in result:
        img_bytes = base64.b64decode(result["image"])
        path = f"/tmp/blender_screenshot_{int(time.time())}.png"
        with open(path, "wb") as f:
            f.write(img_bytes)
        return f"Screenshot saved: {path} ({len(img_bytes)} bytes)"
    else:
        return f"Error: {result.get('error', json.dumps(result))}"


@mcp.tool()
def blender_exec(code: str) -> str:
    """Execute Python code inside Blender. The code has access to bpy and the full Blender Python API.
    If `code` is a path to an existing .py file, its contents will be read and executed.
    To return structured data, set __result__ in your code."""
    if os.path.isfile(code):
        with open(code) as f:
            code = f.read()

    task_id = _create_task("exec", {"code": code})
    result = _wait_for_result(task_id, timeout=30)

    parts = []
    if result.get("stdout"):
        parts.append(result["stdout"])
    if result.get("stderr"):
        parts.append(f"[stderr] {result['stderr']}")
    if result.get("status") == "error":
        parts.append(f"[error] {result.get('error', '')}")
    if "result" in result:
        parts.append(f"[return] {result['result']}")
    return "\n".join(parts) if parts else "OK (no output)"


@mcp.tool()
def blender_logs(n: int = 100) -> str:
    """Get recent Blender console logs. Returns the last n lines of stdout/stderr output."""
    task_id = _create_task("logs", {})
    result = _wait_for_result(task_id, timeout=10)

    if result.get("status") == "ok":
        logs = result.get("logs", [])
        return "\n".join(logs) if logs else "(no logs)"
    else:
        return f"Error: {result.get('error', json.dumps(result))}"


@mcp.tool()
def blender_push(file_path: str, dest_path: str = "") -> str:
    """Push a local file to the Mac running Blender.
    file_path: local file to send
    dest_path: destination path on Mac (default: ~/blender_plugins/<filename>)"""
    if not os.path.isfile(file_path):
        return f"Error: file not found: {file_path}"

    filename = os.path.basename(file_path)
    if not dest_path:
        dest_path = f"~/blender_plugins/{filename}"

    with open(file_path, "rb") as f:
        resp = session.post(
            f"{RELAY_URL}/files/{filename}",
            data=f.read(),
            headers={**session.headers, "Content-Type": "application/octet-stream"},
        )
    resp.raise_for_status()

    task_id = _create_task("push_file", {"filename": filename, "dest_path": dest_path})
    result = _wait_for_result(task_id, timeout=15)

    if result.get("status") == "ok":
        return f"File delivered to Mac: {result.get('path')} ({result.get('size')} bytes)"
    else:
        return f"Error: {result.get('error', json.dumps(result))}"


@mcp.tool()
def blender_scene_info() -> str:
    """Get information about all objects in the current Blender scene.
    Returns object names, types, locations, and materials."""
    code = """
import bpy
import json
scene = bpy.context.scene
objects = []
for obj in scene.objects:
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "visible": obj.visible_get(),
    }
    if obj.data and hasattr(obj.data, "materials"):
        info["materials"] = [m.name for m in obj.data.materials if m]
    if obj.type == "MESH":
        info["vertices"] = len(obj.data.vertices)
        info["faces"] = len(obj.data.polygons)
    objects.append(info)

result = {
    "scene": scene.name,
    "object_count": len(objects),
    "objects": objects,
    "active_camera": scene.camera.name if scene.camera else None,
    "render_engine": scene.render.engine,
    "resolution": f"{scene.render.resolution_x}x{scene.render.resolution_y}",
}
__result__ = json.dumps(result, indent=2, ensure_ascii=False)
"""
    return blender_exec(code)


@mcp.tool()
def blender_object_info(object_name: str) -> str:
    """Get detailed information about a specific Blender object.
    Returns location, rotation, scale, materials, mesh data, modifiers, etc."""
    code = f"""
import bpy
import json
obj = bpy.data.objects.get("{object_name}")
if not obj:
    __result__ = json.dumps({{"error": "Object '{object_name}' not found"}})
else:
    info = {{
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "visible": obj.visible_get(),
        "parent": obj.parent.name if obj.parent else None,
        "children": [c.name for c in obj.children],
        "modifiers": [{{
            "name": m.name,
            "type": m.type,
        }} for m in obj.modifiers],
    }}
    if obj.data and hasattr(obj.data, "materials"):
        info["materials"] = []
        for m in obj.data.materials:
            if m:
                mat_info = {{"name": m.name, "use_nodes": m.use_nodes}}
                if m.use_nodes:
                    bsdf = m.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        bc = bsdf.inputs["Base Color"].default_value
                        mat_info["base_color"] = [round(bc[i], 3) for i in range(4)]
                info["materials"].append(mat_info)
    if obj.type == "MESH":
        info["vertices"] = len(obj.data.vertices)
        info["edges"] = len(obj.data.edges)
        info["faces"] = len(obj.data.polygons)
        bb = [list(v) for v in obj.bound_box]
        info["bounding_box"] = bb
    __result__ = json.dumps(info, indent=2, ensure_ascii=False)
"""
    return blender_exec(code)


if __name__ == "__main__":
    mcp.run(transport="stdio")
