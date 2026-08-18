-- Schema für PostgresStore, abgeleitet aus tcl/store_protocol.py
-- (Decision 2026-08-18: Persistenz-Architektur)

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    text TEXT NOT NULL,
    assertion_time TIMESTAMPTZ NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_turns_conversation ON turns(conversation_id);

CREATE TABLE propositions (
    id UUID PRIMARY KEY,
    turn_id UUID NOT NULL REFERENCES turns(id),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    decomposition_group_id UUID,
    proposition_text TEXT NOT NULL,
    assertion_status TEXT NOT NULL CHECK (assertion_status IN ('ASSERTED', 'NOT_ASSERTED')),
    transition_type TEXT NOT NULL DEFAULT 'BARE'
        CHECK (transition_type IN ('BARE', 'CONTINUATION', 'TRANSITION')),
    raw_temporal_expression TEXT,
    normalized_start TIMESTAMPTZ,
    normalized_end TIMESTAMPTZ,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_propositions_turn ON propositions(turn_id);
CREATE INDEX idx_propositions_conversation ON propositions(conversation_id);
CREATE INDEX idx_propositions_group ON propositions(decomposition_group_id);

CREATE TABLE pairwise_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposition_a_id UUID NOT NULL REFERENCES propositions(id),
    proposition_b_id UUID NOT NULL REFERENCES propositions(id),
    temporal_relation TEXT NOT NULL
        CHECK (temporal_relation IN ('BEFORE', 'AFTER', 'OVERLAP', 'UNDETERMINED')),
    content_relation TEXT NOT NULL
        CHECK (content_relation IN ('COMPATIBLE', 'INCOMPATIBLE', 'UNDETERMINED')),
    state_relation TEXT NOT NULL
        CHECK (state_relation IN ('CONTINUES', 'SUPERSEDES', 'CONTRADICTS', 'UNDETERMINED')),
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (proposition_a_id, proposition_b_id)
);
CREATE INDEX idx_relations_a ON pairwise_relations(proposition_a_id);
CREATE INDEX idx_relations_b ON pairwise_relations(proposition_b_id);