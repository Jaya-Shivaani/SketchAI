"""
Authentication Routes
Endpoints for user registration, login, and profile fetching.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from app.database import db_manager
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models import UserRegister, UserLogin, UserOut, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister):
    # Check if username exists
    existing_user = await db_manager.find_user_by_username(user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Check if email exists
    existing_email = await db_manager.find_user_by_email(user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )

    user_doc = {
        "username": user_in.username,
        "email": user_in.email.lower(),
        "hashed_password": hash_password(user_in.password),
        "created_at": datetime.utcnow().isoformat(),
        "stats": {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "correct_guesses": 0
        }
    }

    await db_manager.insert_user(user_doc)

    token = create_access_token(data={"sub": user_doc["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user_doc["username"],
            "email": user_doc["email"],
            "stats": user_doc["stats"],
            "created_at": user_doc["created_at"]
        }
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db_manager.find_user_by_username(credentials.username)
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    token = create_access_token(data={"sub": user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user.get("email", ""),
            "stats": user.get("stats", {
                "games_played": 0,
                "games_won": 0,
                "total_score": 0,
                "correct_guesses": 0
            }),
            "created_at": str(user.get("created_at", ""))
        }
    }


@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "email": current_user.get("email", ""),
        "stats": current_user.get("stats", {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "correct_guesses": 0
        }),
        "created_at": str(current_user.get("created_at", ""))
    }

