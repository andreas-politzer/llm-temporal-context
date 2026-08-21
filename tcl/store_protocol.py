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
    def add_conversation(self, workspace_id: Optional[str] = None) -> str:
        """
        Erzeugt eine neue Conversation. Ohne workspace_id wird
        automatisch der feste Default-Workspace verwendet (Multi-User
        bewusst ausgeschlossen, ein Default genügt für den aktuellen
        Anwendungsfall).
        """
        ...

    def add_turn(self, conversation_id: str, text: str, assertion_time: Optional[datetime] = None) -> str:
        """
        Persistiert einen Turn IMMER (Audit-Trail-Prinzip). Falls
        assertion_time nicht übergeben wird, setzt die Implementierung
        die echte Server-Systemzeit (autoritative Quelle, 19.08.,
        siehe Message-Level-Timestamping-Contract) — niemals eine
        künstliche Uhrzeit wie Mitternacht erfinden.
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

    def search_turns(self, conversation_id: str, search_term: str) -> list:
        """
        Reine Textsuche über turns.text (Temporal Memory, Roadmap v2
        Punkt 1). Kein LLM, keine Interpretation — findet nur
        tatsächlich vorkommende Wörter/Wortformen, keine Paraphrasen.
        Gibt Liste von {"turn_text": str, "assertion_time": datetime} zurück.
        """
        ...
    
    def get_all_propositions(self, conversation_id: str) -> list[Proposition]:
        """
        Alle Propositionen einer Conversation, UNABHÄNGIG vom
        assertion_status — für Audit-Trail-Prüfungen (siehe Decision
        2026-08-18). Anders als get_candidates() nicht auf ASSERTED
        gefiltert.
        """
        ...

    def get_turn_assertion_time(self, turn_id: str) -> datetime:
        """Für ingest_proposition: Zeitquelle ist der Turn, nicht das Modell."""
        ...

    def get_propositions_for_turn(self, turn_id: str) -> list:
        """
        Alle Propositionen, die aus einem bestimmten Turn extrahiert
        wurden — Brücke zwischen Temporal Memory (Turn-Ebene, Mention-
        Zeit) und der Proposition-Pipeline (Event-Zeit über
        normalized_temporal_reference). Kein LLM, reine Verknüpfung
        über turn_id.
        """
        ...

    def search_temporal_memory(self, search_term: str, workspace_id: Optional[str] = None) -> list:
        """
        Workspace-gescoped, NICHT conversation-gescoped (siehe Workspace-
        Scope Contract v0). Jeder Treffer trägt explizit time_source:
        "EVENT" (aufgelöstes Ereignisdatum aus einer Proposition),
        "MENTION" (nur Turn-Zeit bekannt), "UNKNOWN" (keine belastbare
        Zeit vorhanden - defensiver Fallback, praktisch unerreichbar).
        Kein LLM. Keine Cluster-/Musterbildung - reine, sortierte Liste.
        """
        ...