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
from uuid import uuid4
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
        self._propositions_by_conversation: dict[str, list[str]] = {}
        self._conversation_by_turn: dict[str, str] = {}
        self._workspace_by_conversation: dict[str, str] = {}
        self._default_workspace_id: Optional[str] = None

    def _get_default_workspace(self) -> str:
        if self._default_workspace_id is None:
            self._default_workspace_id = str(uuid4())
        return self._default_workspace_id

    def add_conversation(self, workspace_id: Optional[str] = None) -> str:
        if workspace_id is None:
            workspace_id = self._get_default_workspace()
        conv = Conversation()
        self._conversations[conv.id] = conv
        self._propositions_by_conversation[conv.id] = []
        self._workspace_by_conversation[conv.id] = workspace_id
        return conv.id

    def add_turn(self, conversation_id: str, text: str, assertion_time: Optional[datetime] = None) -> str:
        if assertion_time is None:
            assertion_time = datetime.now()
        turn = Turn(conversation_id=conversation_id, text=text, assertion_time=assertion_time)
        self._turns[turn.id] = turn
        self._conversation_by_turn[turn.id] = conversation_id
        return turn.id

    def get_turn_assertion_time(self, turn_id: str) -> datetime:
        if turn_id not in self._turns:
            raise ValueError(f"turn_id {turn_id!r} existiert nicht")
        return self._turns[turn_id].assertion_time

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

    def search_turns(self, conversation_id: str, search_term: str) -> list:
        term_lower = search_term.lower()
        results = []
        for turn in self._turns.values():
            if turn.conversation_id == conversation_id and term_lower in turn.text.lower():
                results.append({"turn_text": turn.text, "assertion_time": turn.assertion_time})
        results.sort(key=lambda r: r["assertion_time"])
        return results

    def get_propositions_for_turn(self, turn_id: str) -> list:
        return [p for p in self._propositions.values() if p.turn_id == turn_id]

    def search_temporal_memory(self, search_term: str, workspace_id: Optional[str] = None) -> list:
        if workspace_id is None:
            workspace_id = self._get_default_workspace()
        term_lower = search_term.lower()
        results = []

        conv_ids_in_workspace = [
            cid for cid, wid in self._workspace_by_conversation.items() if wid == workspace_id
        ]

        for turn in self._turns.values():
            if turn.conversation_id not in conv_ids_in_workspace:
                continue

            matching_props = [
                p for p in self._propositions.values()
                if p.turn_id == turn.id and p.normalized_temporal_reference and p.normalized_temporal_reference.start
                and term_lower in p.proposition_text.lower()
            ]
            if matching_props:
                for p in matching_props:
                    results.append({
                        "text": p.proposition_text,
                        "time": p.normalized_temporal_reference.start,
                        "time_source": "EVENT",
                        "conversation_id": turn.conversation_id,
                    })
            elif term_lower in turn.text.lower():
                time_value = turn.assertion_time
                results.append({
                    "text": turn.text,
                    "time": time_value,
                    "time_source": "MENTION" if time_value is not None else "UNKNOWN",
                    "conversation_id": turn.conversation_id,
                })

        results.sort(key=lambda r: r["time"] or datetime.min)
        return results

    def __len__(self) -> int:
        return len(self._propositions)