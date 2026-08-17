# Temporal Context Layer

> A model-agnostic temporal continuity layer for AI systems.

**Work in Progress — Architecture v0**

Temporal Context Layer explores how AI systems can maintain reliable temporal continuity across interactions, model instances, and periods of inactivity.

The core idea is simple:

> **Temporal context should not live exclusively inside the model that happens to be answering right now.**

Instead, temporal knowledge can be extracted from conversations, normalized by a deterministic temporal engine, persisted independently of the language model, and queried when a later interaction needs to know what was previously true, what changed, and what remains uncertain.

This repository contains the experimental implementation of that idea.

---

## Why Temporal Context?

Large language models are good at understanding language, but temporal continuity is a different problem.

A model may correctly understand:

> "We use Jira."

and later:

> "We use Linear."

But understanding the two sentences individually is not enough.

The system needs to distinguish between fundamentally different situations:

- Linear replaced Jira.
- Jira and Linear are simultaneously claimed to be current.
- The temporal relationship cannot be determined.
- A transition was explicitly stated but its predecessor is unknown.
- A previously valid state is no longer valid.
- Two statements refer to different time intervals and are therefore not contradictory.

A naïve implementation tends to collapse these cases into "the newest statement wins".

That is precisely what this project is trying to avoid.

The goal is not merely to store timestamps.

The goal is to build a **persistent, model-independent temporal context layer that knows the difference between what is known, what is inferred, and what remains unresolved.**

---

# Core Design Principle

Temporal Context Layer separates three fundamentally different responsibilities:

```text
Language understanding
        ↓
Semantic representation
        ↓
Deterministic temporal reasoning
        ↓
Persistent storage
        ↓
Query-time interpretation