# Temporal Context Layer
> Three dimensions, not two.
Language models operate primarily in conversational order: what was said,
and what came before or after it. Real-world time is a separate dimension.
Two messages can be seconds apart in a conversation while referring to events
months apart in reality. The Temporal Context Layer (TCL) provides persistent,
explicit temporal infrastructure so a model can reason about that dimension.
## What is Time Awareness?
**Time Awareness** is the ability of a model to treat real-world time as a
continuous dimension of its context.
That includes knowing:
- what happened and when
- what is true now
- what has changed
- what remains valid
- what has expired
- what is approaching
- how long ago something happened
The TCL is **infrastructure for Time Awareness, not Time Awareness itself**.
---
## What the TCL does
The TCL stores and evaluates temporal propositions independently of the
language model.
It distinguishes:
- **Mention time** — when something was said
- **Event time** — when the referenced event occurred
- **Validity** — when a state is considered true
- **Temporal relations** — how states continue, change, contradict or supersede
- **Conversation scope** — local continuity and compatibility
- **Workspace scope** — persistent retrieval across conversations
The fundamental architectural boundary is:
> **The LLM interprets language. The deterministic engine performs temporal
> arithmetic.**
---
## Current Status
**Core temporal engine: working.**  
**PostgreSQL persistence: working.**  
**MCP integration: working.**  
**Cross-conversation temporal retrieval: working.**  
**Autonomous relevance-based capture: demonstrated live.**
The most important recent result:
Claude independently decided that a relevant project statement should be
stored and invoked `note_moment` without being told to "remember this".
At the same time, an irrelevant Pizza question was not captured.
This demonstrates the first working form of **autonomous relevance-based
temporal capture**.
It is deliberately not described as true ambient capture.
---
## Architecture
The temporal processing pipeline separates model reasoning from deterministic
processing:
```text
Conversation
     │
     ▼
Proposition Extraction        LLM
     │
     ▼
Assertion Check               LLM
     │
     ▼
Temporal Expression           LLM
     │
     ▼
Temporal Normalization        TCL
     │
     ▼
Candidate Retrieval           Store
     │
     ▼
Temporal Relations            TCL
     │
     ▼
Persistent Store              PostgreSQL

The engine supports temporal relations including:

* CONTINUES
* SUPERSEDES
* CONTRADICTS

Temporal relations are derived from temporal intervals and proposition
compatibility, not from conversational proximity.

⸻

Capture

The old workflow required the model to orchestrate separate operations such
as begin_turn and ingest_proposition.

That proved too fragile: the model could forget or skip the preliminary
begin_turn call.

The capture interface has therefore been simplified.

begin_turn is now an internal implementation detail.

The public capture path is:

Model
  │
  ▼
note_moment
  │
  ▼
TCL creates the Turn internally
  │
  ▼
temporal processing
  │
  ▼
persistent memory

The user does not need to manage turn IDs or explicitly request storage.

⸻

Autonomous Capture

The intended interaction is:

User ↔ Model
       │
       └── relevant information detected
                    │
                    ▼
               note_moment
                    │
                    ▼
                  TCL

The model decides whether information is sufficiently relevant to preserve.

Examples:

"Where can I get good pizza in Eppendorf?"
        → no capture
"We decided to use PostgreSQL as the persistent store."
        → capture

The user should not have to become the system’s archivist.

⸻

MCP Boundary

MCP is a tool protocol, not an ambient message listener.

An MCP server cannot independently observe every message in a host
application. A tool call must be initiated through the model/host.

Therefore:

True ambient message capture cannot be implemented through MCP alone.

The project does not attempt to hide or fake this limitation.

The current approach is autonomous relevance-based capture: the model decides
when to call the TCL rather than requiring the user to explicitly say
“remember this”.

⸻

Scope

The current architecture deliberately uses two scopes:

Conversation

A narrow scope for local continuity and compatibility checks.

Workspace

A broader scope for persistent temporal retrieval across conversations.

This allows a new conversation to retrieve information from earlier
conversations without knowing their conversation IDs.

For the current single-user architecture, one default workspace is sufficient.

⸻

Proof and Testing

The TCL has been tested end-to-end with:

* a real language model
* a real MCP integration
* PostgreSQL
* real separate conversations

Testing has exposed issues that isolated unit tests did not reveal, including:

* incorrect temporal anchors
* turn-creation coupling
* conversation/workspace scope conflicts
* MCP limitations
* model tool-call reliability

The project’s guiding principle is:

Test against reality, not against our assumptions about the system.

⸻

Current Open Questions

The core memory and temporal engine are no longer the main research problem.

The next question is:

How can a running model receive a reliable, current temporal context
without requiring the user to explicitly ask for it?

One promising direction is a separate time/scheduler layer:

Scheduler / Clock
       │
       ▼
      TCL
       │
       ▼
Temporal Context Frame
       │
       ▼
     Model

The scheduler would provide reliable passage-of-time signals without calling
Claude through visible MCP operations.

This is currently a research direction, not an implemented component.

The larger goal remains unchanged:

Give language models a genuine temporal dimension of context — not merely
a database in which old conversations can be searched.

