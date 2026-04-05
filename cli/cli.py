#!/usr/bin/env python3
"""
CLI tool for Claude to interact with remote Blender.
Usage:
    python cli.py screenshot
    python cli.py exec "bpy.data.objects.keys()"
    python cli.py logs
    python cli.py push file.py --dest ~/addons/file.py
"""

import os
import sys
import time
import json
import base64
import argparse

import requests

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8080")
API_KEY = os.environ.get("BLENDER_RELAY_API_KEY", "dev-key-change-me")

session = requests.Session()
session.headers["X-API-Key"] = API_KEY


def create_task(task_type: str, payload: dict) -> str:
    resp = session.post(
        f"{RELAY_URL}/tasks",
        json={"type": task_type, "payload": payload},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_for_result(task_id: str, timeout: int = 30) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        wait_time = min(10, int(deadline - time.time()))
        resp = session.get(
            f"{RELAY_URL}/tasks/{task_id}/result",
            params={"wait": wait_time},
        )
        if resp.status_code == 200:
            return resp.json()
        # 204 = not ready yet
    print(f"Error: task {task_id} timed out after {timeout}s", file=sys.stderr)
    sys.exit(1)


def cmd_screenshot(args):
    task_id = create_task("screenshot", {})
    print(f"Waiting for screenshot (task {task_id})...")
    data = wait_for_result(task_id, timeout=15)

    result = data.get("result", {})
    if result.get("status") == "ok" and "image" in result:
        img_bytes = base64.b64decode(result["image"])
        path = f"/tmp/blender_screenshot_{int(time.time())}.png"
        with open(path, "wb") as f:
            f.write(img_bytes)
        print(f"Screenshot saved: {path} ({len(img_bytes)} bytes)")
    else:
        error = result.get("error", data.get("result", "Unknown error"))
        print(f"Error: {error}", file=sys.stderr)


def cmd_exec(args):
    code = args.code
    # If code is a file path, read it
    if os.path.isfile(code):
        with open(code) as f:
            code = f.read()

    task_id = create_task("exec", {"code": code})
    print(f"Executing code (task {task_id})...")
    data = wait_for_result(task_id, timeout=30)

    result = data.get("result", {})
    if result.get("stdout"):
        print(result["stdout"])
    if result.get("stderr"):
        print(result["stderr"], file=sys.stderr)
    if result.get("status") == "error":
        print(f"Error:\n{result.get('error', '')}", file=sys.stderr)
    if "result" in result:
        print(f"Return: {result['result']}")


def cmd_logs(args):
    task_id = create_task("logs", {})
    data = wait_for_result(task_id, timeout=10)

    result = data.get("result", {})
    if result.get("status") == "ok":
        for line in result.get("logs", []):
            print(line)
    else:
        print(f"Error: {result}", file=sys.stderr)


def cmd_push(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(filepath)
    dest = args.dest or f"~/blender_plugins/{filename}"

    # Upload file to relay
    with open(filepath, "rb") as f:
        resp = session.post(
            f"{RELAY_URL}/files/{filename}",
            data=f.read(),
            headers={**session.headers, "Content-Type": "application/octet-stream"},
        )
    resp.raise_for_status()
    print(f"Uploaded {filename} to relay")

    # Create task for bridge to download it
    task_id = create_task("push_file", {"filename": filename, "dest_path": dest})
    data = wait_for_result(task_id, timeout=15)

    result = data.get("result", {})
    if result.get("status") == "ok":
        print(f"File delivered to Mac: {result.get('path')}")
    else:
        print(f"Error: {result}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Blender Remote CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("screenshot", help="Capture Blender screenshot")

    p_exec = sub.add_parser("exec", help="Execute Python code in Blender")
    p_exec.add_argument("code", help="Python code string or path to .py file")

    sub.add_parser("logs", help="Get Blender console logs")

    p_push = sub.add_parser("push", help="Push a file to the Mac")
    p_push.add_argument("file", help="Local file to push")
    p_push.add_argument("--dest", help="Destination path on Mac")

    args = parser.parse_args()

    commands = {
        "screenshot": cmd_screenshot,
        "exec": cmd_exec,
        "logs": cmd_logs,
        "push": cmd_push,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
