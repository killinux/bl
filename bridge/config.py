import os

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8080")
API_KEY = os.environ.get("BLENDER_RELAY_API_KEY", "dev-key-change-me")
BLENDER_HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
BLENDER_PORT = int(os.environ.get("BLENDER_PORT", "9876"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
