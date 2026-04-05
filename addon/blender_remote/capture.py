"""Screenshot and console log capture utilities."""

import subprocess
import tempfile
import base64
import os
import sys
import collections
import platform

_log_buffer = collections.deque(maxlen=1000)
_original_stdout = None
_original_stderr = None


class _LogCapture:
    def __init__(self, original):
        self._original = original

    def write(self, text):
        if text.strip():
            _log_buffer.append(text)
        self._original.write(text)

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def install():
    """Install log capture on stdout/stderr."""
    global _original_stdout, _original_stderr
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    sys.stdout = _LogCapture(_original_stdout)
    sys.stderr = _LogCapture(_original_stderr)


def get_logs(n: int = 100) -> list[str]:
    """Return the last n log lines."""
    return list(_log_buffer)[-n:]


def capture_screenshot() -> str:
    """Capture a screenshot and return as base64 PNG."""
    path = os.path.join(tempfile.gettempdir(), "blender_screenshot.png")

    if platform.system() == "Darwin":
        # macOS: use screencapture (captures the focused window with -x for no sound)
        try:
            subprocess.run(["screencapture", "-x", path], check=True, timeout=5)
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # fall through to bpy method

    # Fallback: use Blender's built-in screenshot (must be called from main thread)
    return _screenshot_bpy(path)


def _screenshot_bpy(path: str) -> str:
    """Capture screenshot using Blender's API. Must run on main thread."""
    import bpy
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            # Blender 3.6 uses context override dict, 4.x uses temp_override
            if hasattr(bpy.context, "temp_override"):
                with bpy.context.temp_override(window=window, area=area):
                    bpy.ops.screen.screenshot(filepath=path, full=True)
            else:
                override = bpy.context.copy()
                override["window"] = window
                override["area"] = area
                bpy.ops.screen.screenshot(override, filepath=path, full=True)
            break
        break
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
