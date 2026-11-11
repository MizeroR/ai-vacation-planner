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

### LLM integration

The planner gathers bounded context from local weather, knowledge-base, and
budget tools, with external MCP tools available when configured. It then asks
the configured Anthropic model to return an `ItineraryPlan`; invalid or
unavailable model responses fail the generation request rather than being
saved as a successful itinerary. Configure the Anthropic model and token limit
through `ANTHROPIC_MODEL` and `ANTHROPIC_MAX_TOKENS`.
Requests leave sampling temperature unset because current Anthropic models
may reject that parameter; the selected model uses its default behavior.

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
ANTHROPIC_MODEL=claude-haiku-5-5
ANTHROPIC_MAX_TOKENS=1200
AGENT_MAX_STEPS=4
EXTERNAL_REQUEST_TIMEOUT_SECONDS=10
STT_MODEL=small
TTS_ENGINE=pyttsx3
TTS_VOICE=
MAX_AUDIO_UPLOAD_BYTES=25000000
MAX_IMAGE_UPLOAD_BYTES=10000000
MCP_SERVER_URL=
DATADOG_ENABLED=false
DATADOG_SERVICE=ai-vacation-planner
DATADOG_ENV=development
DD_AGENT_HOST=localhost
DD_TRACE_AGENT_PORT=8126
DD_DOGSTATSD_PORT=8125
```

Notes:
- `MCP_SERVER_URL` is optional. If empty, the app uses only its built-in local tools.
- Datadog tracing and metrics are disabled by default. To enable them, set `DATADOG_ENABLED=true` and configure the Datadog Agent host and ports above before starting the API.
- Local speech features rely on `faster-whisper` and `pyttsx3` and work without internet access.
- The app is designed to run on Python 3.12 in the pinned environment used for the project.

### Datadog signals

When enabled, the API reports request duration, status, and route; itinerary
generation duration and outcome; LLM model, phase, and token counts when the
provider returns usage metadata; and travel-tool calls and unavailable/invalid
results. These are emitted as APM spans and DogStatsD metrics, including:

- `vacation_planner.http.requests` and `vacation_planner.http.request.duration`
- `vacation_planner.generations` and `vacation_planner.generation.duration`
- `vacation_planner.llm.calls` and `vacation_planner.llm.tokens`
- `vacation_planner.tools.calls` and `vacation_planner.tools.errors`

Only route templates and bounded operational labels are used as metric tags.
Request IDs are included on spans and returned in the `X-Request-ID` response
header. Prompts, user identifiers, and API credentials are not sent as
observability attributes.

An importable dashboard definition is provided at
[`observability/datadog-dashboard.json`](./observability/datadog-dashboard.json).
Import it from Datadog's dashboard import flow after enabling instrumentation
and sending metrics to a Datadog Agent. Its environment and service filters
default to `development` and `ai-vacation-planner`; update them if your
deployment uses different values. The dashboard will remain empty until the
Agent receives data from the application.

#### Verify Datadog locally on macOS

Use either the native Datadog Agent or a Docker-compatible runtime. Docker
Desktop requires a supported macOS version; Colima on macOS versions earlier
than 13 requires QEMU. The Docker route also requires the Docker Compose v2
plugin.

For Docker, enter the Datadog API key at the hidden prompt. It is passed to the
Agent as an environment variable and is not stored in the repository:

```bash
read -s "DD_API_KEY?Datadog API key: "
echo
export DD_API_KEY
export DD_SITE=datadoghq.com
docker compose -f observability/docker-compose.datadog.yml up -d
unset DD_API_KEY
docker exec ai-vacation-planner-datadog-agent agent status
```

For the native macOS Agent, install the Datadog Agent package and configure
`api_key` and `site: datadoghq.com` locally in
`/opt/datadog-agent/etc/datadog.yaml`. Do not put the key in the application
`.env`, commit it, or send it in chat. Start or restart the Agent using the
Datadog Agent app or its `datadog-agent` command.

In the local, untracked `.env`, set `DATADOG_ENABLED=true`,
`DATADOG_SERVICE=ai-vacation-planner`, `DATADOG_ENV=development`,
`DD_AGENT_HOST=127.0.0.1`, `DD_TRACE_AGENT_PORT=8126`, and
`DD_DOGSTATSD_PORT=8125`. Restart the API, call `GET /`, make an unauthenticated
request to verify failed-request metrics, and generate one itinerary to emit
LLM and generation metrics. These actions can send live Anthropic requests.
Never put the Datadog API key in the application `.env` or commit it.

After allowing a few minutes for ingestion, find
`vacation_planner.http.requests` in Metrics Explorer and
`ai-vacation-planner` in APM. Import the dashboard JSON, use the `development`
and `ai-vacation-planner` filters, and verify the HTTP and latency widgets
display data. Capture screenshots of the populated dashboard and a representative
trace for submission, with secrets and personal information excluded. Stop the
Docker Agent when finished with
`docker compose -f observability/docker-compose.datadog.yml down`.

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

The regular suite uses mocked provider and tool responses for deterministic,
offline checks. It covers API behavior, schema validation, planner outcomes,
and observability instrumentation. The live DeepEval run described below is
opt-in and is not part of `pytest`.

## Security and guardrails

- Protected API operations use JWT authentication; trip and itinerary access
  checks ownership against the authenticated user.
- Passwords are stored as bcrypt hashes. Keep `SECRET_KEY` and
  `ANTHROPIC_API_KEY` in local environment configuration and out of version
  control.
- Generated itineraries are validated for the requested trip duration,
  sequential day numbering, 3–5 activities per day, and nonblank activity
  names before they are saved.
- The planner's tool loop is bounded by `AGENT_MAX_STEPS`. External requests
  are bounded by request timeouts where supported, and unavailable tool
  results do not become fabricated facts in the final itinerary.
- Voice and image uploads have configurable size limits. Set these limits
  appropriately for the deployment.
- Observability emits operational metadata only: prompts, user identifiers,
  and credentials are excluded from span attributes and metric tags.

### AI evaluation and golden dataset

The versioned golden cases are in
[`evaluations/datasets/itinerary_goldens.json`](./evaluations/datasets/itinerary_goldens.json).
They cover varied destinations, durations, budgets, travel styles, and user
preferences. The regular pytest suite validates dataset structure and tests the
planner deterministically with mocked model responses; it does not make live
LLM calls.

Run DeepEval in a separate environment because its current Pydantic and MCP
requirements are newer than the application's pinned runtime stack:

```bash
python3.12 -m venv .venv-eval
source .venv-eval/bin/activate
pip install -r requirements.txt
pip install -r requirements-evaluation.txt
python -m evaluations.run_deepeval
```

For a lower-cost live smoke run, evaluate a single golden case first:

```bash
python -m evaluations.run_deepeval --case-id paris-budget-museums
```

The evaluation uses the configured Anthropic model to generate each itinerary
and to judge it with DeepEval G-Eval. The Anthropic judge requires a complete
JSON score and reason; if its first response is malformed, the runner requests
one corrected response and then reports a clear error if it remains invalid.
Set `ANTHROPIC_API_KEY` in `.env` first.
Each generated itinerary is checked against the application’s Pydantic schema
and trip duration before the quality judge runs. A case passes at a G-Eval
score of 0.70 or higher; the command exits nonzero if any case fails. This
evaluation makes live provider calls and may incur API cost, so it is kept
separate from ordinary tests.

---

## Notes

- The local speech stack is intentionally dependency-light and offline-friendly.
- The MCP integration is optional and does not block local planner behavior when no server is configured.
- Avoid checking in real API keys, database files, or generated media outputs.
- The test suite is committed with the project and validates the expected behavior for the planner, speech, TTS, images, and MCP flows.
