"""
Persistent Store — Architecture Contract v0, Schritt 5/8.

v0-Prinzip (siehe Decisions/2026-08-17 State-Relation - Storage-Query-
Trennung und Transition-Dominanz, Retrieval-Addendum):

    Candidate Retrieval is exhaustive by default. No semantic or
    temporal filtering is applied across independent assertions until
    a filtering strategy has been empirically validated to preserve
    recall.

decomposition_group_id bleibt unter Exhaustive Retrieval automatisch
erfüllt, ohne eigenen Codepfad. Scope: GLOBAL für v0.

Update 17.08.2026, zweiter Durchgang: Store speichert jetzt auch
PairwiseRelation-Objekte, nicht nur Propositionen. Ohne das wäre
Schritt 9 (Query) nicht implementierbar — Query liest laut Contract
ausschließlich bereits gespeicherte Relationen, berechnet nichts neu.

Bewusst KEINE Persistenzmechanismus-Entscheidung — weiterhin in-memory.
"""

from __future__ import annotations

from typing import List, Optional

from .proposition import Proposition
from .relation import PairwiseRelation


class Store:
    def __init__(self) -> None:
        self._propositions: List[Proposition] = []
        self._relations: List[PairwiseRelation] = []

    def add(self, proposition: Proposition) -> None:
        self._propositions.append(proposition)

    def add_relation(self, relation: PairwiseRelation) -> None:
        self._relations.append(relation)

    def get_candidates(self, new_proposition: Proposition) -> List[Proposition]:
        """Schritt 5 — exhaustive, global. Siehe Modul-Docstring."""
        return list(self._propositions)

    def get_by_id(self, proposition_id: str) -> Optional[Proposition]:
        for p in self._propositions:
            if p.proposition_id == proposition_id:
                return p
        return None

    def get_relation_between(self, id_a: str, id_b: str) -> Optional[PairwiseRelation]:
        """
        Sucht die gespeicherte Relation zwischen zwei Propositionen,
        unabhängig davon, welche als proposition_a_id/b_id gespeichert
        wurde. Gibt es unter Exhaustive Retrieval nie mehr als eine
        Relation pro Paar (jede Proposition wird nur einmal, beim
        eigenen Einfügen, gegen den damaligen Store verglichen).
        """
        for r in self._relations:
            if {r.proposition_a_id, r.proposition_b_id} == {id_a, id_b}:
                return r
        return None

    def __len__(self) -> int:
        return len(self._propositions)