# AI Vacation Planner

A FastAPI-based travel-planning backend with JWT auth, LangGraph tool use, structured itinerary generation, and optional multimodal inputs/outputs. It supports local voice transcription, local text-to-speech playback, image analysis, and optional external MCP tool integrations.

---

## Final Architecture

```text
app/
├── agents/
│   ├── graph.py      # LangGraph orchestration and tool routing
│   └── state.py      # Planner state contract for trip/context/tool results
├── core/
│   ├── dependencies.py  # Authenticated-user dependency
│   └── security.py      # JWT and password helpers
├── models/
│   ├── itinerary.py
│   ├── trip.py
│   └── user.py
├── routers/
│   ├── auth.py
│   ├── itineraries.py
│   ├── kb.py
│   ├── trips.py
│   └── users.py
├── schemas/
│   ├── itinerary.py
│   ├── media.py
│   ├── trip.py
│   └── user.py
├── services/
│   ├── image.py      # Vision-based image analysis for trip photos
│   ├── knowledge.py  # Local semantic travel knowledge base
│   ├── llm.py        # Anthropic chat and structured itinerary generation
│   ├── mcp.py        # Optional external MCP client adapter
│   ├── planner.py    # Planner orchestration boundary
│   ├── pricing.py    # Deterministic budget estimator
│   ├── speech.py     # Local STT using faster-whisper
│   ├── tts.py        # Local TTS generation using pyttsx3
│   └── weather.py    # Open-Meteo forecast lookups
├── tools/
│   └── travel.py     # LangChain tools for weather, knowledge, pricing, and MCP calls
├── config.py         # Environment-backed settings
├── database.py       # SQLAlchemy engine and session factory
├── main.py           # App bootstrap and router registration
├── __init__.py
└── ...
```

### Core stack
- FastAPI for HTTP APIs
- SQLAlchemy + SQLite for persistence
- Pydantic models for validation and schema contracts
- LangChain + LangGraph for tool-using planner orchestration
- Anthropic Claude for structured trip planning and image analysis
- Local Python services for STT/TTS and optional MCP tool access

### Runtime flow
1. Authenticated users create or update a trip.
2. The planner graph decides whether to call local travel tools or an external MCP tool.
3. Weather, pricing, knowledge-base, and MCP tool results are bundled back into the model context.
4. Claude returns a structured itinerary plan that is validated before saving.
5. Users can also upload voice or image files for natural multimodal trip input.

---

## Setup

Requirements: Python 3.12+

```bash
# 1. Clone and enter the project
git clone https://github.com/MizeroR/ai-vacation-planner
cd ai-vacation-planner

# 2. Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your environment
cp .env.example .env
# Edit .env and set your SECRET_KEY, ANTHROPIC_API_KEY, and any optional MCP settings.

# 5. Run the API
uvicorn app.main:app --reload
```

The database tables are created automatically on first startup.

---

## Environment configuration

Use `.env.example` as the baseline template. Keep real secrets out of version control.

```env
DATABASE_URL=sqlite:///./vacation_planner.db
SECRET_KEY=replace-with-a-generated-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=replace-with-your-anthropic-key
ANTHROPIC_MODEL=claude-3-5-haiku-latest
ANTHROPIC_MAX_TOKENS=1200
ANTHROPIC_TEMPERATURE=0.0
AGENT_MAX_STEPS=4
EXTERNAL_REQUEST_TIMEOUT_SECONDS=10
STT_MODEL=small
TTS_ENGINE=pyttsx3
TTS_VOICE=
MAX_AUDIO_UPLOAD_BYTES=25000000
MAX_IMAGE_UPLOAD_BYTES=10000000
MCP_SERVER_URL=
```

Notes:
- `MCP_SERVER_URL` is optional. If empty, the app uses only its built-in local tools.
- Local speech features rely on `faster-whisper` and `pyttsx3` and work without internet access.
- The app is designed to run on Python 3.12 in the pinned environment used for the project.

---

## API docs

Interactive Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

---

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | No | Register a new user |
| POST | `/auth/login` | No | Login and receive a JWT token |
| GET | `/users/me` | Yes | View the authenticated user |
| POST | `/trips` | Yes | Create a trip |
| GET | `/trips` | Yes | List trips for the user |
| GET | `/trips/{trip_id}` | Yes | Retrieve a trip |
| PUT | `/trips/{trip_id}` | Yes | Update a trip |
| DELETE | `/trips/{trip_id}` | Yes | Delete a trip |
| POST | `/trips/{trip_id}/voice` | Yes | Upload audio and transcribe it |
| POST | `/trips/{trip_id}/voice/response` | Yes | Convert text into spoken audio output |
| POST | `/trips/{trip_id}/image` | Yes | Upload an image and analyze it for travel context |
| POST | `/itineraries` | Yes | Create a manual itinerary |
| POST | `/itineraries/generate` | Yes | Generate an AI trip itinerary |
| GET | `/itineraries/{trip_id}` | Yes | Fetch an itinerary for a trip |
| POST | `/kb/seed` | Protected | Seed the local knowledge base |
| GET | `/kb/query` | No | Query local travel knowledge |

