"""
WebSocket Real-Time Routes
Handles real-time bidirectional multiplayer communication:
stroke streaming, live AI predictions, guess submissions, round synchronization.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.auth import decode_access_token
from app.websocket_manager import connection_manager

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/room/{room_code}")
async def room_websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    username: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None)
):
    # Resolve player identity from token or username
    player_name = username
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            player_name = payload["sub"]

    if not player_name:
        # Fallback guest name
        import random
        player_name = f"Guest_{random.randint(1000, 9999)}"

    code = room_code.strip().upper()
    room = await connection_manager.connect_player(websocket, code, player_name)
    if not room:
        return

    logger.info("Player '%s' connected to room '%s'", player_name, code)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "draw_segment":
                segment_data = msg.get("segment", {})
                await connection_manager.handle_segment(code, player_name, segment_data)

            elif msg_type == "draw_stroke":
                stroke_data = msg.get("stroke", {})
                await connection_manager.handle_stroke(code, player_name, stroke_data)

            elif msg_type == "clear_canvas":
                await connection_manager.handle_clear_canvas(code, player_name)

            elif msg_type == "undo_stroke":
                await connection_manager.handle_undo_stroke(code, player_name)

            elif msg_type == "chat_guess":
                guess_text = msg.get("message", "")
                await connection_manager.handle_guess(code, player_name, guess_text)

            elif msg_type == "start_game":
                await connection_manager.start_game(code, player_name)

            elif msg_type == "emoji_reaction":
                emoji = msg.get("emoji", "🔥")
                await connection_manager.handle_emoji(code, player_name, emoji)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Player '%s' disconnected from room '%s'", player_name, code)
        await connection_manager.disconnect_player(code, player_name)
    except Exception as e:
        logger.error("WebSocket exception for %s in %s: %s", player_name, code, e)
        await connection_manager.disconnect_player(code, player_name)

