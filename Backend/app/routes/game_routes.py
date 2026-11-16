"""
Game Routes
Endpoints for Machine Learning prediction, Generative AI prompt generation,
user game history, and global leaderboards.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional

from app.auth import get_optional_user, get_current_user
from app.database import db_manager
from app.ml_service import ml_service
from app.genai_service import genai_service
from app.models import (
    PredictRequest,
    PredictResponse,
    GenAIPromptRequest,
    GenAIPromptResponse,
    GameHistoryOut,
    LeaderboardEntry
)

router = APIRouter(prefix="/game", tags=["Game & AI"])


import logging
logger = logging.getLogger("uvicorn.error")

@router.post("/predict", response_model=PredictResponse)
async def predict_sketch_category(req: PredictRequest):
    """
    Classifies a live drawing into one of 5 categories: Animal, Object, Food, Vehicle, Nature.
    Runs real inference using the trained KNeighborsClassifier.
    """
    result = ml_service.predict_drawing(
        strokes=req.strokes,
        image_base64=req.image_base64
    )
    logger.info(
        "LIVE AI PREDICTION: strokes=%s -> %s (conf: %.1f%%)",
        len(req.strokes) if req.strokes else 0,
        result["predicted_category"],
        result["confidence"] * 100
    )
    return result


@router.post("/prompt", response_model=GenAIPromptResponse)
async def generate_prompt(req: GenAIPromptRequest):
    """
    Generates a creative drawing prompt, secret word, game description, and challenge rule
    via Gemini LLM API (or graceful fallback).
    """
    result = await genai_service.generate_prompt(
        category=req.category,
        difficulty=req.difficulty
    )
    return result


@router.get("/description")
async def get_game_description(theme: Optional[str] = Query(default="Collaborative Drawing")):
    """Generates an engaging promotional or lobby description using Gemini LLM."""
    desc = await genai_service.generate_game_description(theme)
    return {"description": desc}


@router.get("/history", response_model=List[GameHistoryOut])
async def get_user_history(
    username: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Retrieves past game history, scores, and ranks for a user."""
    target_username = username
    if not target_username and current_user:
        target_username = current_user.get("username")

    if not target_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username parameter or authentication required"
        )

    history = await db_manager.get_user_game_history(target_username)
    return history


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = Query(default=15, ge=1, le=100)):
    """Retrieves top players ordered by total points earned."""
    data = await db_manager.get_global_leaderboard(limit=limit)
    leaderboard = []

    for entry in data:
        stats = entry.get("stats", {})
        played = stats.get("games_played", 0)
        won = stats.get("games_won", 0)
        win_rate = round((won / played * 100), 1) if played > 0 else 0.0

        leaderboard.append({
            "username": entry.get("username", "Player"),
            "total_score": stats.get("total_score", 0),
            "games_played": played,
            "games_won": won,
            "correct_guesses": stats.get("correct_guesses", 0),
            "win_rate": win_rate
        })

    return leaderboard

