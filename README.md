# AI Vacation Planner

A FastAPI backend for planning trips and managing itineraries with JWT authentication.

---

## Architecture

```
app/
├── main.py           # App entry point — registers routers and creates DB tables
├── config.py         # Reads environment variables via pydantic-settings
├── database.py       # SQLAlchemy engine, session factory, and Base class
├── models/           # ORM table definitions (User, Trip, Itinerary)
├── schemas/          # Pydantic request/response shapes
├── routers/          # Route handlers grouped by domain
├── services/         # Business logic — LLM integration
└── core/
    ├── security.py   # Password hashing and JWT encode/decode
    └── dependencies.py  # get_current_user dependency (token → User)
```

**Database:** SQLite (dev). Swap `DATABASE_URL` in `.env` for Postgres in production.  
**Auth:** JWT Bearer tokens. Include `Authorization: Bearer <token>` on protected routes.  
**LLM:** Claude API (Anthropic) for AI-powered itinerary generation.

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
# Edit .env and set:
#  - SECRET_KEY: a strong random string
#  - ANTHROPIC_API_KEY: get from https://console.anthropic.com

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
  -d '{"trip_id": 1}'
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

## LLM Integration

The backend uses **Claude (Anthropic's LLM)** to generate realistic, budget-conscious itineraries.

**How it works:**

1. User calls `POST /itineraries/generate` with just the `trip_id`
2. Backend fetches trip details (destination, days, budget, style) from the database
3. A detailed prompt is sent to Claude:
  - Trip context (destination, days, budget)
  - Weather context from a lightweight Open-Meteo lookup
  - Constraints (stay within destination area, respect budget)
  - Requirements (3-5 activities per day, include meals/rest)
4. Claude generates structured JSON with `days`, `weather`, and nested activity objects
5. The backend validates the response with Pydantic, retries on invalid output, and saves only validated data to the database

**Prompt Strategy:**

The prompt includes:
- Clear trip context (destination, duration, budget constraints)
- Guidelines to focus activities within the destination
- Travel style consideration (budget, luxury, adventure, etc.)
- Structured JSON output requirement to ensure parseable response
- No plaintext instructions outside the JSON to avoid parsing errors

**Setup:**

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. Add it to your `.env` file: `ANTHROPIC_API_KEY=sk-ant-...`
3. The system uses Claude 3.5 Sonnet for cost-effective, high-quality itineraries

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
- When generating an AI itinerary the server calls `kb.query(destination, top_k=3)` and appends the returned chunk texts to the LLM prompt under a `Travel knowledge` section. This gives Claude factual local context to improve suggestions.

Live testing checklist
- Start server: `uvicorn app.main:app --reload`
- Register and login: get JWT token from `/auth/login`.
- Seed the KB using `/kb/seed` (protected) and verify `/kb/query` returns seeded chunks.
- Create a trip and call `/itineraries/generate` to confirm the LLM call succeeds and includes KB context in prompt.

Notes
- The KB stores embeddings and metadata under `data/kb/` by default. Do not commit large seeded data to the repository.
- In tests and CI, mock `SentenceTransformer.encode` and the Anthropic client to make runs fast and deterministic.
