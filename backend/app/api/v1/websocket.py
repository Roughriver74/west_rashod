"""WebSocket endpoints for real-time updates."""
import logging
import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.services.background_tasks import task_manager, TaskInfo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections for task updates."""

    def __init__(self):
        # task_id -> set of websockets
        self.task_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> set of task_ids
        self.connection_tasks: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        """Connect a websocket to task updates."""
        await websocket.accept()

        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)

        if websocket not in self.connection_tasks:
            self.connection_tasks[websocket] = set()
        self.connection_tasks[websocket].add(task_id)

        logger.info(f"WebSocket connected for task {task_id}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket from all task updates."""
        if websocket in self.connection_tasks:
            for task_id in self.connection_tasks[websocket]:
                if task_id in self.task_connections:
                    self.task_connections[task_id].discard(websocket)
                    if not self.task_connections[task_id]:
                        del self.task_connections[task_id]
            del self.connection_tasks[websocket]

        logger.info("WebSocket disconnected")

    async def broadcast_task_update(self, task_id: str, task: TaskInfo):
        """Broadcast task update to all connected clients."""
        if task_id not in self.task_connections:
            return

        message = json.dumps({
            "type": "task_update",
            "data": task.to_dict()
        })

        disconnected = set()
        for websocket in self.task_connections[task_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(
    websocket: WebSocket,
    task_id: str
):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket, task_id)

    # Send initial task state
    task = task_manager.get_task(task_id)
    if task:
        await websocket.send_text(json.dumps({
            "type": "task_update",
            "data": task.to_dict()
        }))

    # Subscribe to task updates
    async def on_task_update(task_info: TaskInfo):
        await manager.broadcast_task_update(task_id, task_info)

    task_manager.subscribe(task_id, on_task_update)

    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                try:
                    msg = json.loads(data)
                    if msg.get("action") == "cancel":
                        task_manager.cancel_task(task_id)
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        task_manager.unsubscribe(task_id, on_task_update)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        task_manager.unsubscribe(task_id, on_task_update)


@router.websocket("/ws/tasks")
async def websocket_all_tasks(websocket: WebSocket):
    """WebSocket endpoint for all task updates."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "list":
                # Send current task list
                tasks = task_manager.get_all_tasks()
                await websocket.send_text(json.dumps({
                    "type": "task_list",
                    "data": [t.to_dict() for t in tasks]
                }))
            elif data.startswith("subscribe:"):
                task_id = data.split(":", 1)[1]
                if task_id not in manager.task_connections:
                    manager.task_connections[task_id] = set()
                manager.task_connections[task_id].add(websocket)
                if websocket not in manager.connection_tasks:
                    manager.connection_tasks[websocket] = set()
                manager.connection_tasks[websocket].add(task_id)

                # Send current state
                task = task_manager.get_task(task_id)
                if task:
                    await websocket.send_text(json.dumps({
                        "type": "task_update",
                        "data": task.to_dict()
                    }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
