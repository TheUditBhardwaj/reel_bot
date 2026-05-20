# 🎬 ReelMind AI

**AI-powered Instagram Reel summarizer** — Send an Instagram Reel URL to a Telegram bot and get instant AI-generated summaries, key takeaways, and actionable insights.

Built with **FastAPI**, **Whisper**, **Mistral AI**, **PostgreSQL**, and **ChromaDB**.

---

## ✨ Features

- 🤖 **Telegram Bot** — Send a reel URL, get structured AI analysis
- 🔍 **Multi-Context Analysis** — Combines caption + transcript + metadata + hashtags
- 🎙 **Whisper Transcription** — Supports English & Hindi/Hinglish audio
- 🧠 **Mistral AI** — Generates titles, summaries, takeaways, and action items
- 🗄 **PostgreSQL** — Persistent storage with URL-based caching
- 📊 **ChromaDB** — Vector embeddings for future semantic search
- 📝 **Notion Sync** — Optional auto-sync to Notion database
- 🚀 **Railway Deploy** — Production-ready with Dockerfile

---

## 🏗 Architecture

```
Telegram User
     ↓ sends reel URL
Telegram Bot (python-telegram-bot)
     ↓ webhook / polling
FastAPI Backend
     ↓
┌──────────────────────────┐
│  Reel Extractor (yt-dlp) │ → caption, metadata, hashtags, audio
└──────────────────────────┘
     ↓
┌──────────────────────────┐
│  Whisper Transcriber     │ → audio → text transcript
└──────────────────────────┘
     ↓
┌──────────────────────────┐
│  Multi-Context Builder   │ → merges ALL sources into unified context
└──────────────────────────┘
     ↓
┌──────────────────────────┐
│  Mistral AI Analyzer     │ → structured JSON analysis
└──────────────────────────┘
     ↓
PostgreSQL + ChromaDB (storage)
     ↓
Telegram Reply + Optional Notion Sync
```

---

## 📁 Project Structure

```
reel_bot/
├── api/                  # FastAPI routes and schemas
│   ├── routes.py
│   └── schemas.py
├── bot/                  # Telegram bot handlers
│   ├── handlers.py
│   ├── formatter.py
│   └── polling.py        # Local dev polling mode
├── ai/                   # AI analysis pipeline
│   ├── analyzer.py       # Mistral AI client
│   ├── context_builder.py # Multi-context merger
│   └── prompts.py        # System/user prompts
├── extractor/            # Reel data extraction
│   └── reel_extractor.py # yt-dlp wrapper
├── transcriber/          # Audio transcription
│   └── whisper_service.py
├── database/             # PostgreSQL layer
│   ├── models.py         # SQLAlchemy ORM
│   ├── connection.py     # Async engine
│   └── crud.py           # CRUD operations
├── vector_store/         # ChromaDB embeddings
│   └── chroma_service.py
├── notion/               # Optional Notion sync
│   └── sync.py
├── utils/                # Shared utilities
│   ├── config.py         # Environment settings
│   ├── logger.py         # Structured logging
│   └── validators.py     # URL validation
├── main.py               # Application entrypoint
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/reel_bot.git
cd reel_bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
choco install ffmpeg
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required keys:**
- `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `MISTRAL_API_KEY` — from [Mistral Console](https://console.mistral.ai/)
- `DATABASE_URL` — PostgreSQL connection string

### 4. Run Locally (Polling Mode)

```bash
python -m bot.polling
```

### 5. Run with FastAPI (Webhook Mode)

```bash
uvicorn main:app --reload --port 8080
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/process-reel` | Process a reel URL |
| `GET` | `/api/reel/{id}` | Get processed reel |
| `POST` | `/webhook` | Telegram webhook |

### Example: Process a Reel

```bash
curl -X POST http://localhost:8080/api/process-reel \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/ABC123xyz/"}'
```

---

## 🚂 Railway Deployment

1. Push your code to GitHub
2. Create a new project on [Railway](https://railway.app)
3. Add a **PostgreSQL** database service
4. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `MISTRAL_API_KEY`
   - `DATABASE_URL` (auto-set by Railway)
   - `WEBHOOK_URL` = `https://your-app.railway.app`
   - `APP_ENV` = `production`
   - `WHISPER_MODEL` = `base`
5. Deploy — Railway uses the `Dockerfile` automatically

---

## 📊 Telegram Response Format

```
🎬 How to Build an AI App in 2025

📝 Summary:
The creator walks through building a full-stack AI application...

📋 Detailed Summary:
In this comprehensive tutorial, the creator demonstrates...

💡 Key Takeaways:
  • Start with a clear problem statement
  • Use FastAPI for the backend
  • Integrate Whisper for transcription

🛠 Tools Mentioned:
  🔧 FastAPI
  🔧 OpenAI Whisper
  🔧 Mistral AI

📂 Category: Tech

🏷 Keywords: #AI, #FastAPI, #Whisper, #Tutorial

🚀 Action Items:
  ✅ Set up a FastAPI project
  ✅ Integrate Whisper for audio processing
────────────────────
🤖 Powered by ReelMind AI
```

---

## 🔮 Future Roadmap

- [ ] YouTube Shorts support
- [ ] TikTok support
- [ ] LinkedIn video support
- [ ] Semantic search across all processed reels
- [ ] AI memory system (conversation context)
- [ ] Recommendation engine
- [ ] LangGraph workflow orchestration
- [ ] Multi-agent architecture

---

## 📄 License

MIT License

---

**Built with ❤️ by ReelMind AI**
