# Temporal Context Layer

> Three dimensions, not two.

Language models move through two dimensions by default: what is being said,
and the order in which it was said. A third dimension — real, calendar time,
independent of conversation order — is usually missing entirely. Two messages
next to each other in a conversation can be five minutes or five months apart
in the real world, and a model that only tracks conversational order cannot
tell the difference.

This project adds that third dimension back.

## What is Time Awareness?

**Time Awareness is the ability of a model to treat time as a continuous
dimension of its context: understanding what has happened, what is true now,
what has changed, what remains valid, what is approaching, and what can be
expected or planned in relation to time.**

This is a larger goal than any single mechanism. Temporal memory, temporal
validity, temporal continuity, projection, and planning are distinct
capabilities that together contribute to time awareness.

## What this layer does

**A Temporal Context Layer gives language models an explicit representation
of the passage of time and the temporal validity of information, so that
information retrieved or remembered from the past is not automatically
treated as current.**

The layer is therefore infrastructure for time awareness, not time awareness
itself. It provides explicit temporal context that a model can use when
reasoning about past, present, and future.

**Status: Work in progress, Phase A/B — architecture validated, core proven
live against a real model and a real database, several components still open.**

---

## Why this matters

Language models routinely work with information whose temporal status is
implicit: something may have been true when it was written, may still be true
now, may have changed since, or may only become relevant in the future.

Conversation order alone does not encode that distinction. A message can be
the most recent thing in the context while referring to something that is
already obsolete in the real world.

The goal is therefore not clever date parsing. The goal is a persistent,
model-independent temporal context layer that gives a model an explicit
representation of the passage of time and the temporal validity of information,
so that information retrieved or remembered from the past is not automatically
treated as current.

Temporal validity is one important part of that problem. Temporal memory,
continuity, projection, and planning are related but distinct capabilities.
This project deliberately treats them as separate building blocks rather than
pretending that one mechanism solves "time awareness" as a whole.

---

## What "temporal awareness" actually breaks down into

Not one problem. Several, mostly independent:

- **Temporal Presence** — knowing what "now" is, without being told. *(Already works for Claude, via its own system context — verified live: asked "how long until Christmas" with no date mentioned anywhere in the conversation, and it answered correctly. Not guaranteed for every model/platform.)*
- **Temporal Memory** — "when did we talk about X?" A pure timestamp lookup over conversation history, no interpretation needed. *(Not yet built — the raw data already exists in every stored turn, but nothing searches it yet.)*
- **Temporal Validity** — "is this still true?" This is the core of what's built and proven: propositions with a known expiry are checked against the current query time, and the system says so honestly — never silently "still valid," never a guessed "no longer valid," always the known fact plus the acknowledged gap.
- **Temporal Continuity** — how a state evolves: replaced, contradicted, or simply continued. Already implemented as the pairwise relation engine (`CONTINUES` / `SUPERSEDES` / `CONTRADICTS`).
- **Temporal Projection** — "how long until X?" Follows naturally once Presence and Validity work; not a separate thing to build.
- **Temporal Planning** — using time to decide what to do next. A model's own reasoning, downstream of good grounding — not something this layer should try to own.

This layer is infrastructure for the middle of that list, mainly Validity and Continuity. It is not the whole of "time awareness" — being honest about that scope is part of the design, not a disclaimer.

---

## Architecture

Nine pipeline steps, each with an explicit responsibility and an explicit thing it is *not* allowed to decide:

1.  Proposition Extraction (LLM) — splits a turn into atomic statements
2.  Assertion Check (LLM) — ASSERTED/NOT_ASSERTED + transition_type
3.  Temporal Expression Extract (LLM) — raw time expressions, fixed vocabulary
4.  Temporal Normalization (Engine) — deterministic, no LLM involved
5.  Candidate Retrieval (Store) — exhaustive within a conversation, no premature filtering
6.  Relation Resolution (Engine) — pure interval arithmetic
7.  State Relation /
    Content Compatibility (LLM+Engine)— the only step that touches world knowledge
