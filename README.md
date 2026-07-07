# AI Customer Support Refund Agent

A production-style AI customer support agent for e-commerce refunds. The LLM
reasons; **tools verify facts**; a deterministic policy engine has the final
word. Reasoning traces stream to an admin dashboard, and customer PII never
leaves the backend.

## [Video Walkthrough](https://www.loom.com/share/84c7c5ac15ae4dd7bdc7b4c7b878146f)

## Architecture

```
Customer UI (Next.js)          Admin Dashboard (Next.js)
      │ REST /api/chat               │ WS /ws/admin (trace events)
      ▼                              ▼
FastAPI ──────────────────────────────
      │
LangGraph agent (PostgresSaver checkpoints)
  START → extract_intent → retrieve_customer → retrieve_order
        → retrieve_policy → retrieve_similar_cases → decision
        ⇄ tools (needs more info?) → policy_validation → generate_response → END
      │
Tool layer (7 tools, sanitized outputs)
      │
Postgres + pgvector  (CRM, checkpoints, policy & case embeddings)
      │
OpenAI-compatible LLM server (Ollama locally / vLLM + Qwen2.5-7B-Instruct in production)
```

Key properties:

- **Privacy split state.** Graph state is divided into public / private / shared
  (`backend/graph/state.py`). Every trace event and API response is built via
  `public_view()`, which never touches the `private` key (PII, fraud score, raw
  rows). Tool outputs fed to the LLM are sanitized at the source
  (`backend/tools/refund_tools.py`), so prompts and LangFuse traces are PII-free
  by construction.
- **Tool-based decisions.** The LLM proposes a decision, but the deterministic
  `policy_validation` node re-derives the verdict from database facts and
  overrides the LLM on any mismatch (emitting a `decision_overridden` trace event).
- **Transparent reasoning.** Nodes emit `node_started` / `node_completed` /
  `tool_called` / `retry` / `escalation` / `decision_overridden` events with
  latencies over `/ws/admin`.

## Refund policy

See [data/refund_policy.md](data/refund_policy.md): 30-day window, opened
electronics non-refundable, max two refunds per 12 months, one VIP override per
year, manual review over ₹50,000, digital products non-refundable, damaged
items refundable, fraud-flagged accounts escalate.

## Local setup (macOS)

Prereqs: Python 3.10+, Node 20+, Homebrew.

```bash
# 1. Infrastructure
brew install postgresql@17 pgvector ollama
brew services start postgresql@17
createdb refund_agent
brew services start ollama
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# 2. Backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env      # defaults work for the local setup above

# 3. Seed the CRM (15 customers / 50 orders / 20 products / 25 refund requests + embeddings)
cd backend && .venv/bin/python ../data/seed_customers.py && cd ..

# 4. Run
cd backend && .venv/bin/uvicorn main:app --port 8000 &
cd frontend && npm install && npm run dev
```

- Customer chat: http://localhost:3000
- Admin dashboard: http://localhost:3000/admin
- API docs: http://localhost:8000/docs

Prefer containers? `docker compose -f deployment/docker-compose.yml up` starts
Postgres+pgvector and Ollama instead of the brew services.

## Demo scenarios

Pick a customer in the UI header, then ask for a refund:

| Customer | Order | Expected outcome |
|---|---|---|
| CUST-006 (first-time) | ORD-1001 | Approved — in window |
| CUST-004 (loyal) | ORD-1002 | Denied — outside 30-day window |
| CUST-001 (VIP) | ORD-1003 | Approved — VIP annual override |
| CUST-005 (high LTV) | ORD-1004 | Escalated — ₹82,000 > ₹50,000 |
| CUST-002 (refund abuser) | ORD-1005 | Denied — 2 refunds in 12 months |
| CUST-003 (fraud flag) | ORD-1006 | Escalated — fraud check |
| CUST-008 | ORD-1007 | Denied — opened electronics |
| CUST-009 | ORD-1008 | Denied — digital product |
| CUST-010 | ORD-1009 | Approved — damaged on arrival |

## Configuration

All via `.env` (see [.env.example](.env.example)):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres+pgvector (local or Supabase) |
| `LLM_BASE_URL`, `LLM_MODEL` | Any OpenAI-compatible server. Local: Ollama `qwen2.5:3b`. Production: vLLM `Qwen/Qwen2.5-7B-Instruct` |
| `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Embedding endpoint (default: Ollama `nomic-embed-text`, 768-dim) |
| `OPENAI_API_KEY` | Enables the voice pipeline (OpenAI Realtime API). Empty ⇒ mic disabled |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Enables LangFuse tracing. Empty ⇒ off |

## Voice

`/ws/voice` relays OpenAI Realtime API events through the backend (the API key
stays server-side). The Realtime session has a single tool,
`submit_refund_request`, which runs the same LangGraph agent as text chat —
voice cannot bypass policy enforcement. Set `OPENAI_API_KEY` to enable.

## Production deployment

- **Frontend** → Vercel (`NEXT_PUBLIC_API_URL` pointing at the backend).
- **Backend** → Railway/Render (`uvicorn main:app`).
- **Database** → Supabase Postgres with the `vector` extension enabled; set `DATABASE_URL`.
- **LLM** → vLLM on a GPU host (RunPod/Vast):
  `vllm serve Qwen/Qwen2.5-7B-Instruct --enable-auto-tool-choice --tool-call-parser hermes`,
  then `LLM_BASE_URL=http://<host>:8000/v1`, `LLM_MODEL=Qwen/Qwen2.5-7B-Instruct`.

## Repository layout

```
backend/
  api/          REST routes (chat, admin events)
  graph/        LangGraph state, nodes, builder (PostgresSaver checkpointing)
  tools/        7 agent tools (sanitized outputs)
  services/     db, llm, embeddings, event bus, langfuse, agent runner
  models/       SQLAlchemy models
  prompts/      system prompts
  websocket/    /ws/admin (traces), /ws/voice (Realtime relay)
frontend/
  app/          / (customer chat), /admin (dashboard)
  components/   chat, decision card, trace log, graph flow, metrics
  store/        Zustand stores
  hooks/        WebSocket hooks
data/           refund_policy.md, seed_customers.py, historical_cases.json
deployment/     docker-compose.yml (infra services)
```
