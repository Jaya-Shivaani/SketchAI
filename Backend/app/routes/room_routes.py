"""
Room Management Routes
Endpoints for creating, joining, and listing multiplayer rooms.
"""

import random
import string
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional

from app.auth import get_optional_user
from app.models import RoomCreate, RoomJoin, RoomOut
from app.websocket_manager import connection_manager

router = APIRouter(prefix="/rooms", tags=["Rooms"])


def generate_room_code(length: int = 6) -> str:
    """Generates a clean alphanumeric room code (e.g. SKETCH, DRAW42)."""
    chars = string.ascii_uppercase + "23456789"
    return "".join(random.choices(chars, k=length))


@router.post("/create", response_model=RoomOut)
async def create_room(room_in: RoomCreate, current_user: Optional[dict] = Depends(get_optional_user)):
    host_name = current_user["username"] if current_user else f"Host_{random.randint(100, 999)}"

    # Generate unique room code
    code = generate_room_code()
    while connection_manager.get_room(code) is not None:
        code = generate_room_code()

    room = connection_manager.create_room(
        code=code,
        host_username=host_name,
        max_players=room_in.max_players,
        round_duration=room_in.round_duration,
        max_rounds=room_in.max_rounds,
        category=room_in.category or "Random",
        difficulty=room_in.difficulty or "medium"
    )

    return {
        "room_code": room.code,
        "host_username": room.host_username,
        "players": list(room.players.keys()),
        "status": room.status,
        "current_round": room.current_round,
        "max_rounds": room.max_rounds,
        "round_duration": room.round_duration
    }


@router.post("/join", response_model=RoomOut)
async def join_room(join_in: RoomJoin):
    code = join_in.room_code.strip().upper()
    room = connection_manager.get_room(code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with code '{code}' does not exist"
        )

    if len(room.players) >= room.max_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room '{code}' is already full ({room.max_players} players max)"
        )

    return {
        "room_code": room.code,
        "host_username": room.host_username,
        "players": list(room.players.keys()),
        "status": room.status,
        "current_round": room.current_round,
        "max_rounds": room.max_rounds,
        "round_duration": room.round_duration
    }


@router.get("/list", response_model=List[RoomOut])
async def list_active_rooms():
    active_rooms = []
    for room in connection_manager.rooms.values():
        active_rooms.append({
            "room_code": room.code,
            "host_username": room.host_username,
            "players": list(room.players.keys()),
            "status": room.status,
            "current_round": room.current_round,
            "max_rounds": room.max_rounds,
            "round_duration": room.round_duration
        })
    return active_rooms


@router.get("/{room_code}", response_model=RoomOut)
async def get_room_details(room_code: str):
    code = room_code.strip().upper()
    room = connection_manager.get_room(code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{code}' not found"
        )

    return {
        "room_code": room.code,
        "host_username": room.host_username,
        "players": list(room.players.keys()),
        "status": room.status,
        "current_round": room.current_round,
        "max_rounds": room.max_rounds,
        "round_duration": room.round_duration
    }


@router.post("/{room_code}/start")
async def start_room_game(room_code: str):
    """Direct REST endpoint to trigger starting the game."""
    code = room_code.strip().upper()
    room = connection_manager.get_room(code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{code}' not found"
        )

    success = await connection_manager.start_game(code, requested_by=room.host_username)
    return {
        "success": success,
        "status": room.status,
        "current_round": room.current_round,
        "room_code": code
    }

