"""
FastAPI Server & WebSocket Real-time API for Jev AI Trading Bot.
Provides live status, control endpoints, and bi-directional WebSocket streaming.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from execution.trader import coordinator


app = FastAPI(title="Jev AI Binance Trading Terminal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory for Web UI
web_dir = Path(__file__).resolve().parent.parent / "web"
web_dir.mkdir(exist_ok=True)


class SettingsPayload(BaseModel):
    risk_per_trade_percent: float
    min_jev_confidence: int
    atr_sl_multiplier: float
    atr_tp_multiplier: float
    trailing_stop_enabled: bool


@app.on_event("startup")
async def startup_event():
    # Start trading loop in background
    await coordinator.start()
    asyncio.create_task(broadcast_loop())


@app.on_event("shutdown")
async def shutdown_event():
    await coordinator.stop()


@app.get("/")
async def serve_index():
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "Dashboard loading...", "version": "1.0.0"})


@app.get("/api/status")
async def get_status():
    return coordinator.latest_data


@app.post("/api/bot/start")
async def start_bot():
    await coordinator.start()
    return {"status": "SUCCESS", "message": "Bot loop started."}


@app.post("/api/bot/stop")
async def stop_bot():
    await coordinator.stop()
    return {"status": "SUCCESS", "message": "Bot loop paused."}


@app.post("/api/bot/emergency_close")
async def emergency_close():
    res = await coordinator.emergency_close_all()
    return {"status": "SUCCESS", "result": res}


@app.post("/api/bot/settings")
async def update_settings(payload: SettingsPayload):
    config.risk_per_trade_percent = payload.risk_per_trade_percent
    config.min_jev_confidence = payload.min_jev_confidence
    config.atr_sl_multiplier = payload.atr_sl_multiplier
    config.atr_tp_multiplier = payload.atr_tp_multiplier
    config.trailing_stop_enabled = payload.trailing_stop_enabled

    coordinator.risk.risk_pct = payload.risk_per_trade_percent
    coordinator.risk.min_confidence = payload.min_jev_confidence
    coordinator.risk.atr_sl_mult = payload.atr_sl_multiplier
    coordinator.risk.atr_tp_mult = payload.atr_tp_multiplier
    coordinator.risk.trailing_enabled = payload.trailing_stop_enabled

    coordinator.log(f"⚙️ Cập nhật cấu hình: Risk={payload.risk_per_trade_percent}%, MinConf={payload.min_jev_confidence}%")
    return {"status": "SUCCESS", "message": "Settings updated."}


# WebSocket connection manager
active_websockets = set()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        # Send initial snapshot immediately
        await websocket.send_text(json.dumps(coordinator.latest_data))
        while True:
            # Keep connection alive and receive client commands
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                cmd = msg.get("command")
                if cmd == "EMERGENCY_CLOSE":
                    await coordinator.emergency_close_all()
                elif cmd == "START":
                    await coordinator.start()
                elif cmd == "STOP":
                    await coordinator.stop()
            except Exception:
                pass
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
    except Exception:
        active_websockets.discard(websocket)


async def broadcast_loop():
    """Broadcasts latest telemetry snapshot to all connected UI clients every second."""
    while True:
        if active_websockets:
            payload_str = json.dumps(coordinator.latest_data)
            disconnected = []
            for ws in active_websockets:
                try:
                    await ws.send_text(payload_str)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                active_websockets.discard(ws)
        await asyncio.sleep(1.5)


app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
