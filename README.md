# Temporal Context Layer

> A model-agnostic temporal continuity layer for AI systems.

**Status: Work in Progress — Phase A (Architecture Validation)**

Temporal Context Layer explores how AI systems can maintain reliable temporal continuity across interactions, model instances, and periods of inactivity.

The core idea is simple:

> **Temporal context should not live exclusively inside the model that happens to be answering right now.**

Instead, temporal knowledge is extracted from conversations, checked for logical consistency by a deterministic engine, persisted independently of the language model, and queried when a later interaction needs to know what was previously true, what changed, and what remains uncertain.

This repository contains the working implementation of that idea — not a demo, not a thought experiment. Every rule described below is backed by a test that currently passes.

---

## Why Temporal Context?

Language models have no sense of time passing. A model reads its context top to bottom, every single turn — it has no way to tell whether the last message in that context was written five minutes ago or five years ago. Nothing marks the passage of time; the text just sits there, equally "present" no matter how stale it actually is.

This produces a specific, recurring failure: a model confidently treats something as still valid long after it has expired. Ask about a certification, a contract, a deadline — "yes, that's fine, it's valid until June 2026" — without registering that the conversation is actually happening in August 2026, two months past that date. The information itself wasn't wrong. The model just had no way of knowing that time had moved on since it was true.

That is the actual problem this project set out to solve — not clever language understanding, but basic temporal grounding: knowing *when* something was said relative to *now*, whether it's still current, and being honest about the difference between "this was true," "this is still true," and "I can no longer tell."

Solving that turns out to require more than tracking timestamps. The system needs to distinguish between genuinely different situations — a stated fact being superseded by a later one, two facts genuinely contradicting each other, a change being mentioned without knowing what it replaced, or simply not having enough information to say either way. A naive implementation collapses all of these into "the newest statement wins," which quietly produces exactly the kind of false confidence described above. That is precisely what this project avoids — deliberately, and at the cost of a much slower build process, because every shortcut we tried turned out to hide a real edge case.

The goal is a persistent, model-independent temporal context layer that keeps a model honestly grounded in *when* it is and what has or hasn't expired since — one that knows the difference between what is known, what is inferred, and what remains unresolved.

---

## Architecture

Nine pipeline steps, each with a clearly defined responsibility and an explicit negative responsibility (what it is not allowed to decide):

1. Proposition Extraction (LLM) — splits a turn into atomic statements
2. Assertion Check (LLM) — ASSERTED/NOT_ASSERTED + transition_type
3. Temporal Expression Extraction (LLM) — raw time expressions, fixed vocabulary
4. Temporal Normalization (Engine) — deterministic, no LLM involved
5. Candidate Retrieval (Store) — exhaustive by default, no premature filtering
6. Relation Resolution (Engine) — pure interval arithmetic
7. State Relation / Content Compatibility (LLM+Engine) — the only step that touches world knowledge
8. Store — persists propositions and computed relations
9. Query / Current-State — reads only, never re-evaluates

The full specification, including every rule and the reasoning behind it, lives in the Architecture Contract v0 document and its three companion contracts (Proposition Extraction, Assertion Check, Content Relation) — these are working documents kept outside this repository.

### Design principles that shaped every decision here

- No relation is inferred from timing alone. Two statements 15 minutes apart and two statements 7 months apart are treated identically at the storage level — a deliberate rejection of "default persistence" heuristics that turned out to break more cases than they fixed.
- Exhaustive retrieval, not premature filtering. Every new proposition is compared against everything already stored. Slower, but guarantees recall — filtering is deferred until it's actually needed and can be validated against this baseline.
- The deterministic engine never sees content; the LLM never does date arithmetic. A hard boundary, enforced in code, not just convention.
- Ground truth by triangulation, not by decree. Every classification rule in this project was checked against independent, blind judgments from multiple models before being written into a prompt. Several rules exist only because two models initially disagreed, and the disagreement turned out to reveal a genuine, previously invisible edge case.
- Pragmatism over purity, deliberately. Where a strict "no world knowledge" rule would have made the system nearly useless for ordinary language, the rule was changed — but only after the tension itself had been used to find a real bug.

---

## What's implemented

| Component | File | Status |
|---|---|---|
| Proposition / relation data model | tcl/proposition.py, tcl/relation.py | done |
| Deterministic temporal engine | tcl/temporal_engine.py | done (one known edge-case bug, see below) |
| Persistent store (in-memory, exhaustive retrieval) | tcl/store.py | done |
| Pipeline orchestration (steps 5-8) | tcl/pipeline.py | done |
| Current-state query resolution | tcl/query.py | done |
| Content relation (LLM, step 7a) | tcl/content_relation.py | done, 31/31 regression corpus |
| Proposition extraction (LLM, step 1) | tcl/extraction.py | done, 16/16 regression corpus |
| Assertion check (LLM, step 2) | tcl/assertion_check.py | done, 7/7 regression corpus |
| Temporal expression extraction (LLM, step 3) | tcl/temporal_expression.py | done, 6/6 regression corpus |
| End-to-end wiring (steps 1 to 9 in one pass) | — | not yet built |

Every LLM-backed component was built the same way: define the contract and its boundaries first, construct minimal test pairs, get independent blind classifications from multiple models, resolve disagreements explicitly, then write the prompt, then validate against the corpus. No component skipped this order.

### Known open issue

The weekday resolution helper in temporal_engine.py resolves weekday references backward-only. When the reference date itself falls on the interval's start weekday, this can produce a logically inverted interval (end before start) for "from X through Y" expressions. Pre-existing, not something the recent work introduced — flagged, not yet fixed.

---

## Running the tests

Deterministic and free:

    python test_known_cases.py
    python test_pipeline.py
    python test_query.py
    python test_store_baseline.py

Call the Anthropic API, need `pip install anthropic` and an `ANTHROPIC_API_KEY` environment variable, cost a small amount per run:

    python test_content_relation_llm.py
    python test_extraction.py
    python test_assertion_check.py
    python test_temporal_expression.py

---

## What's next

The Proposition Extraction pipeline (steps 1-3) is now complete and individually tested, alongside Content Relation (step 7a) and the deterministic core (steps 4-9) built earlier. The next milestone is wiring steps 1 through 4 into a single end-to-end pass, followed by the transition from Phase A (architecture validation) into Phase B: real persistent storage, conversation scoping, and robust handling of missing temporal information — the beginning of an actual usable layer rather than a validated architecture.

This is not a finished product. It is a project that has, so far, refused every shortcut that looked easy — and gotten more reliable for it.