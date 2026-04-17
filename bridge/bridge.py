"""
Mac Bridge Agent - polls the relay server and dispatches tasks to the Blender addon.
Communicates with blender-mcp addon via TCP socket on localhost:9876.
Run this on the Mac alongside Blender.
"""

import os
import json
import time
import socket
import logging
import requests

from config import RELAY_URL, API_KEY, BLENDER_HOST, BLENDER_PORT, POLL_INTERVAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bridge")

session = requests.Session()
session.headers["X-API-Key"] = API_KEY


def send_to_blender(command: dict, timeout: float = 120.0) -> dict:
    """Send a JSON command to blender-mcp addon via TCP socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((BLENDER_HOST, BLENDER_PORT))
        sock.sendall(json.dumps(command).encode("utf-8"))

        # Receive response (may come in chunks)
        chunks = []
        while True:
            try:
                data = sock.recv(65536)
                if not data:
                    break
                chunks.append(data)
                # Try to parse accumulated data as JSON
                try:
                    result = json.loads(b"".join(chunks).decode("utf-8"))
                    return result
                except json.JSONDecodeError:
                    continue  # Incomplete, wait for more
            except socket.timeout:
                break

        if chunks:
            return json.loads(b"".join(chunks).decode("utf-8"))
        return {"status": "error", "error": "No response from Blender"}
    finally:
        sock.close()


def poll_task() -> dict | None:
    """Poll the relay for a pending task."""
    try:
        resp = session.get(f"{RELAY_URL}/tasks/pending", timeout=10)
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error(f"Failed to poll relay: {e}")
        return None


def submit_result(task_id: str, result: dict):
    """Submit task result back to the relay."""
    try:
        resp = session.post(
            f"{RELAY_URL}/tasks/{task_id}/result",
            json=result,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to submit result for {task_id}: {e}")


def dispatch_screenshot() -> dict:
    """Request viewport screenshot from blender-mcp addon."""
    import tempfile
    import base64

    # blender-mcp requires a filepath param, saves screenshot to that file
    tmp_path = os.path.join(tempfile.gettempdir(), "blender_screenshot.png")
    result = send_to_blender({
        "type": "get_viewport_screenshot",
        "params": {"filepath": tmp_path}
    })
    if "error" in result:
        return {"status": "error", "error": result["error"]}

    # Read the saved file and return as base64
    if os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 0:
        with open(tmp_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        return {"status": "ok", "image": image_b64}
    else:
        return {"status": "error", "error": "Screenshot file not created"}


def dispatch_exec(code: str) -> dict:
    """Execute Python code via blender-mcp addon."""
    result = send_to_blender({"type": "execute_code", "params": {"code": code}})
    if "error" in result:
        return {"status": "error", "error": result.get("error", result.get("message", ""))}
    return {
        "status": "ok",
        "stdout": result.get("result", ""),
        "stderr": "",
    }


def dispatch_scene_info() -> dict:
    """Get scene info via blender-mcp addon."""
    result = send_to_blender({"type": "get_scene_info", "params": {}})
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", "result": result}


def dispatch_logs() -> dict:
    """Get logs - use execute_code to read recent print output."""
    # blender-mcp doesn't have a dedicated logs endpoint,
    # so we return a hint
    return {"status": "ok", "logs": ["(Use exec to check Blender state. blender-mcp addon does not capture console logs separately.)"]}


def dispatch_push_file(task: dict) -> dict:
    """Download file from relay and save locally."""
    filename = task["payload"]["filename"]
    dest_path = task["payload"].get("dest_path", os.path.expanduser(f"~/blender_plugins/{filename}"))
    dest_path = os.path.expanduser(dest_path)

    resp = session.get(f"{RELAY_URL}/files/{filename}", timeout=30)
    resp.raise_for_status()

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(resp.content)

    return {"status": "ok", "path": dest_path, "size": len(resp.content)}


def handle_task(task: dict):
    """Dispatch a task to the appropriate handler."""
    task_type = task["type"]
    task_id = task["id"]
    log.info(f"Handling task {task_id}: {task_type}")

    try:
        if task_type == "screenshot":
            result = dispatch_screenshot()
        elif task_type == "exec":
            code = task["payload"].get("code", "")
            result = dispatch_exec(code)
        elif task_type == "logs":
            result = dispatch_logs()
        elif task_type == "scene_info":
            result = dispatch_scene_info()
        elif task_type == "push_file":
            result = dispatch_push_file(task)
        else:
            result = {"status": "error", "error": f"Unknown task type: {task_type}"}
    except ConnectionRefusedError:
        result = {"status": "error", "error": "Blender addon not reachable (is Blender running with blender-mcp addon started?)"}
    except socket.timeout:
        result = {"status": "error", "error": "Blender addon timed out"}
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    submit_result(task_id, result)
    log.info(f"Task {task_id} completed: {result.get('status', 'unknown')}")


def main():
    log.info(f"Bridge starting - relay={RELAY_URL} blender={BLENDER_HOST}:{BLENDER_PORT}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")

    while True:
        task = poll_task()
        if task:
            handle_task(task)
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
