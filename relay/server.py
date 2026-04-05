import os
import time
import asyncio
from typing import Optional
from collections import OrderedDict
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response

from models import Task, TaskCreate, TaskStatus

API_KEY = os.environ.get("BLENDER_RELAY_API_KEY", "dev-key-change-me")
TASK_TTL = 300  # 5 minutes
FILE_TTL = 600  # 10 minutes
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

# In-memory stores
tasks: OrderedDict[str, Task] = OrderedDict()
files: dict[str, tuple[bytes, float]] = {}


def cleanup():
    now = time.time()
    expired = [tid for tid, t in tasks.items() if now - t.created_at > TASK_TTL]
    for tid in expired:
        del tasks[tid]
    expired_files = [f for f, (_, ts) in files.items() if now - ts > FILE_TTL]
    for f in expired_files:
        del files[f]


async def periodic_cleanup():
    while True:
        await asyncio.sleep(30)
        cleanup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(title="Blender Relay", lifespan=lifespan)


def verify_key(x_api_key: str = Header(alias="X-API-Key", default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/tasks", dependencies=[Depends(verify_key)])
def create_task(req: TaskCreate):
    task = Task(type=req.type, payload=req.payload)
    tasks[task.id] = task
    return {"id": task.id}


@app.get("/tasks/pending", dependencies=[Depends(verify_key)])
def get_pending():
    for task in tasks.values():
        if task.status == TaskStatus.pending:
            task.status = TaskStatus.in_progress
            return task.model_dump()
    return Response(status_code=204)


@app.post("/tasks/{task_id}/result", dependencies=[Depends(verify_key)])
def submit_result(task_id: str, result: dict):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    task.result = result
    task.status = TaskStatus.completed
    return {"ok": True}


@app.get("/tasks/{task_id}/result", dependencies=[Depends(verify_key)])
async def get_result(task_id: str, wait: int = Query(default=0, le=30)):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    deadline = time.time() + wait
    while True:
        task = tasks[task_id]
        if task.status in (TaskStatus.completed, TaskStatus.failed, TaskStatus.timeout):
            return task.model_dump()
        if time.time() >= deadline:
            return Response(status_code=204)
        await asyncio.sleep(0.2)


@app.post("/files/{filename}", dependencies=[Depends(verify_key)])
async def upload_file(filename: str, request: Request):
    body = await request.body()
    if len(body) > MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    files[filename] = (body, time.time())
    return {"ok": True, "filename": filename, "size": len(body)}


@app.get("/files/{filename}", dependencies=[Depends(verify_key)])
def download_file(filename: str):
    if filename not in files:
        raise HTTPException(status_code=404, detail="File not found")
    data, _ = files[filename]
    return Response(content=data, media_type="application/octet-stream")


@app.get("/health")
def health():
    return {"status": "ok", "tasks": len(tasks), "files": len(files)}
