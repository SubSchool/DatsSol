from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import init_db
from app.services.runtime import runtime_service
from app.services.stats_tracker import stats_tracker_service

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    await stats_tracker_service.start()
    if settings.runtime_autostart and (settings.game_provider != "datssol-live" or settings.auth_configured):
        await runtime_service.start()
    yield
    await runtime_service.close()
    await stats_tracker_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.websocket("/ws/telemetry")
async def telemetry_socket(websocket: WebSocket) -> None:
    await runtime_service.telemetry.connect(websocket)
    await websocket.send_json({"type": "world.updated", "world": runtime_service.world().model_dump(mode="json")})
    await websocket.send_json({"type": "runtime.updated", "runtime": runtime_service.snapshot().model_dump(mode="json")})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        runtime_service.telemetry.disconnect(websocket)
