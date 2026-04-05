bl_info = {
    "name": "Remote Control",
    "author": "Blender Remote Bridge",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "category": "Development",
    "description": "Local HTTP server for remote script execution and screenshot capture",
}


def register():
    from . import executor, server, capture
    capture.install()
    executor.start()
    server.start(port=9876)
    print("[Remote Control] Addon registered - server on localhost:9876")


def unregister():
    from . import executor, server
    server.stop()
    executor.stop()
    print("[Remote Control] Addon unregistered")