8.  Store — persists propositions, relations, full audit trail
9.  Query / Current-State — reads only, checks validity against "now", never re-evaluates


**A design principle that runs through every decision here:** the deterministic engine never sees content, and the LLM never does date arithmetic. Every relation is computed from real intervals — never from how close together two statements happened to be said. A contradiction fifteen minutes apart and one seven months apart are judged by the same rule, not by an implicit "recent things conflict" heuristic. That distinction alone took a full day to get right, because every shortcut we tried quietly broke something else.

---

## What is actually proven

The core Temporal Context Layer has been exercised end-to-end with a real
language model, a real MCP host, and a real PostgreSQL database.

The system can persist temporally grounded propositions, maintain their
relations, evaluate their temporal validity against a query time, detect
knowledge that has become temporally unresolved, and expose that state through
MCP to a model.

A live model test also exposed an important limitation that our isolated tests
had missed: the model could sometimes compensate for missing temporal
functionality using its own reasoning. That distinction matters. A correct
model answer is not evidence that the Temporal Context Layer itself performed
the reasoning.

The project's standard of proof is therefore deliberately stricter:
deterministic temporal behaviour must first be demonstrated by the layer
itself; model integration is then tested separately to verify that the model
can actually use that information.

---

## What's implemented

| Component | Status |
|---|---|
| Proposition / relation data model, deterministic temporal engine | done |
| Persistent store — `InMemoryStore` and `PostgresStore`, same protocol, both tested against the same contract | done |
| Conversation/turn scoping, atomic ingestion, full audit trail (including rejected/hypothetical statements) | done |
| Content relation, proposition extraction, assertion check, temporal expression extraction (LLM-backed) | done, each with its own regression corpus |
| Lifecycle/decay — expiry detection against real query time, honest "expired, unknown since" responses | done, proven live |
| MCP server — five tools, verified against a real MCP host (Inspector + Claude Desktop), verified against real Postgres | done |

## What's explicitly not done yet

- **Temporal Memory** (Klasse A above) — searching conversation history by content for "when was X mentioned," without needing the heavier semantic pipeline at all.
- **Message-level timestamping** — every turn currently gets a timestamp only when something is deliberately stored; there's no automatic per-message log yet, which is what would let the system answer "how long have we actually been working, net of breaks" without being told.
- **Read/write tool permission structure and call-frequency policy** — right now nothing stops a model from calling these tools too eagerly; a normal conversation should mostly *not* touch the server at all, and that boundary isn't formally specified yet.
- **Graduated expiry warnings** ("expires soon") — currently binary: expired or not.
- **Cross-model reliability** — everything proven so far was proven with Claude. MCP support elsewhere is currently uneven (partial for OpenAI, weak for Gemini), which is a real, current constraint on the "model-agnostic" goal, not a solved problem.

---

## Running it

```bash
python -m venv .venv
source .venv/bin/activate
pip install "psycopg[binary]" "mcp[cli]>=2.0,<3.0" anthropic
export ANTHROPIC_API_KEY="your-key-here"

docker run --name tcl-postgres -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=temporal_context_layer -p 5432:5432 -d postgres:16
docker exec -i tcl-postgres psql -U postgres -d temporal_context_layer < schema.sql
```

Deterministic tests (free, no API calls): `test_known_cases.py`, `test_store_contract.py`, `test_query_decay.py`, `test_certificate_decay.py`.

LLM-backed tests (small real API cost, a full pass is well under a dollar): `test_content_relation_llm.py`, `test_extraction.py`, `test_assertion_check.py`, `test_temporal_expression.py`, `test_ingest.py`, `test_mcp_server.py`.

Run the MCP server directly, or inspect it interactively: `mcp dev tcl/server.py`.

---

This isn't a finished product, and more than once today it wasn't clear it was heading anywhere useful at all. What kept it honest was testing against a real model instead of trusting our own explanations of what we'd built — twice today, a live test found a real gap that every unit test had missed. That's the actual method here, not a footnote: build the smallest true thing, test it against reality, believe the result over the theory.