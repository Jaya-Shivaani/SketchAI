"""
Database Module: MongoDB connection management with Motor async client.
Provides collections for users, rooms, game history, and leaderboards.
Includes an in-memory resilient fallback repository for test environments if MongoDB is offline.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger("uvicorn.error")


class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_connected: bool = False

    # Resilient fallback storage if MongoDB is not reachable
    _memory_users: Dict[str, Dict[str, Any]] = {}
    _memory_rooms: Dict[str, Dict[str, Any]] = {}
    _memory_history: List[Dict[str, Any]] = []

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            self.db = self.client[settings.DATABASE_NAME]
            await self.client.admin.command('ping')
            self.is_connected = True
            logger.info("Connected to MongoDB successfully at %s", settings.MONGO_URI)

            # Ensure indexes
            await self.db.users.create_index("username", unique=True)
            await self.db.users.create_index("email", unique=True)
            await self.db.rooms.create_index("code", unique=True)
            await self.db.game_history.create_index("played_at")
        except Exception as e:
            self.is_connected = False
            logger.warning("MongoDB connection failed (%s). Operating with in-memory fallback.", e)

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection.")

    # --- User Operations ---
    async def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if self.is_connected and self.db is not None:
            try:
                # Case-insensitive lookup using regex
                import re
                user = await self.db.users.find_one({"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}})
                return user
            except Exception as e:
                logger.error("DB error finding user by username: %s", e)
        for u in self._memory_users.values():
            if u.get("username", "").lower() == username.lower():
                return u
        return None

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if self.is_connected and self.db is not None:
            try:
                user = await self.db.users.find_one({"email": email.lower()})
                return user
            except Exception as e:
                logger.error("DB error finding user by email: %s", e)
        for u in self._memory_users.values():
            if u.get("email", "").lower() == email.lower():
                return u
        return None

    async def insert_user(self, user_doc: Dict[str, Any]) -> bool:
        user_doc["created_at"] = user_doc.get("created_at", datetime.utcnow())
        user_doc["stats"] = user_doc.get("stats", {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "correct_guesses": 0
        })

        if self.is_connected and self.db is not None:
            try:
                await self.db.users.insert_one(user_doc)
                return True
            except Exception as e:
                logger.error("DB error inserting user: %s", e)
        # Store in fallback
        self._memory_users[user_doc["username"].lower()] = user_doc
        return True

    async def update_user_stats(self, username: str, score_delta: int, is_win: bool = False, correct_guess: bool = False):
        if self.is_connected and self.db is not None:
            try:
                import re
                inc_doc = {
                    "stats.total_score": score_delta,
                    "stats.games_played": 1,
                    "stats.games_won": 1 if is_win else 0,
                    "stats.correct_guesses": 1 if correct_guess else 0
                }
                # Case-insensitive username match to avoid case mismatch bugs
                await self.db.users.update_one(
                    {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}},
                    {"$inc": inc_doc}
                )
                return
            except Exception as e:
                logger.error("DB error updating user stats: %s", e)

        # Fallback update
        u = self._memory_users.get(username.lower())
        if u:
            stats = u.setdefault("stats", {"games_played": 0, "games_won": 0, "total_score": 0, "correct_guesses": 0})
            stats["total_score"] = stats.get("total_score", 0) + score_delta
            stats["games_played"] = stats.get("games_played", 0) + 1
            if is_win:
                stats["games_won"] = stats.get("games_won", 0) + 1
            if correct_guess:
                stats["correct_guesses"] = stats.get("correct_guesses", 0) + 1

    # --- Game History Operations ---
    async def record_game_history(self, history_doc: Dict[str, Any]):
        history_doc["played_at"] = history_doc.get("played_at", datetime.utcnow())
        if self.is_connected and self.db is not None:
            try:
                await self.db.game_history.insert_one(history_doc)
                return
            except Exception as e:
                logger.error("DB error recording game history: %s", e)
        self._memory_history.append(history_doc)

    async def get_user_game_history(self, username: str, limit: int = 20) -> List[Dict[str, Any]]:
        if self.is_connected and self.db is not None:
            try:
                import re
                cursor = self.db.game_history.find(
                    {"players.username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
                ).sort("played_at", -1).limit(limit)
                history = await cursor.to_list(length=limit)
                for h in history:
                    h["_id"] = str(h["_id"])
                    if isinstance(h.get("played_at"), datetime):
                        h["played_at"] = h["played_at"].isoformat()
                return history
            except Exception as e:
                logger.error("DB error getting user game history: %s", e)

        # Fallback
        res = [h for h in self._memory_history if any(p.get("username") == username for p in h.get("players", []))]
        res.sort(key=lambda x: str(x.get("played_at")), reverse=True)
        return res[:limit]

    async def get_global_leaderboard(self, limit: int = 15) -> List[Dict[str, Any]]:
        if self.is_connected and self.db is not None:
            try:
                cursor = self.db.users.find({}, {"_id": 0, "username": 1, "stats": 1}).sort("stats.total_score", -1).limit(limit)
                users = await cursor.to_list(length=limit)
                return users
            except Exception as e:
                logger.error("DB error getting leaderboard: %s", e)

        # Fallback
        users = list(self._memory_users.values())
        users.sort(key=lambda u: u.get("stats", {}).get("total_score", 0), reverse=True)
        return [{"username": u["username"], "stats": u.get("stats", {})} for u in users[:limit]]


db_manager = DatabaseManager()

