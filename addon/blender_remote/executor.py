"""
Main-thread execution queue for Blender.

bpy operations must run on the main thread. This module bridges background
HTTP server threads to the main thread via a queue + bpy.app.timers.
"""

import queue
import threading
import traceback
import io
import sys

import bpy

_queue = queue.Queue()


def execute_on_main_thread(code: str, timeout: float = 30.0) -> dict:
    """Called from HTTP server thread. Blocks until main thread executes the code."""
    result_event = threading.Event()
    result_container = {}

    def _run():
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        try:
            sys.stdout = captured_out
            sys.stderr = captured_err
            namespace = {"bpy": bpy, "__builtins__": __builtins__}
            exec(code, namespace)
            result_container["status"] = "ok"
            result_container["stdout"] = captured_out.getvalue()
            result_container["stderr"] = captured_err.getvalue()
            # Allow scripts to set __result__ for structured return
            if "__result__" in namespace:
                result_container["result"] = namespace["__result__"]
        except Exception:
            result_container["status"] = "error"
            result_container["error"] = traceback.format_exc()
            result_container["stdout"] = captured_out.getvalue()
            result_container["stderr"] = captured_err.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            result_event.set()

    _queue.put(_run)
    result_event.wait(timeout=timeout)

    if not result_event.is_set():
        return {"status": "error", "error": f"Execution timed out ({timeout}s)"}
    return result_container


def _timer_callback():
    """Runs on Blender's main thread, drains the queue."""
    while not _queue.empty():
        try:
            func = _queue.get_nowait()
            func()
        except queue.Empty:
            break
    return 0.1  # re-run every 100ms


def start():
    bpy.app.timers.register(_timer_callback, persistent=True)


def stop():
    if bpy.app.timers.is_registered(_timer_callback):
        bpy.app.timers.unregister(_timer_callback)
