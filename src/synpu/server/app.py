import asyncio
import re
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from synpu import config

ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
)

DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[3] / "static"


def is_allowed_origin(origin: str | None) -> bool:
    if origin is None:
        return True
    return re.fullmatch(ORIGIN_REGEX, origin) is not None


def create_app(collector, push_interval: float = config.PUSH_INTERVAL_S,
               static_dir: Path = DEFAULT_STATIC_DIR, on_show=None) -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=ORIGIN_REGEX,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/snapshot")
    def snapshot():
        return collector.snapshot()

    @app.get("/api/show")
    def show():
        if on_show is not None:
            try:
                on_show()
            except Exception:
                pass
        return {"ok": True}

    @app.get("/api/history")
    def history(minutes: int = 60):
        minutes = min(max(minutes, 1), 60)
        history_buffer = getattr(collector, "history", None)
        samples = history_buffer.series(minutes) if history_buffer is not None else []
        return {"minutes": minutes, "samples": samples}

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        if not is_allowed_origin(websocket.headers.get("origin")):
            await websocket.accept()
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                data = await asyncio.to_thread(collector.snapshot)
                await websocket.send_json(data)
                await asyncio.sleep(push_interval)
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    return app
