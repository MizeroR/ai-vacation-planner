# AI Vacation Planner

A FastAPI backend for planning trips and managing itineraries with JWT authentication, LangChain tools, and a LangGraph travel-planning workflow.

---

## Architecture

```
app/
├── agents/
│   ├── graph.py      # LangGraph agent/tool workflow
│   └── state.py      # Shared planner state
├── main.py           # App entry point and router registration
├── config.py         # Environment-backed settings
├── database.py       # SQLAlchemy engine and sessions
├── models/           # User, Trip, and Itinerary ORM models
├── schemas/          # Pydantic request/response contracts
├── routers/          # Auth, trip, itinerary, user, and KB routes
├── services/
│   ├── knowledge.py  # Local semantic RAG knowledge base
│   ├── llm.py        # ChatAnthropic and structured output setup
│   ├── planner.py    # Planner orchestration boundary
│   ├── pricing.py    # Deterministic budget estimator
│   └── weather.py    # Open-Meteo integration
├── tools/
│   └── travel.py     # Weather, RAG, and pricing LangChain tools
└── core/
  ├── security.py   # Password hashing and JWT encode/decode
  └── dependencies.py  # Authenticated-user dependency
```

**Database:** SQLite (dev). Swap `DATABASE_URL` in `.env` for Postgres in production.  
**Auth:** JWT Bearer tokens. Include `Authorization: Bearer <token>` on protected routes.  
**LLM:** Claude through LangChain's Anthropic integration. LangGraph controls tool selection and execution.

---

## Setup

**Requirements:** Python 3.12+

```bash
# 1. Clone and enter the project
git clone https://github.com/MizeroR/ai-vacation-planner
cd ai-vacation-planner

# 2. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set a generated SECRET_KEY and your ANTHROPIC_API_KEY.

# 5. Run the server
uvicorn app.main:app --reload
```

The database tables are created automatically on first startup.

---

## API Docs

Interactive Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

---

## Endpoints

| Method | Path                     | Auth | Description                          |
| ------ | ------------------------ | ---- | ------------------------------------ |
| POST   | `/auth/register`         | No   | Register a new user                  |
| POST   | `/auth/login`            | No   | Login and get a JWT token            |
| GET    | `/users/me`              | Yes  | View your profile                    |
| POST   | `/trips`                 | Yes  | Create a trip                        |
| GET    | `/trips`                 | Yes  | List your trips                      |
| GET    | `/trips/{id}`            | Yes  | Get a single trip                    |
| PUT    | `/trips/{id}`            | Yes  | Update a trip                        |
| DELETE | `/trips/{id}`            | Yes  | Delete a trip                        |
| POST   | `/itineraries`           | Yes  | Create a manual itinerary for a trip |
| POST   | `/itineraries/generate`  | Yes  | Generate an AI itinerary for a trip  |
| GET    | `/itineraries/{trip_id}` | Yes  | Get a trip's itinerary               |

---

## Example Usage

**Register**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "username": "you", "password": "secret"}'
```

**Login**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "secret"}'
```

**Create a Trip**

```bash
curl -X POST http://localhost:8000/trips \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"destination": "Paris", "days": 5, "budget": 1500, "trip_style": "budget"}'
```

**Create an Itinerary**

```bash
curl -X POST http://localhost:8000/itineraries \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": 1,
    "days": [
      {"day": 1, "activities": ["Eiffel Tower", "Seine River Walk"]},
      {"day": 2, "activities": ["Louvre Museum", "Montmartre"]}
    ]
  }'
```

**Generate AI Itinerary**
```bash
curl -X POST http://localhost:8000/itineraries/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"trip_id": 1, "request": "Include weather-friendly activities and local food recommendations."}'
```

Response:
```json
{
  "trip_id": 1,
  "itinerary": [
    {
      "day": 1,
      "weather": "mostly clear",
      "activities": [
        {"name": "Eiffel Tower visit", "notes": "Go early to avoid queues"},
        {"name": "Seine River cruise", "notes": "Best near sunset"}
      ]
    },
    {
      "day": 2,
      "weather": "partly cloudy",
      "activities": [
        {"name": "Louvre Museum", "notes": "Book a timed entry"},
        {"name": "Montmartre walk", "notes": "Keep this lighter if rain is likely"}
      ]
    }
  ],
  "message": "Itinerary generated successfully by AI",
  "ai_generated": true
}
```

---

## LLM and Agent Integration

The backend uses Claude through LangChain and LangGraph to generate realistic, budget-conscious itineraries.

The generation flow is:

1. The authenticated user submits a `trip_id` and optional natural-language request.
2. The backend loads the user's trip details.
3. LangGraph gives the model access to approved travel tools.
4. The agent can call weather, internal travel knowledge, and budget-estimation tools.
5. Tool results are returned to the agent as messages.
6. A structured Claude model generates the final `ItineraryPlan`.
7. Pydantic validates the itinerary before it is saved.

### Available Tools

| Tool | Purpose |
| --- | --- |
| `get_destination_weather` | Retrieves available Open-Meteo forecast data. |
| `search_travel_knowledge` | Searches the local embedding-based travel knowledge base. |
| `estimate_travel_cost` | Estimates budget allocation by travel style. |

Weather and RAG failures return controlled unavailable results where possible. The agent also has a configurable maximum step count to prevent infinite tool loops.

### Environment Configuration

Create a root-level `.env` file. Keep it out of version control:

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
```

Use `.env.example` as the shareable template. Never commit real API keys.

## Knowledge Base (RAG)

This project includes a lightweight, file-backed Semantic Knowledge Base (KB) used to store travel guides, local tips, FAQs, and destination notes. The KB is embedded with `sentence-transformers` and searched with `scikit-learn` NearestNeighbors. The server retrieves relevant KB chunks and includes them in prompts sent to the LLM (Retrieval-Augmented Generation).

Files and endpoints:
- Service: `app/services/knowledge.py` — `kb.add_documents(docs)` and `kb.query(q, top_k)`
- Router: `POST /kb/seed` — seed/index documents (protected)
- Router: `GET /kb/query?q=...&k=3` — return top-k chunks (unprotected)

Seeding example (protected):

1. Register and login to get a token (see above). 2. Seed KB:

```bash
curl -X POST http://localhost:8000/kb/seed \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[{"id":"paris-guide","title":"Paris tips","text":"Arrive early to the Louvre..."}]'
```

Query example:

```bash
curl 'http://localhost:8000/kb/query?q=paris&k=3'
```

How it integrates:
- The knowledge base is exposed to the LangGraph workflow through `search_travel_knowledge`.
- Retrieved chunks and metadata are returned to the model as tool results.
- The final structured generation uses that context when it is relevant.

Live testing checklist
- Start server: `uvicorn app.main:app --reload`
- Register and login: get JWT token from `/auth/login`.
- Seed the KB using `/kb/seed` (protected) and verify `/kb/query` returns seeded chunks.
- Create a trip and call `/itineraries/generate` with an optional request to confirm the agent workflow succeeds.

Notes
- The KB stores embeddings and metadata under `data/kb/` by default. Do not commit large seeded data to the repository.
- Tests mock external model and provider calls so the suite does not require an API key or live network access.

## Testing

Tests are stored in the root-level `tests/` directory and cover schemas, tools, agent state, graph routing, planner orchestration, and reliability behavior.

Run the complete suite from the repository root:

```bash
pytest -q
```

The tests should be committed and pushed with the application. They document expected behavior and allow reviewers or CI to verify the Phase 5 implementation. Keep only secrets and local environment files, such as `.env`, out of version control.
