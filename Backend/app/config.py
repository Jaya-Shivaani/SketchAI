"""
Application Configuration and Environment Settings
Loads environment variables safely with python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root or backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings:
    PROJECT_NAME: str = "AI-Enhanced Collaborative Drawing Game"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # MongoDB Configuration
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "drawing_game_db")

    # JWT Authentication Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-collaborative-drawing-key-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Generative AI (Gemini) Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Machine Learning Model Paths
    ML_DIR: str = os.path.join(BASE_DIR, "ML")
    SAVED_MODELS_DIR: str = os.path.join(ML_DIR, "saved_models")

    MODEL_PATH: str = os.path.join(SAVED_MODELS_DIR, "knn_drawing_model.joblib")
    SCALER_PATH: str = os.path.join(SAVED_MODELS_DIR, "scaler.joblib")
    ENCODER_PATH: str = os.path.join(SAVED_MODELS_DIR, "label_encoder.joblib")


settings = Settings()
