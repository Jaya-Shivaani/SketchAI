"""
WebSocket Connection & Game Room Manager
Handles real-time stroke streaming, canvas synchronization, guess validation,
scoring rules, countdown timers, turn rotation, and ML prediction broadcasts.
"""

import asyncio
import json
import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import WebSocket

from app.database import db_manager
from app.ml_service import ml_service
from app.genai_service import genai_service
from app.anti_cheat_service import anti_cheat_service

logger = logging.getLogger("uvicorn.error")


class Player:
    def __init__(self, username: str, websocket: WebSocket):
        self.username = username
        self.websocket = websocket
        self.score = 0
        self.round_score = 0
        self.is_drawer = False
        self.has_guessed = False
        self.is_connected = True

    def to_dict(self):
        return {
            "username": self.username,
            "score": self.score,
            "round_score": self.round_score,
            "is_drawer": self.is_drawer,
            "has_guessed": self.has_guessed,
            "is_connected": self.is_connected
        }


class GameRoom:
    def __init__(
        self,
        code: str,
        host_username: str,
        max_players: int = 8,
        round_duration: int = 60,
        max_rounds: int = 3,
        category: str = "Random",
        difficulty: str = "medium"
    ):
        self.code = code
        self.host_username = host_username
        self.max_players = max_players
        self.round_duration = round_duration
        self.max_rounds = max_rounds
        self.category = category
        self.difficulty = difficulty

        self.status = "lobby"  # lobby, playing, round_summary, game_over
        self.players: Dict[str, Player] = {}
        self.drawer_order: List[str] = []
        self.current_drawer_index: int = 0
        self.current_round: int = 0

        self.remaining_time: int = round_duration
        self.timer_task: Optional[asyncio.Task] = None

        # Round state
        self.current_word: str = ""
        self.current_prompt: str = ""
        self.current_description: str = ""
        self.current_challenge: str = ""
        self.current_category: str = ""
        self.revealed_indices: List[int] = []

        # Canvas stroke history for current round
        self.strokes: List[List[List[float]]] = []
        self.raw_strokes_data: List[Dict[str, Any]] = []

        # Current AI prediction
        self.ai_prediction: Dict[str, Any] = {
            "predicted_category": "Waiting for strokes...",
            "confidence": 0.0,
            "probabilities": {}
        }

    def get_drawer(self) -> Optional[Player]:
        if not self.drawer_order or self.current_drawer_index >= len(self.drawer_order):
            return None
        drawer_name = self.drawer_order[self.current_drawer_index]
        return self.players.get(drawer_name)

    def get_masked_word(self) -> str:
        """Constructs word mask, revealing spaces and progressively unmasked letters."""
        if not self.current_word:
            return ""
        chars = []
        for i, c in enumerate(self.current_word):
            if c == " ":
                chars.append(" ")
            elif i in self.revealed_indices:
                chars.append(c.upper())
            else:
                chars.append("_")
        return " ".join(chars)

    def get_room_state(self, for_username: Optional[str] = None) -> Dict[str, Any]:
        """Returns room state. Hides secret word from guessers during an active round."""
        drawer = self.get_drawer()
        is_drawer = (drawer and drawer.username == for_username)
        player_obj = self.players.get(for_username) if for_username else None
        has_guessed = (player_obj and player_obj.has_guessed)

        # Reveal word only if drawer, or has guessed, or round ended
        show_word = is_drawer or has_guessed or (self.status in ["round_summary", "game_over"])
        word_hint = self.get_masked_word()

        return {
            "room_code": self.code,
            "host": self.host_username,
            "status": self.status,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "round_duration": self.round_duration,
            "remaining_time": self.remaining_time,
            "current_drawer": drawer.username if drawer else None,
            "is_drawer": is_drawer,
            "category": self.current_category or self.category,
            "difficulty": self.difficulty,
            "word": self.current_word if show_word else word_hint,
            "word_hint": word_hint,
            "prompt": self.current_prompt if is_drawer else "",
            "description": self.current_description,
            "challenge": self.current_challenge,
            "players": [p.to_dict() for p in self.players.values()],
            "ai_prediction": self.ai_prediction
        }


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def get_room(self, room_code: str) -> Optional[GameRoom]:
        return self.rooms.get(room_code.upper())

    def create_room(
        self,
        code: str,
        host_username: str,
        max_players: int = 8,
        round_duration: int = 60,
        max_rounds: int = 3,
        category: str = "Random",
        difficulty: str = "medium"
    ) -> GameRoom:
        room = GameRoom(
            code=code.upper(),
            host_username=host_username,
            max_players=max_players,
            round_duration=round_duration,
            max_rounds=max_rounds,
            category=category,
            difficulty=difficulty
        )
        self.rooms[code.upper()] = room
        return room

    async def connect_player(self, websocket: WebSocket, room_code: str, username: str) -> Optional[GameRoom]:
        room = self.get_room(room_code)
        if not room:
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": f"Room '{room_code}' does not exist."})
            await websocket.close()
            return None

        if len(room.players) >= room.max_players and username not in room.players:
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": "Room is full."})
            await websocket.close()
            return None

        # Accept WebSocket
        await websocket.accept()

        player = room.players.get(username)
        if player:
            player.websocket = websocket
            player.is_connected = True
        else:
            player = Player(username, websocket)
            room.players[username] = player
            room.drawer_order.append(username)

        # Auto-promote first real player as room host if host is a placeholder or not in room
        if room.host_username.startswith("Host_") or room.host_username not in room.players or len(room.players) == 1:
            room.host_username = username

        # Broadcast player joined
        await self.broadcast_to_room(room.code, {
            "type": "player_joined",
            "username": username,
            "players": [p.to_dict() for p in room.players.values()]
        })

        # Send full initial room state to the newly connected player
        await websocket.send_json({
            "type": "init_state",
            "state": room.get_room_state(username),
            "canvas_history": room.raw_strokes_data
        })

        return room

    async def disconnect_player(self, room_code: str, username: str):
        room = self.get_room(room_code)
        if not room:
            return

        if username in room.players:
            room.players[username].is_connected = False

            await self.broadcast_to_room(room.code, {
                "type": "player_left",
                "username": username,
                "players": [p.to_dict() for p in room.players.values()]
            })

            # If host leaves and others remain, assign new host
            if room.host_username == username:
                active_players = [p.username for p in room.players.values() if p.is_connected]
                if active_players:
                    room.host_username = active_players[0]
                    await self.broadcast_to_room(room.code, {
                        "type": "host_changed",
                        "new_host": room.host_username
                    })

    async def broadcast_to_room(self, room_code: str, message: Dict[str, Any], exclude_username: Optional[str] = None):
        room = self.get_room(room_code)
        if not room:
            return

        for uname, player in list(room.players.items()):
            if exclude_username and uname == exclude_username:
                continue
            if player.is_connected:
                try:
                    await player.websocket.send_json(message)
                except Exception as e:
                    logger.debug("Failed sending WS message to %s: %s", uname, e)

    # --- Live Stroke Broadcast & Real-Time ML Classification ---
    async def handle_segment(self, room_code: str, username: str, segment_data: Dict[str, Any]):
        room = self.get_room(room_code)
        if not room:
            return
        if room.status == "playing":
            drawer = room.get_drawer()
            if not drawer or drawer.username != username:
                return
        # Broadcast continuous live drawing segment to guessers with zero lag
        await self.broadcast_to_room(room.code, {
            "type": "segment_broadcast",
            "segment": segment_data
        }, exclude_username=username)

    async def handle_stroke(self, room_code: str, username: str, stroke_data: Dict[str, Any]):
        room = self.get_room(room_code)
        if not room:
            return

        # If playing, ensure drawer is drawing; if in lobby, allow practice drawing
        if room.status == "playing":
            drawer = room.get_drawer()
            if not drawer or drawer.username != username:
                return

        # Store raw stroke for replay / new joiners
        room.raw_strokes_data.append(stroke_data)

        # Broadcast live stroke to all other players
        await self.broadcast_to_room(room.code, {
            "type": "stroke_broadcast",
            "stroke": stroke_data
        }, exclude_username=username)

        # Aggregate coordinate points into strokes list for ML feature extraction
        points = stroke_data.get("points", [])
        if points and len(points) >= 2:
            xs = [pt[0] for pt in points]
            ys = [pt[1] for pt in points]
            room.strokes.append([xs, ys])

            # Trigger real ML prediction on every stroke
            prediction = ml_service.predict_drawing(strokes=room.strokes)
            room.ai_prediction = prediction

            # Broadcast live AI prediction badge to all players in the room
            await self.broadcast_to_room(room.code, {
                "type": "ai_prediction_update",
                "prediction": prediction
            })

            # Real-Time Anti-Cheat OCR Inspection during active round
            if room.status == "playing" and len(room.raw_strokes_data) >= 3 and len(room.raw_strokes_data) % 2 == 0:
                is_cheat, detected_word, cheat_conf = anti_cheat_service.check_spoiler_cheating(
                    room.raw_strokes_data,
                    room.current_word
                )
                if is_cheat:
                    logger.warning(
                        "ANTI-CHEAT TRIGGERED: Player '%s' wrote word '%s' (detected: '%s', conf: %s)",
                        username, room.current_word, detected_word, cheat_conf
                    )
                    # Deduct penalty points from cheating drawer
                    drawer_obj = room.players.get(username)
                    if drawer_obj:
                        drawer_obj.score = max(0, drawer_obj.score - 50)
                        drawer_obj.round_score = max(0, drawer_obj.round_score - 50)

                    # Wipe the cheating drawing from canvas
                    room.raw_strokes_data.clear()
                    room.strokes.clear()
                    room.ai_prediction = {
                        "predicted_category": "Cheating Detected! 🚫",
                        "confidence": 1.0,
                        "probabilities": {}
                    }

                    # Broadcast canvas wipe and penalty warning to all players
                    await self.broadcast_to_room(room.code, {
                        "type": "canvas_cleared",
                        "cleared_by": "AI Referee"
                    })

                    await self.broadcast_to_room(room.code, {
                        "type": "anti_cheat_violation",
                        "cheater": username,
                        "detected_word": detected_word or room.current_word,
                        "message": f"🚨 CHEATING DETECTED! {username} wrote the word on the board! Canvas wiped & 50 pts deducted!",
                        "penalty": -50,
                        "players": [p.to_dict() for p in room.players.values()]
                    })

    async def handle_clear_canvas(self, room_code: str, username: str):
        room = self.get_room(room_code)
        if not room:
            return

        if room.status == "playing":
            drawer = room.get_drawer()
            if not drawer or drawer.username != username:
                return

        room.raw_strokes_data.clear()
        room.strokes.clear()
        room.ai_prediction = {
            "predicted_category": "Canvas cleared",
            "confidence": 0.0,
            "probabilities": {}
        }

        await self.broadcast_to_room(room.code, {
            "type": "canvas_cleared",
            "cleared_by": username
        })

    async def handle_undo_stroke(self, room_code: str, username: str):
        """Removes the last stroke from room history and updates AI prediction."""
        room = self.get_room(room_code)
        if not room:
            return

        if room.status == "playing":
            drawer = room.get_drawer()
            if not drawer or drawer.username != username:
                return

        if room.raw_strokes_data:
            room.raw_strokes_data.pop()
        if room.strokes:
            room.strokes.pop()

        # Re-compute AI prediction on the remaining strokes
        if room.strokes:
            prediction = ml_service.predict_drawing(strokes=room.strokes)
        else:
            prediction = {
                "predicted_category": "Waiting for strokes...",
                "confidence": 0.0,
                "probabilities": {}
            }
        room.ai_prediction = prediction

        await self.broadcast_to_room(room.code, {
            "type": "undo_broadcast",
            "canvas_history": room.raw_strokes_data,
            "ai_prediction": prediction
        })

    # --- Chat & Guess Submission System ---
    async def handle_guess(self, room_code: str, username: str, guess_text: str):
        room = self.get_room(room_code)
        if not room:
            return

        clean_guess = guess_text.strip()
        if not clean_guess:
            return

        target = room.current_word.strip().lower() if room.current_word else ""
        drawer = room.get_drawer()
        player = room.players.get(username)
        if not player:
            return

        # If not playing, treat as lobby/general chat
        if room.status != "playing":
            await self.broadcast_to_room(room.code, {
                "type": "chat_message",
                "username": username,
                "message": clean_guess,
                "is_system": False
            })
            return

        # Drawer cannot guess their own drawing or leak hints
        if drawer and drawer.username == username:
            guess_lower = clean_guess.lower()
            # Anti-Spoiling Check:
            # 1. Exact secret word (e.g. "bus")
            # 2. Secret word contained inside message (e.g. "draw a bus", "it is bus")
            # 3. Partial substring/spelling hints of length >= 2 (e.g. "bu", "us")
            # 4. Single-letter spelling hints (e.g. 'b', 'u', 's')
            common_safe_words = {"is", "in", "at", "on", "to", "me", "we", "he", "so", "no", "go", "do", "my", "by", "an", "as", "or", "if", "hi", "ok", "hey"}
            is_spoiler = False

            if target:
                if guess_lower == target:
                    is_spoiler = True
                elif target in guess_lower:
                    is_spoiler = True
                elif len(guess_lower) >= 2 and guess_lower in target and guess_lower not in common_safe_words:
                    is_spoiler = True
                elif len(guess_lower) == 1 and guess_lower in target and guess_lower.isalpha():
                    is_spoiler = True

            if is_spoiler:
                await player.websocket.send_json({
                    "type": "chat_message",
                    "username": "System",
                    "message": "🎨 Shh! You are the drawer — do not reveal or hint parts of the secret word!",
                    "is_system": True
                })
                return

            # Allow regular friendly chat from drawer
            await self.broadcast_to_room(room.code, {
                "type": "chat_message",
                "username": username,
                "message": clean_guess,
                "is_system": False
            })
            return

        # If player already guessed correctly in this round
        if player.has_guessed:
            await player.websocket.send_json({
                "type": "chat_message",
                "username": "System",
                "message": "You already guessed correctly! Shh, don't spoil it.",
                "is_system": True
            })
            return

        # Check if guess matches target secret word (case-insensitive, trimmed)
        if target and clean_guess.lower() == target:
            # CORRECT GUESS!
            player.has_guessed = True

            # Scoring: 100 base + remaining time * 2
            guess_points = 100 + max(room.remaining_time, 0) * 2
            drawer_points = 50

            player.score += guess_points
            player.round_score += guess_points
            if drawer:
                drawer.score += drawer_points
                drawer.round_score += drawer_points

            # Update stats in DB
            asyncio.create_task(db_manager.update_user_stats(username, score_delta=guess_points, correct_guess=True))
            if drawer:
                asyncio.create_task(db_manager.update_user_stats(drawer.username, score_delta=drawer_points))

            # Notify the room that this player guessed correctly (WITHOUT revealing the word)
            await self.broadcast_to_room(room.code, {
                "type": "correct_guess",
                "username": username,
                "points_awarded": guess_points,
                "players": [p.to_dict() for p in room.players.values()],
                "message": f"🎉 {username} guessed the secret word! (+{guess_points} pts)"
            })

            # Check if all active non-drawer guessers have guessed (or solo player got it)
            active_guessers = [
                p for p in room.players.values()
                if p.is_connected and not p.is_drawer
            ]
            all_guessed = (active_guessers and all(p.has_guessed for p in active_guessers)) or (len(room.players) == 1 and player.has_guessed)

            if all_guessed:
                # End round early if everyone got it right
                await self.broadcast_to_room(room.code, {
                    "type": "chat_message",
                    "username": "System",
                    "message": "🎉 Secret word guessed! Moving to round summary...",
                    "is_system": True
                })
                asyncio.create_task(self.end_round(room.code))

        else:
            # Regular incorrect guess - broadcast as chat to everyone
            await self.broadcast_to_room(room.code, {
                "type": "chat_message",
                "username": username,
                "message": clean_guess,
                "is_system": False
            })

    # --- Turn & Round Management ---
    async def start_game(self, room_code: str, requested_by: str = ""):
        room = self.get_room(room_code)
        if not room:
            return False

        if room.status == "playing":
            logger.info("Room %s is already playing, ignoring start_game", room_code)
            return True

        logger.info("start_game triggered for room %s by player '%s'", room_code, requested_by)

        # Adopt real player as host if default or if single player
        if room.host_username.startswith("Host_") or len(room.players) <= 1 or not room.host_username:
            if requested_by:
                room.host_username = requested_by

        room.status = "playing"
        room.current_round = 0
        room.current_drawer_index = 0

        # Reset all scores
        for p in room.players.values():
            p.score = 0
            p.round_score = 0

        await self.start_next_round(room_code)
        return True

    async def start_next_round(self, room_code: str):
        room = self.get_room(room_code)
        if not room:
            return

        # Cancel any active timer
        if room.timer_task and not room.timer_task.done():
            room.timer_task.cancel()

        active_players = [p.username for p in room.players.values() if p.is_connected]
        if not active_players:
            room.status = "lobby"
            return

        room.drawer_order = active_players
        if room.current_drawer_index >= len(room.drawer_order):
            room.current_drawer_index = 0
            room.current_round += 1

        if room.current_round >= room.max_rounds:
            # All rounds completed
            await self.end_game(room_code)
            return

        # Advance drawer
        drawer_name = room.drawer_order[room.current_drawer_index]
        for uname, p in room.players.items():
            p.is_drawer = (uname == drawer_name)
            p.has_guessed = False
            p.round_score = 0

        # Clear canvas & revealed hints
        room.strokes.clear()
        room.raw_strokes_data.clear()
        room.revealed_indices.clear()
        room.remaining_time = room.round_duration
        room.status = "playing"

        try:
            # Generate prompt using GenAI service (Gemini)
            prompt_data = await genai_service.generate_prompt(category=room.category, difficulty=room.difficulty)
            room.current_word = prompt_data.get("word") or "Cat"
            room.current_category = prompt_data.get("category") or "Animal"
            room.current_prompt = prompt_data.get("prompt") or f"Draw a {room.current_word} sketch!"
            room.current_description = prompt_data.get("description") or "Show your artistic skills!"
            room.current_challenge = prompt_data.get("challenge") or "Draw as fast as you can!"
        except Exception as e:
            logger.error("Error generating prompt: %s", e)
            room.current_word = "Cat"
            room.current_category = "Animal"
            room.current_prompt = "Draw a playful cat!"
            room.current_description = "Capture those pointy ears and tail!"
            room.current_challenge = "Speed Paw: 60s"

        room.ai_prediction = {
            "predicted_category": f"Target: {room.current_category}",
            "confidence": 0.0,
            "probabilities": {}
        }

        # Send personalized round start event to each player
        for uname, p in room.players.items():
            if p.is_connected:
                try:
                    await p.websocket.send_json({
                        "type": "round_start",
                        "state": room.get_room_state(uname)
                    })
                except Exception as e:
                    logger.debug("Error sending round start to %s: %s", uname, e)

        # Start background timer task
        room.timer_task = asyncio.create_task(self._run_timer_loop(room_code))

    async def _run_timer_loop(self, room_code: str):
        room = self.get_room(room_code)
        if not room:
            return

        try:
            while room.remaining_time > 0 and room.status == "playing":
                await asyncio.sleep(1)
                room.remaining_time -= 1

                # Dynamic Progressive Letter Hints (reveals 1st letter at <= 40% time, 2nd letter at <= 20% time)
                # For 3-letter words like "Cat", NEVER reveal hints so word isn't given away!
                word_clean = room.current_word.replace(" ", "")
                if len(word_clean) >= 4:
                    first_hint_time = int(room.round_duration * 0.40)   # e.g. 24s if round=60s
                    second_hint_time = int(room.round_duration * 0.20)  # e.g. 12s if round=60s

                    if room.remaining_time <= first_hint_time and len(room.revealed_indices) == 0:
                        avail = [i for i, c in enumerate(room.current_word) if c != " "]
                        if avail:
                            room.revealed_indices.append(random.choice(avail))
                    elif room.remaining_time <= second_hint_time and len(room.revealed_indices) == 1 and len(word_clean) >= 6:
                        avail = [i for i, c in enumerate(room.current_word) if c != " " and i not in room.revealed_indices]
                        if avail:
                            room.revealed_indices.append(random.choice(avail))

                await self.broadcast_to_room(room.code, {
                    "type": "timer_tick",
                    "remaining_time": room.remaining_time,
                    "word_hint": room.get_masked_word()
                })

            if room.status == "playing":
                await self.end_round(room_code)
        except asyncio.CancelledError:
            pass

    async def end_round(self, room_code: str):
        room = self.get_room(room_code)
        if not room:
            return

        current_task = asyncio.current_task()
        if room.timer_task and not room.timer_task.done() and room.timer_task != current_task:
            room.timer_task.cancel()

        room.status = "round_summary"
        drawer = room.get_drawer()

        # Final AI classification of the completed sketch
        final_prediction = ml_service.predict_drawing(strokes=room.strokes)
        ai_matched = (final_prediction["predicted_category"].lower() == room.current_category.lower())

        # Generate witty commentary / playful roast via Gemini AI
        guessed_count = sum(1 for p in room.players.values() if p.has_guessed)
        commentary = await genai_service.generate_round_commentary(
            word=room.current_word,
            category=room.current_category,
            drawer_name=drawer.username if drawer else "Unknown",
            ai_predicted=final_prediction["predicted_category"],
            ai_matched=ai_matched,
            guessed_count=guessed_count
        )

        summary_data = {
            "type": "round_ended",
            "secret_word": room.current_word,
            "category": room.current_category,
            "drawer": drawer.username if drawer else "Unknown",
            "ai_predicted_category": final_prediction["predicted_category"],
            "ai_confidence": final_prediction["confidence"],
            "ai_matched_category": ai_matched,
            "ai_commentary": commentary,
            "players": [p.to_dict() for p in room.players.values()]
        }

        await self.broadcast_to_room(room.code, summary_data)

        # 7-second intermission countdown - broadcast each second so frontend stays in sync
        for tick in range(7, 0, -1):
            await asyncio.sleep(1)
            await self.broadcast_to_room(room.code, {
                "type": "intermission_tick",
                "seconds_remaining": tick - 1,
                "message": f"Next round in {tick - 1}s..." if tick > 1 else "Starting now!"
            })

        room.current_drawer_index += 1
        await self.start_next_round(room_code)

    async def end_game(self, room_code: str):
        room = self.get_room(room_code)
        if not room:
            return

        room.status = "game_over"

        # Sort players by score
        sorted_players = sorted(room.players.values(), key=lambda p: p.score, reverse=True)
        winner_name = sorted_players[0].username if sorted_players else "No one"

        rankings = []
        for rank, p in enumerate(sorted_players, start=1):
            rankings.append({
                "username": p.username,
                "score": p.score,
                "rank": rank
            })

            # Update winner stats in DB
            is_win = (rank == 1 and p.score > 0)
            asyncio.create_task(db_manager.update_user_stats(p.username, score_delta=0, is_win=is_win))

        # Save game history to database
        history_doc = {
            "room_code": room.code,
            "played_at": datetime.utcnow(),
            "rounds": room.max_rounds,
            "winner": winner_name,
            "category": room.category,
            "difficulty": room.difficulty,
            "players": rankings
        }
        asyncio.create_task(db_manager.record_game_history(history_doc))

        await self.broadcast_to_room(room.code, {
            "type": "game_over",
            "winner": winner_name,
            "rankings": rankings
        })

    async def handle_emoji(self, room_code: str, username: str, emoji: str):
        room = self.get_room(room_code)
        if not room:
            return
        await self.broadcast_to_room(room.code, {
            "type": "emoji_reaction",
            "emoji": emoji,
            "sender": username
        })


connection_manager = ConnectionManager()

