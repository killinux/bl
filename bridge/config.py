import os

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8080")
API_KEY = os.environ.get("BLENDER_RELAY_API_KEY", "dev-key-change-me")
BLENDER_ADDON_URL = os.environ.get("BLENDER_ADDON_URL", "http://127.0.0.1:9876")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
