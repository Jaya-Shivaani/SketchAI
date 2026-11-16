"""
Pydantic Models and Schemas
Data contracts for REST APIs and WebSocket payloads.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# --- Auth Schemas ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=25, pattern=r"^[a-zA-Z0-9_\s-]+$")
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserStats(BaseModel):
    games_played: int = 0
    games_won: int = 0
    total_score: int = 0
    correct_guesses: int = 0


class UserOut(BaseModel):
    username: str
    email: str
    stats: UserStats = Field(default_factory=UserStats)
    created_at: Optional[Any] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Room Schemas ---
class RoomCreate(BaseModel):
    max_players: int = Field(default=8, ge=2, le=16)
    round_duration: int = Field(default=60, ge=30, le=120)
    max_rounds: int = Field(default=3, ge=1, le=10)
    category: Optional[str] = "Random"
    difficulty: Optional[str] = "medium"


class RoomJoin(BaseModel):
    room_code: str = Field(..., min_length=4, max_length=10)
    player_name: Optional[str] = None


class RoomOut(BaseModel):
    room_code: str
    host_username: str
    players: List[str]
    status: str
    current_round: int
    max_rounds: int
    round_duration: int


# --- ML & Drawing Schemas ---
class PredictRequest(BaseModel):
    strokes: Optional[List[List[List[float]]]] = None
    image_base64: Optional[str] = None


class PredictResponse(BaseModel):
    predicted_category: str
    confidence: float
    probabilities: Dict[str, float]
    category_id: int


# --- GenAI Schemas ---
class GenAIPromptRequest(BaseModel):
    category: Optional[str] = "Random"
    difficulty: Optional[str] = "medium"


class GenAIPromptResponse(BaseModel):
    word: str
    category: str
    prompt: str
    description: str
    challenge: str
    difficulty: str


# --- Game History & Leaderboard Schemas ---
class PlayerScoreItem(BaseModel):
    username: str
    score: int
    rank: int = 1


class GameHistoryOut(BaseModel):
    room_code: str
    played_at: str
    rounds: int
    winner: str
    players: List[PlayerScoreItem]


class LeaderboardEntry(BaseModel):
    username: str
    total_score: int
    games_played: int
    games_won: int
    correct_guesses: int
    win_rate: float
