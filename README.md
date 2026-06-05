# GLSClass Orchestrator

A lightweight Python microservice that acts as an **intent-classification orchestrator**.  
It receives natural-language requests from users, identifies the correct downstream service using **GLiClass** (a local HuggingFace zero-shot classifier — no API key required), extracts all required data, and returns a ready-to-forward payload — or a structured fallback asking the user for missing information.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Service Classes](#service-classes)
3. [API Reference](#api-reference)
   - [POST /api/v1/classify](#post-apiv1classify)
   - [POST /api/v1/classes/register](#post-apiv1classesregister)
   - [GET /api/v1/classes](#get-apiv1classes)
   - [GET /health](#get-health)
4. [Missing-Fields Flow](#missing-fields-flow)
5. [Running Without Docker](#running-without-docker)
6. [Running With Docker](#running-with-docker)
7. [Environment Variables Reference](#environment-variables-reference)
8. [Extending the Service](#extending-the-service)

---

## Architecture Overview

```
User / Frontend
      │
      ▼
 Backend Server
      │
      │  POST /api/v1/classify
      ▼
┌──────────────────────────────────────┐
│       GLSClass Orchestrator          │
│                                      │
│  1. GLiClass zero-shot classifier    │  ← local HuggingFace model (no API key)
│     (knowledgator/gliclass-small-v1.0│    loaded once at startup
│      or any model set in .env)       │
│  2. Field extractor                  │
│  3. Required-field checker           │
└──────────────┬───────────────────────┘
               │
      ┌────────┴────────┐
      │  All fields     │  No  ──►  HTTP 422  MissingFieldsResponse
      │  present?       │           (backend asks user for more data)
      └────────┬────────┘
               │ Yes
               ▼
           HTTP 200  ClassifyResponse
           (includes downstream_url + downstream_payload)
               │
               ▼
      Backend forwards to the correct downstream service
```

The orchestrator **never** calls downstream services directly — it only classifies and routes.  
Your backend reads `downstream_url` and `downstream_payload` from the `200` response and makes that call itself.

### Model loading

The GLiClass model is downloaded from HuggingFace on first startup and cached locally.  
Subsequent restarts reuse the cache (no re-download). In Docker, mount the `hf_cache` volume (included in `docker-compose.yml`) to persist it across container rebuilds.

---

## Service Classes

| Class | Description | Required Fields | Optional Fields |
|---|---|---|---|
| `summary` | Generate a lecture summary | `lecture` | — |
| `mcq` | Generate multiple-choice questions | `lecture` | `num_questions` |
| `flashcard` | Generate study flash-cards | `lecture` | `num_cards` |
| `tts` | Text-to-speech conversion | `lecture` | `voice`, `speed` |
| `plan` | Generate a study plan (no lecture needed) | `start_date`, `end_date` | `topics`, `hours_per_day` |
| `rag` | Fallback — answer via knowledge base | `query` | — |

> **Fallback rule**: if the classifier score is below the threshold for every class, the service automatically selects `rag` and sets `query` from the user message.

---

## API Reference

### `POST /api/v1/classify`

**User-facing endpoint.** Classifies a natural-language request.

#### Request body

```json
{
  "user_message": "Can you summarize lecture 3 for me?",
  "context": {
    "lecture": "In this lecture we covered neural networks and backpropagation…"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `user_message` | string | ✅ | Raw user input |
| `context` | object | ❌ | Structured data already collected by the backend (lecture text, dates, etc.) |

#### Response `200 OK` — all fields present

```json
{
  "status": "classified",
  "detected_class": "summary",
  "confidence": 0.9312,
  "extracted_data": {
    "lecture": "In this lecture we covered neural networks…"
  },
  "downstream_payload": {
    "lecture": "In this lecture we covered neural networks…"
  },
  "downstream_url": "http://summary-service:8001"
}
```

#### Response `422 Unprocessable Entity` — missing fields

```json
{
  "status": "missing_fields",
  "detected_class": "summary",
  "missing_fields": ["lecture"],
  "prompt_message": "To generate a summary, I need a bit more information. Please provide the lecture content you'd like to work with."
}
```

The backend should relay `prompt_message` to the user, collect the missing data, then retry the request with the gathered values placed inside the `context` object.

---

### `POST /api/v1/classes/register`

**Admin endpoint.** Register a new service class or update an existing one at runtime (no restart needed).

#### Request body

```json
{
  "name": "quiz",
  "description": "Generate a graded quiz from lecture content.",
  "required_fields": ["lecture"],
  "optional_fields": ["num_questions", "difficulty"]
}
```

#### Response `200 OK`

```json
{
  "success": true,
  "message": "Class 'quiz' registered successfully.",
  "classes": ["summary", "mcq", "flashcard", "tts", "plan", "rag", "quiz"]
}
```

---

### `GET /api/v1/classes`

Returns the full list of currently registered class definitions.

#### Response `200 OK`

```json
[
  {
    "name": "summary",
    "description": "Generate a concise summary of a lecture…",
    "required_fields": ["lecture"],
    "optional_fields": []
  }
]
```

---

### `GET /health`

Returns service liveness status.

#### Response `200 OK`

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Missing-Fields Flow

```
Frontend                 Backend               GLSClass Orchestrator
   │                        │                          │
   │─ "Summarize it" ──────►│                          │
   │                        │── POST /classify ────────►│
   │                        │   (no lecture in context) │
   │                        │◄── 422 missing_fields ────│
   │◄─ "Which lecture?" ────│                           │
   │                        │                           │
   │─ "Lecture 5: …" ──────►│                           │
   │                        │── POST /classify ─────────►│
   │                        │   context: {lecture: "…"} │
   │                        │◄── 200 classified ─────────│
   │                        │                            │
   │                        │── forward to summary-svc ──►
```

**Status codes at a glance**

| Code | Meaning |
|---|---|
| `200` | Classified — all required fields present, `downstream_payload` is ready |
| `422` | Missing fields — relay `prompt_message` to the user and retry with `context` |
| `500` | Internal error (model load failure, bad input, etc.) |

---

## Running Without Docker

### Prerequisites

- Python 3.12+
- Internet access on first run (to download the HuggingFace model)

### Steps

```bash
# 1. Enter the project directory
cd classifier-service

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (edit .env as needed)
#    At minimum, verify CLASSIFIER_MODEL points to the model you want.

# 5. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: **http://localhost:8000/docs**

> **First boot note**: the model will be downloaded from HuggingFace (~500 MB for `gliclass-small-v1.0`) and cached at `~/.cache/huggingface`. Subsequent starts are instant.

---

## Running With Docker

### Build and run manually

```bash
# Build (CPU-only torch, multi-stage build for a smaller image)
docker build -t glsclass-orchestrator:latest .

# Run (model cache stored inside the container)
docker run --rm -p 8000:8000 --env-file .env glsclass-orchestrator:latest

# Run with a persistent model cache volume (recommended)
docker run --rm -p 8000:8000 --env-file .env \
  -v glsclass_hf_cache:/app/.cache/huggingface \
  glsclass-orchestrator:latest
```

### Using Docker Compose (recommended)

```bash
# Start (builds image, creates hf_cache volume automatically)
docker compose up --build

# Stop
docker compose down

# Stop and remove the model cache volume
docker compose down -v
```

Service available at **http://localhost:8000**.

> **First boot**: the model is downloaded inside the container on first startup. The `hf_cache` Docker volume persists it across restarts and rebuilds.

---

## Environment Variables Reference

All variables are loaded from `.env` (real environment variables override `.env` values).

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Port the server listens on |
| `HOST` | `0.0.0.0` | Bind address |
| `LOG_LEVEL` | `info` | Log level: `debug`, `info`, `warning`, `error` |
| `CLASSIFIER_MODEL` | `knowledgator/gliclass-small-v1.0` | HuggingFace model ID — change to swap models with no code changes |
| `CLASSIFIER_TYPE` | `single-label` | `single-label` (one best class) or `multi-label` (all above threshold) |
| `CLASSIFIER_THRESHOLD` | `0.5` | Minimum score to accept a label (multi-label mode only) |
| `CLASSIFIER_DEVICE` | `cpu` | Inference device: `cpu`, `cuda:0`, `mps` |
| `CLASSIFIER_MAX_LENGTH` | `512` | Max token length fed to the model |
| `SUMMARY_SERVICE_URL` | `http://summary-service:8001` | Downstream summary service |
| `MCQ_SERVICE_URL` | `http://mcq-service:8002` | Downstream MCQ service |
| `FLASHCARD_SERVICE_URL` | `http://flashcard-service:8003` | Downstream flashcard service |
| `TTS_SERVICE_URL` | `http://tts-service:8004` | Downstream TTS service |
| `PLAN_SERVICE_URL` | `http://plan-service:8005` | Downstream study-plan service |
| `RAG_SERVICE_URL` | `http://rag-service:8006` | Downstream RAG service |

### Switching models

Edit `CLASSIFIER_MODEL` in `.env` and restart. No code changes needed. Any HuggingFace model compatible with the `gliclass` library works — for example:

```dotenv
CLASSIFIER_MODEL=knowledgator/gliclass-large-v1.0
```

---

## Extending the Service

### Add a class at runtime (no restart)

```bash
curl -X POST http://localhost:8000/api/v1/classes/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rag",
    "description": "Updated: answer questions with extra metadata.",
    "required_fields": ["query"],
    "optional_fields": ["top_k", "filter_subject"]
  }'
```

### Add a class permanently

1. Add a value to `ServiceClass` in `app/models/schemas.py`.
2. Add a `ClassDefinition` to `_DEFAULT_CLASSES` in `app/services/registry.py`.
3. Add the URL env var to `app/core/config.py` and `.env`.
4. Add the URL mapping in `app/services/url_resolver.py`.
5. Rebuild the Docker image.