---

## Example usage

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "username": "you", "password": "secret"}'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "secret"}'
```

### Create a trip

```bash
curl -X POST http://localhost:8000/trips \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"destination": "Paris", "days": 5, "budget": 1500, "trip_style": "budget"}'
```

### Generate an itinerary

```bash
curl -X POST http://localhost:8000/itineraries/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"trip_id": 1, "request": "Include weather-friendly activities and local food recommendations."}'
```

### Upload voice for transcription

```bash
curl -X POST http://localhost:8000/trips/1/voice \
  -H "Authorization: Bearer <token>" \
  -F "file=@voice-note.wav" \
  -F "request=Plan my trip around museums and food stops"
```

Example response:

```json
{
  "text": "Plan my trip around museums and food stops",
  "language": "en"
}
```

### Generate spoken audio for itinerary text

```bash
curl -X POST http://localhost:8000/trips/1/voice/response \
  -H "Authorization: Bearer <token>" \
  -F "text=Welcome to Paris. Your itinerary includes the Louvre, Montmartre, and a Seine river walk."
```

Example response:

```json
{
  "media_type": "audio/mpeg",
  "filename": "speech-9d0a...mp3"
}
```

### Upload an image for travel analysis

```bash
curl -X POST http://localhost:8000/trips/1/image \
  -H "Authorization: Bearer <token>" \
  -F "file=@photo.jpg" \
  -F "request=Describe the view and suggest activities"
```

Example response:

```json
{
  "description": "A scenic harbor town with colorful buildings and bright blue water.",
  "destination": "Amalfi",
  "activities": ["harbor stroll", "boat ride", "cafe stop"]
}
```

---

## Planner and tool system

The itinerary planner uses a LangGraph workflow with a bounded tool loop.

### Local tools
| Tool | Purpose |
| --- | --- |
| `get_destination_weather` | Fetch Open-Meteo forecast data for a destination |
| `search_travel_knowledge` | Query the semantic local KB |
| `estimate_travel_cost` | Estimate how a trip budget should be spread |
| `call_external_mcp_tool` | Call an optional external MCP tool if configured |

The planner keeps tool calls bounded with `AGENT_MAX_STEPS` to prevent infinite loops. Tool failures return explicit `status: unavailable` or `status: invalid` payloads instead of crashing the planner.

### External MCP integration

The app can optionally connect to an external MCP server by setting `MCP_SERVER_URL` in `.env`.

When configured, the server can expose tools beyond the built-in local set, and the travel tool wrapper calls them through the configured MCP client adapter. This keeps the application modular while preserving a local fallback path when no MCP server is configured.

---

## Knowledge Base (RAG)

The application includes a lightweight, file-backed knowledge base for destination notes, travel tips, and itinerary guidance. It is embedded with `sentence-transformers` and retrieved with `scikit-learn` nearest-neighbor search.

Files and routes:
- Service: `app/services/knowledge.py`
- Router: `POST /kb/seed`
- Router: `GET /kb/query?q=...&k=3`

Example seed request:

```bash
curl -X POST http://localhost:8000/kb/seed \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[{"id":"paris-guide","title":"Paris tips","text":"Arrive early to the Louvre..."}]'
```

Example query request:

```bash
curl 'http://localhost:8000/kb/query?q=paris&k=3'
```

This local KB is included in the planner prompt context when it is relevant, improving the quality and specificity of generated itineraries.

---

## Testing

The repository includes tests covering schemas, travel tools, planner orchestration, speech flow, TTS flow, image upload analysis, and MCP tool integration.

Run the full suite from the project root:

```bash
.venv312/bin/python -m pytest -q
```

The project was validated against the Python 3.12 environment used in this repository, which is the supported configuration for the current dependency stack.

---

## Notes

- The local speech stack is intentionally dependency-light and offline-friendly.
- The MCP integration is optional and does not block local planner behavior when no server is configured.
- Avoid checking in real API keys, database files, or generated media outputs.
- The test suite is committed with the project and validates the expected behavior for the planner, speech, TTS, images, and MCP flows.
