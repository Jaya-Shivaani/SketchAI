"""
Generative AI Service (Gemini API Integration)
Generates creative drawing prompts, game descriptions, and round challenge ideas
tailored by category and difficulty level using Google Gemini LLM.
Handles timeouts and API limits gracefully.
"""

import os
import json
import logging
import random
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger("uvicorn.error")

FALLBACK_PROMPTS = {
    "Animal": [
        {"word": "Cat", "prompt": "Draw a mischievous cat knocking a glass off a table.", "description": "Feline mischief incoming! Capture those pointy ears and swishing tail.", "challenge": "Fast Paw: Finish in under 45 seconds!"},
        {"word": "Dog", "prompt": "Draw a happy golden retriever catching a flying frisbee.", "description": "Man's best friend in full acrobatic action!", "challenge": "Floppy Ears Only: Use smooth rounded lines."},
        {"word": "Fish", "prompt": "Draw an exotic tropical fish swimming through colorful coral.", "description": "Dive deep under the sea! Don't forget the dorsal fin.", "challenge": "Bubble Blitz: Add bubbles with your brush!"},
        {"word": "Bird", "prompt": "Draw a majestic eagle soaring over snow-capped mountains.", "description": "Wings spread wide in the open sky!", "challenge": "One Continuous Line for the wings."},
        {"word": "Rabbit", "prompt": "Draw a fluffy rabbit munching on a giant orange carrot.", "description": "Long ears, twitchy nose, and lots of cuteness.", "challenge": "Speed Hop: Keep it under 50 seconds!"}
    ],
    "Object": [
        {"word": "Clock", "prompt": "Draw an antique grandfather clock ticking at midnight.", "description": "Tick-tock, can you capture the passage of time?", "challenge": "Roman Numerals: Draw at least 2 dial marks."},
        {"word": "Cup", "prompt": "Draw a steaming mug of hot chocolate with floating marshmallows.", "description": "Cozy vibes and warm drinks!", "challenge": "Handle First: Start by drawing the handle."},
        {"word": "Chair", "prompt": "Draw a futuristic gaming chair with glowing neon trim.", "description": "Maximum ergonomic comfort from the year 3000.", "challenge": "Geometric Precision: Use sharp straight lines."},
        {"word": "Umbrella", "prompt": "Draw a bright yellow umbrella shielding someone in a thunderstorm.", "description": "Rain, rain, go away! Make that canopy pop.", "challenge": "Add Rain Drops: Tap the canvas for droplets."}
    ],
    "Food": [
        {"word": "Pizza", "prompt": "Draw a slice of gooey pepperoni pizza with stretchy melted cheese.", "description": "Everyone's favorite slice of heaven!", "challenge": "Cheesy Pull: Draw a stretching cheese string."},
        {"word": "Apple", "prompt": "Draw a glossy red apple with a leaf and a tiny cute worm peeking out.", "description": "Crisp, delicious, and fresh from the orchard.", "challenge": "Two-Tone: Use red and green colors."},
        {"word": "Cake", "prompt": "Draw a decadent multi-tier birthday cake with burning candles.", "description": "Make a wish! Frosting, sprinkles, and celebration.", "challenge": "Three Tiers: Stack them high!"},
        {"word": "Ice Cream", "prompt": "Draw a towering waffle cone with three melting scoops of ice cream.", "description": "Hurry up before it melts all over your canvas!", "challenge": "Triple Scoop: Use distinct colors."}
    ],
    "Vehicle": [
        {"word": "Car", "prompt": "Draw a sleek electric sports car speeding through a tunnel.", "description": "Rev your engines! Sleek curves and spinning wheels.", "challenge": "Speed Blur: Draw wind trails behind it."},
        {"word": "Airplane", "prompt": "Draw a commercial airliner leaving white contrails across blue sky.", "description": "High above the clouds at 30,000 feet!", "challenge": "Swept Wings: Make the wings symmetrical."},
        {"word": "Bicycle", "prompt": "Draw a vintage bicycle with a front wicker basket full of flowers.", "description": "Pedal power! Two wheels and classic handlebars.", "challenge": "Spoke Master: Draw spokes on both wheels."},
        {"word": "Bus", "prompt": "Draw a double-decker bus navigating a bustling city street.", "description": "All aboard! Windows, stairs, and bright paint.", "challenge": "Double Decker: Make it two levels tall."}
    ],
    "Nature": [
        {"word": "Tree", "prompt": "Draw an ancient giant oak tree with sprawling roots and lush leaves.", "description": "Deep roots and leafy majesty reaching towards the sky.", "challenge": "Branch Out: Draw at least 5 visible branches."},
        {"word": "Sun", "prompt": "Draw a smiling cartoon sun with sunglasses rising over hills.", "description": "Good morning sunshine! Radiating warmth and positive energy.", "challenge": "Radiant Rays: Draw at least 8 rays around it."},
        {"word": "Mountain", "prompt": "Draw rugged volcanic mountains with glowing lava down the slopes.", "description": "Epic tectonic power! Jagged peaks and dramatic heights.", "challenge": "Snow Peaks: Draw snowcaps on the summits."},
        {"word": "Flower", "prompt": "Draw a blooming sunflower turning its face toward the light.", "description": "Bright golden petals radiating joy.", "challenge": "Petal Burst: Draw at least 6 petals around center."}
    ]
}


class GenAIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                # Initialize official Google GenAI client
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("GenAI Service: Initialized Gemini Client successfully.")
            except Exception as e:
                logger.warning("GenAI Service: Could not initialize Gemini client: %s", e)
                self.client = None
        else:
            logger.info("GenAI Service: GEMINI_API_KEY not configured. Using dynamic prompt generator.")

    async def generate_prompt(self, category: Optional[str] = "Random", difficulty: Optional[str] = "medium") -> Dict[str, Any]:
        """
        Generates a drawing prompt, secret word, fun description, and challenge rule.
        Uses Gemini LLM if API key is valid; otherwise uses dynamic template generator.
        """
        valid_cats = ["Animal", "Object", "Food", "Vehicle", "Nature"]
        selected_cat = category if category in valid_cats else random.choice(valid_cats)
        diff = difficulty if difficulty in ["easy", "medium", "hard"] else "medium"

        if self.client:
            try:
                prompt_text = (
                    f"You are the game master for an online multiplayer drawing and guessing game.\n"
                    f"Generate a creative drawing round for category: '{selected_cat}' and difficulty: '{diff}'.\n"
                    f"Respond ONLY with a valid JSON object (no markdown, no backticks) with keys:\n"
                    f"- \"word\": single word or simple phrase to guess (e.g. Cat, Airplane, Pizza)\n"
                    f"- \"category\": \"{selected_cat}\"\n"
                    f"- \"prompt\": one engaging instruction sentence for the drawer (e.g. 'Draw a playful kitten chasing a butterfly within 60 seconds.')\n"
                    f"- \"description\": one witty, fun sentence describing the round to players\n"
                    f"- \"challenge\": one creative constraint or challenge (e.g. 'Speed Rush: 45s', 'Single Stroke', 'Use only primary colors')\n"
                    f"- \"difficulty\": \"{diff}\""
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_text
                )

                if response and response.text:
                    cleaned = response.text.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        cleaned = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
                    data = json.loads(cleaned.strip())
                    return {
                        "word": data.get("word", "Cat"),
                        "category": selected_cat,
                        "prompt": data.get("prompt", f"Draw a {selected_cat} sketch!"),
                        "description": data.get("description", "Show your artistic skills!"),
                        "challenge": data.get("challenge", "Draw as fast as you can!"),
                        "difficulty": diff
                    }
            except Exception as e:
                logger.warning("Gemini API call failed (%s). Using dynamic fallback generator.", e)

        # Dynamic fallback selection
        candidates = FALLBACK_PROMPTS.get(selected_cat, FALLBACK_PROMPTS["Animal"])
        choice = random.choice(candidates).copy()
        choice["category"] = selected_cat
        choice["difficulty"] = diff
        return choice

    async def generate_round_commentary(
        self,
        word: str,
        category: str,
        drawer_name: str,
        ai_predicted: str,
        ai_matched: bool,
        guessed_count: int
    ) -> str:
        """Generates a witty 1-line round commentary / playful roast using Gemini or dynamic fallback."""
        if self.client:
            try:
                prompt_text = (
                    f"You are a witty, hilarious commentator for an online multiplayer drawing game.\n"
                    f"A round just ended with these details:\n"
                    f"- Secret word: '{word}' (Category: {category})\n"
                    f"- Drawer: '{drawer_name}'\n"
                    f"- ML AI model predicted: '{ai_predicted}' (Match: {ai_matched})\n"
                    f"- Players who successfully guessed: {guessed_count}\n"
                    f"Write ONE witty, playful commentary sentence (max 15 words) praising or playfully roasting the sketch with emojis!"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_text
                )
                if response and response.text:
                    return response.text.strip().replace('"', '')
            except Exception as e:
                logger.debug("Gemini commentary generation failed: %s", e)

        # Dynamic high-energy fallback commentary templates
        templates = [
            f"🎨 {drawer_name}'s {word} was pure modern art! Even the AI had to double-check. 😂",
            f"⚡ Incredible speed! That {word} sketch belonged in a digital museum.",
            f"🤖 AI thought it was '{ai_predicted}', but the squad cracked '{word}' anyway! 🕵️",
            f"🔥 Picasso in the room! {drawer_name}'s {word} brought home the points. 💯",
            f"🚀 {drawer_name} delivered the {word} masterpiece and the guessers didn't flinch! 🎉",
            f"✨ Look at that {word}! High style, high speed, and big brain guesses! 🏆"
        ]
        return random.choice(templates)

    async def generate_game_description(self, theme: Optional[str] = "Collaborative Drawing") -> str:
        """Generates a lively game description for the room lobby."""
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Generate a short, energetic 2-sentence description for an AI-enhanced multiplayer drawing game with theme '{theme}'."
                )
                if response and response.text:
                    return response.text.strip().replace('"', '')
            except Exception as e:
                logger.warning("Gemini description failed: %s", e)

        descriptions = [
            "Grab your digital brush and challenge your friends in real-time sketch battles powered by live AI category recognition!",
            "Fast strokes, witty guesses, and AI-powered round prompts. Step up to the canvas and prove your artistic prowess!",
            "Doodle against the clock! As you draw, our ML model tries to classify your sketch while your friends guess for points!"
        ]
        return random.choice(descriptions)


genai_service = GenAIService()

