"""
InMemoryStore — erfüllt StoreProtocol (siehe tcl/store_protocol.py).
Keine Übergangslösung, dauerhafte Testimplementierung desselben
Contracts wie ein künftiger PostgresStore (Decision 2026-08-18).

v0-Prinzip weiterhin gültig: Exhaustive Retrieval, aber jetzt
scope-gebunden (nur innerhalb derselben conversation_id) statt global -
löst das O(n²)-Skalierungsproblem strukturell.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from .proposition import AssertionStatus, Conversation, Proposition, Turn
from .relation import PairwiseRelation


class InMemoryStore:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._turns: dict[str, Turn] = {}
        self._propositions: dict[str, Proposition] = {}
        self._relations: list[PairwiseRelation] = []
        # Hilfsindex: welche proposition_ids gehören zu welcher conversation_id
        self._propositions_by_conversation: dict[str, list[str]] = {}
        self._conversation_by_turn: dict[str, str] = {}

    def add_conversation(self) -> str:
        conv = Conversation()
        self._conversations[conv.id] = conv
        self._propositions_by_conversation[conv.id] = []
        return conv.id

    def add_turn(self, conversation_id: str, text: str, assertion_time: datetime) -> str:
        turn = Turn(conversation_id=conversation_id, text=text, assertion_time=assertion_time)
        self._turns[turn.id] = turn
        self._conversation_by_turn[turn.id] = conversation_id
        return turn.id

    def ingest_propositions(
        self,
        turn_id: str,
        propositions: list[Proposition],
        relations: list[PairwiseRelation],
    ) -> None:
        conversation_id = self._conversation_by_turn[turn_id]
        for proposition in propositions:
            self._propositions[proposition.proposition_id] = proposition
            self._propositions_by_conversation[conversation_id].append(proposition.proposition_id)
        for relation in relations:
            self._relations.append(relation)

    def get_candidates(self, conversation_id: str, new_proposition: Proposition) -> list[Proposition]:
        ids_in_scope = self._propositions_by_conversation.get(conversation_id, [])
        return [
            self._propositions[pid]
            for pid in ids_in_scope
            if self._propositions[pid].assertion_status == AssertionStatus.ASSERTED
        ]

    def get_all_propositions(self, conversation_id: str) -> list[Proposition]:
        ids_in_scope = self._propositions_by_conversation.get(conversation_id, [])
        return [self._propositions[pid] for pid in ids_in_scope]

    def get_by_id(self, proposition_id: str) -> Optional[Proposition]:
        return self._propositions.get(proposition_id)

    def get_relation_between(self, id_a: str, id_b: str) -> Optional[PairwiseRelation]:
        for r in self._relations:
            if {r.proposition_a_id, r.proposition_b_id} == {id_a, id_b}:
                return r
        return None

    def __len__(self) -> int:
        return len(self._propositions)