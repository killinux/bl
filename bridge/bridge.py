"""
Mac Bridge Agent - polls the relay server and dispatches tasks to the Blender addon.
Run this on the Mac alongside Blender.
"""

import os
import time
import logging
import requests

from config import RELAY_URL, API_KEY, BLENDER_ADDON_URL, POLL_INTERVAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bridge")

session = requests.Session()
session.headers["X-API-Key"] = API_KEY


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
    resp = requests.get(f"{BLENDER_ADDON_URL}/screenshot", timeout=15)
    resp.raise_for_status()
    return resp.json()


def dispatch_exec(code: str) -> dict:
    resp = requests.post(
        f"{BLENDER_ADDON_URL}/exec",
        json={"code": code},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def dispatch_logs() -> dict:
    resp = requests.get(f"{BLENDER_ADDON_URL}/logs", timeout=5)
    resp.raise_for_status()
    return resp.json()


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
        elif task_type == "push_file":
            result = dispatch_push_file(task)
        else:
            result = {"status": "error", "error": f"Unknown task type: {task_type}"}
    except requests.ConnectionError:
        result = {"status": "error", "error": "Blender addon not reachable (is Blender running with the addon enabled?)"}
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    submit_result(task_id, result)
    log.info(f"Task {task_id} completed: {result.get('status', 'unknown')}")


def main():
    log.info(f"Bridge starting - relay={RELAY_URL} blender={BLENDER_ADDON_URL}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")

    while True:
        task = poll_task()
        if task:
            handle_task(task)
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
