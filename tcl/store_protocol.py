"""
StoreProtocol — formaler Vertrag für jede Store-Implementierung
(InMemoryStore, künftig PostgresStore), siehe Decision 2026-08-18
(Persistenz-Architektur).

Jede Implementierung muss dieses Protocol erfüllen. Contract-Tests
prüfen künftig gegen dieses Protocol, nicht gegen eine konkrete Klasse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from .proposition import Proposition
from .relation import PairwiseRelation


class StoreProtocol(Protocol):
    def add_conversation(self) -> str:
        """Erzeugt eine neue Conversation, gibt ihre id zurück."""
        ...

    def add_turn(self, conversation_id: str, text: str, assertion_time: datetime) -> str:
        """
        Persistiert einen Turn IMMER, unabhängig vom späteren Ergebnis
        der Assertion Check (Audit-Trail-Prinzip). Gibt die turn_id
        zurück.
        """
        ...

    def ingest_propositions(
        self,
        turn_id: str,
        propositions: list[Proposition],
        relations: list[PairwiseRelation],
    ) -> None:
        """
        ATOMAR: speichert alle Propositionen eines Turns (inkl.
        NOT_ASSERTED, ohne eigene Relationen) und alle berechneten
        Relationen der ASSERTED-Propositionen in einem Vorgang.
        """
        ...

    def get_candidates(self, conversation_id: str, new_proposition: Proposition) -> list[Proposition]:
        """
        Scope-gebunden: nur Propositionen derselben conversation_id.
        Exhaustive Retrieval INNERHALB des Scopes, siehe v0-Prinzip.
        """
        ...

    def get_by_id(self, proposition_id: str) -> Optional[Proposition]:
        ...

    def get_relation_between(self, id_a: str, id_b: str) -> Optional[PairwiseRelation]:
        ...
    
    def get_all_propositions(self, conversation_id: str) -> list[Proposition]:
        """
        Alle Propositionen einer Conversation, UNABHÄNGIG vom
        assertion_status — für Audit-Trail-Prüfungen (siehe Decision
        2026-08-18). Anders als get_candidates() nicht auf ASSERTED
        gefiltert.
        """
        ...