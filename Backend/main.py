"""
FastAPI Server Entry Point
Initializes FastAPI, configures CORS, mounts static frontend assets,
and integrates REST endpoints and WebSocket channels.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "Backend"))

from app.config import settings
from app.database import db_manager
from app.ml_service import ml_service
from app.models import PredictRequest, PredictResponse
from app.routes import auth_routes, room_routes, game_routes, ws_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and verify ML models
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    await db_manager.connect()
    ml_service.load_models()
    print("✅ Application startup complete. Ready for real-time multiplayer connections.")
    yield
    # Shutdown
    print("🛑 Shutting down application...")
    await db_manager.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multiplayer Collaborative Drawing Game Platform with Machine Learning & GenAI",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers under /api
app.include_router(auth_routes.router, prefix="/api")
app.include_router(room_routes.router, prefix="/api")
app.include_router(game_routes.router, prefix="/api")
app.include_router(ws_routes.router)


# Expose root POST /predict alias as specified in requirements
@app.post("/predict", response_model=PredictResponse, tags=["Game & AI"])
async def predict_alias(req: PredictRequest):
    """Direct alias for POST /predict as specified in task requirements."""
    return ml_service.predict_drawing(
        strokes=req.strokes,
        image_base64=req.image_base64
    )


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mongodb_connected": db_manager.is_connected,
        "ml_model_loaded": ml_service.is_loaded,
        "version": settings.VERSION
    }


# Mount Frontend static files
FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/game")
    async def serve_game():
        return FileResponse(os.path.join(FRONTEND_DIR, "game.html"))

    @app.get("/dashboard")
    async def serve_dashboard():
        return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

