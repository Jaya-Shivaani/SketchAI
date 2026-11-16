# 🎨 AI-Enhanced Collaborative Drawing Game Platform

[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen.svg?logo=render&logoColor=white)](https://sketchai-idfq.onrender.com)
[![Demo Video](https://img.shields.io/badge/Demo%20Video-Google%20Drive-red.svg?logo=google-drive&logoColor=white)](https://drive.google.com/file/d/1fKyi-FXiVecvxO0b6gJg-sLDhskQXWq4/view?usp=sharing)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-KNN-orange.svg)](https://scikit-learn.org/)
[![Gemini](https://img.shields.io/badge/Gemini-LLM%20API-blueviolet.svg)](https://ai.google.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Async%20Motor-green.svg)](https://www.mongodb.com/)

> 🌐 **Live Cloud Deployment**: [https://sketchai-idfq.onrender.com](https://sketchai-idfq.onrender.com)  
> 🎥 **Walkthrough & Demo Video**: [Watch on Google Drive](https://drive.google.com/file/d/1fKyi-FXiVecvxO0b6gJg-sLDhskQXWq4/view?usp=sharing)  
> *Experience real-time collaborative sketch guessing with live ML classification directly in your browser without local installation!*

A real-time multiplayer drawing and guessing game platform powered by **Machine Learning (K-Nearest Neighbors)** for live sketch classification and **Generative AI (Google Gemini LLM)** for dynamic prompt generation and creative game challenges.

---

## 🌟 Key Features

1. **User Authentication & Profiles**:
   - Secure registration and login with **Bcrypt** password hashing.
   - Stateless **JWT (JSON Web Token)** bearer authentication.
   - Persistent user statistics: total score, games played, victories, and correct guesses.

2. **Multiplayer Game Rooms**:
   - Create or join rooms using unique 6-character room codes (e.g., `SKETCH`).
   - Customizable room parameters: Category themes (Animal, Food, Vehicle, Nature, Object, or Random), AI difficulty, round counts, and duration.
   - Real-time player roster synchronization.

3. **Real-Time Drawing Canvas**:
   - Smooth 60fps HTML5 Canvas with normalized 500x500 virtual coordinate space.
   - Drawing tools: Brush, Eraser, stroke size slider (2px - 32px), color palette swatches, and custom hex color picker.
   - Instant stroke streaming to all players in the room via native WebSockets.
   - Toolbar is interactively enabled for the active Drawer and locked for Guessers.

4. **Live Machine Learning Sketch Classifier (scikit-learn KNN)**:
   - Real-time classification into 5 distinct categories: **Animal**, **Object**, **Food**, **Vehicle**, and **Nature**.
   - 77-dimensional feature extraction: stroke count, bounding box dimensions, aspect ratio, Euclidean path length, curvature, 8-bin orientation histograms, and 7x7 spatial pooling.
   - Live AI confidence badge (e.g. `AI thinks this is: Animal (94%)`) updating as players draw.
   - Backend exposes `POST /predict` and `POST /api/game/predict` endpoints.

5. **Generative AI Game Master (Google Gemini API)**:
   - Dynamic prompt generator tailoring target words, drawer instructions, witty round descriptions, and creative challenges (e.g., *"Speed Rush: 45s!"*, *"Single continuous line"*).
   - Graceful fallback generator ensures 100% uptime even when offline or before configuring API keys.

6. **Intelligent Guess Submission & Scoring**:
   - Integrated live chat with automatic correct guess detection.
   - Time-weighted scoring: $100 \text{ base} + \text{remaining time} \times 2$ for guessers, and $+50$ bonus points for the drawer.
   - Anti-spoiler chat masking: hides the secret word from active guessers while celebrating winners.

7. **Round Rotation & Synchronized Timer**:
   - Turn-based drawer rotation across players.
   - Server-synchronized 1-second countdown loop with visual warning states.
   - Round intermission summary overlay revealing the secret word, scores, and AI prediction accuracy.

8. **Player Dashboard & Global Leaderboard**:
   - Personal stats overview: Total score, games won, win rate, correct guesses.
   - Global Leaderboard with gold/silver/bronze rank badges.
   - Complete past match history log stored in MongoDB.

---

## 🛠️ Tech Stack

- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+ Modules, no frameworks).
- **Backend**: FastAPI (Python 3.13), Uvicorn, native WebSockets.
- **Database**: MongoDB with `motor` (async driver) and `pymongo`.
- **Machine Learning**: `scikit-learn` (KNeighborsClassifier), `numpy`, `joblib`.
- **Generative AI**: Google Gemini API (`google-genai`).

---

## 📂 Project Directory Structure

```text
ProjectRoot/
├── Backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py             # Settings, env vars, JWT secrets, model paths
│   │   ├── database.py           # Async MongoDB connection (Motor) & repository
│   │   ├── auth.py               # Bcrypt password hashing & JWT handling
│   │   ├── models.py             # Pydantic schemas (Users, Rooms, ML, GenAI)
│   │   ├── websocket_manager.py  # Real-time room manager, turns, timer, scoring
│   │   ├── ml_service.py         # KNN model loader & feature extraction inference
│   │   ├── genai_service.py      # Gemini API prompt & challenge generator
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth_routes.py    # /api/auth/register, /api/auth/login, /api/auth/me
│   │       ├── room_routes.py    # /api/rooms/create, /api/rooms/join, /api/rooms/list
│   │       ├── game_routes.py    # /api/game/predict, /api/game/prompt, /api/game/history
│   │       └── ws_routes.py      # /ws/room/{room_code} (WebSocket endpoint)
│   └── main.py                   # FastAPI application entry point & static file mount
├── Frontend/
│   ├── index.html                # Lobby page, user auth modals, room create/join
│   ├── game.html                 # Multiplayer room (Canvas, Toolbar, Guess Chat, AI badge)
│   ├── dashboard.html            # Profile, game history, global leaderboard
│   ├── css/
│   │   ├── styles.css            # Global modern gaming theme, buttons, modals
│   │   ├── game.css              # Canvas, drawing toolbar, guess log, timer
│   │   └── dashboard.css         # Stats cards, history table, leaderboard podium
│   └── js/
│       ├── api.js                # REST API client & toast notifications
│       ├── auth.js               # Auth state persistence & login/register forms
│       ├── canvas.js             # Canvas drawing engine & stroke serialization
│       ├── websocket.js          # Resilient WebSocket client & message routing
│       ├── game.js               # Game loop, timer, turns, guesses, AI badge
│       └── dashboard.js          # User stats and leaderboard rendering
├── ML/
│   ├── dataset/
│   │   ├── quickdraw_sampled.npz # 2,000 balanced sketches across 5 categories
│   │   └── dataset_metadata.json # Metadata and category mappings
│   ├── saved_models/
│   │   ├── knn_drawing_model.joblib # Trained KNeighborsClassifier model
│   │   ├── scaler.joblib         # StandardScaler artifact
│   │   ├── label_encoder.joblib  # Category label encoder
│   │   └── evaluation_report.json# Test metrics and confusion matrix
│   ├── feature_extraction.py     # 77-dim feature extraction pipeline
│   ├── generate_dataset.py       # Dataset collection and synthesis script
│   ├── train_model.py            # Model training & hyperparameter grid search
│   ├── evaluate_model.py         # Standalone model evaluation script
│   └── drawing_classification_knn.ipynb # Comprehensive Jupyter Notebook
├── DOCUMENTATION.md              # In-depth architectural documentation (Word/PDF ready)
├── README.md                     # Project overview and setup guide
├── requirements.txt              # Complete Python dependencies
└── .env.example                  # Environment configuration template
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **MongoDB**: Running locally at `mongodb://localhost:27017` (or MongoDB Atlas URI).
- **Gemini API Key**: (Optional) Get a free key from [Google AI Studio](https://aistudio.google.com/).

### 2. Installation
Clone or navigate to the project root directory:

```bash
cd d:/Gradious
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Open `.env` and configure your settings (or use pre-configured defaults):
```ini
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=drawing_game_db
JWT_SECRET=sketchai-jwt-secret-key-collaborative-game-2026
GEMINI_API_KEY=your_optional_gemini_api_key_here
```
*(Note: `GEMINI_API_KEY` is optional; if omitted, the game automatically uses the built-in dynamic prompt fallback generator).*

### 4. Running the Machine Learning Pipeline (Optional / Retrain)
The trained model artifacts (`knn_drawing_model.joblib`, `scaler.joblib`) are already bundled in `ML/saved_models/`. To retrain or evaluate:

```bash
# Retrain the model
python ML/train_model.py

# Evaluate test metrics and confusion matrix
python ML/evaluate_model.py

# Launch the interactive Jupyter Notebook
jupyter lab ML/drawing_classification_knn.ipynb
```

### 5. Running the Application

#### 🌐 Option 0: Instant Cloud Access & Demo Video (Zero Installation)
The full stack application is deployed live in production on Render:
- **Live Game App**: [https://sketchai-idfq.onrender.com](https://sketchai-idfq.onrender.com)
- **Live Swagger API Docs**: [https://sketchai-idfq.onrender.com/docs](https://sketchai-idfq.onrender.com/docs)
- **Project Walkthrough & Demo Video**: [Watch Demo Video on Google Drive](https://drive.google.com/file/d/1fKyi-FXiVecvxO0b6gJg-sLDhskQXWq4/view?usp=sharing)
- **Status**: Active 24/7 with WebSocket multiplayer streaming, in-memory resilient fallback, and scikit-learn ML inference.

---

The platform also includes **zero-friction local startup scripts** designed so any mentor or evaluator can run the application with **a single command or double-click**:

#### 🌟 Option 1: One-Click Startup (Recommended for Mentors / Windows)
Simply double-click **`run.bat`** in the project folder, or run in your terminal:
```bash
.\run.bat
```
*(This smart batch script automatically detects virtual environments `D:\env`, local `venv/`, Python launcher `py`, and standard Python installations without requiring manual PATH configuration).*

---

#### 🐍 Option 2: Universal Python Command
If you have Python in your environment:
```bash
# Standard Python command
python Backend/main.py

# Or run the root orchestrator
python run.py

# Or using Python Launcher (Windows)
py Backend/main.py
```

---

#### 📦 Option 3: Using the Project Virtual Environment Directly (PowerShell)
```powershell
& "D:\env\Scripts\python.exe" Backend/main.py
```

---

Once started, open your web browser and navigate to:
👉 **`http://localhost:8000`** (or `http://127.0.0.1:8000`)

To access the interactive API docs:
👉 **`http://localhost:8000/docs`**

---

## 🎮 How to Play

1. Open **`http://localhost:8000/`** in your browser.
2. Sign up or log in (or enter as a guest).
3. **Create a Room** (choose category and rounds) or enter a **Room Code** to join.
4. Open a second browser tab (or incognito window) with the same Room Code to simulate a second player.
5. In the first tab, click **▶ Start Game**.
6. The **Drawer** receives a secret word and creative AI prompt:
   - Draw on the canvas using the brush, eraser, and color palette.
   - Watch the **AI Category Prediction** badge guess the category in real time!
7. The **Guesser** sees the live strokes appear instantly:
   - Type guesses into the chat box on the right.
   - Guess correctly to earn points!
8. View cumulative statistics and global leaderboard rankings on the **Dashboard** (`/dashboard`).

---

## 📊 Machine Learning Model Details

- **Algorithm**: `KNeighborsClassifier` ($k=7$, Euclidean distance, Uniform weights).
- **Categories**: `Animal`, `Object`, `Food`, `Vehicle`, `Nature`.
- **Feature Vector**: 77 extracted features (geometric dimensions, path lengths, aspect ratio, curvature, 8-bin orientation histogram, and 7x7 spatial density pooling).
- **Performance**:
  - Test Accuracy: **100.0%**
  - Macro F1-Score: **1.00**
  - Average Inference Time: **< 2ms** per stroke batch.

---

## 📄 Documentation
For detailed system architecture, sequence diagrams, and mathematical formulation of features, see [`DOCUMENTATION.md`](DOCUMENTATION.md).

