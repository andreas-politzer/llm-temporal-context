"""
Persistent Store — Architecture Contract v0, Schritt 5/8.

v0-Prinzip (siehe Decisions/2026-08-17 State-Relation - Storage-Query-
Trennung und Transition-Dominanz, Retrieval-Addendum):

    Candidate Retrieval is exhaustive by default. No semantic or
    temporal filtering is applied across independent assertions until
    a filtering strategy has been empirically validated to preserve
    recall.

Begründung, nicht nur Bequemlichkeit: Full Retrieval garantiert Recall
strukturell (kein Filter existiert, der einen relevanten Vorgänger
übersehen könnte) und liefert die Baseline, gegen die jede künftige
Filterstrategie sich messen muss ("Full Retrieval = 100% Recall").
Kosten (LLM-Aufruf pro Kandidat in Schritt 7) sind für v0 zweitrangig
gegenüber einer unverzerrten Referenzimplementierung.

decomposition_group_id (proposition.py) bleibt die einzige bereits
festgelegte Sonderregel — reine Provenienz, keine semantische
Relevanzbehauptung. Unter Exhaustive Retrieval ist sie aktuell
automatisch erfüllt, ohne eigenen Codepfad: jede Proposition wird
ohnehin zurückgegeben. Das ändert sich, sobald v0 später tatsächlich
filtert — dann MUSS diese Garantie explizit erhalten bleiben, unabhängig
vom gewählten Filter. Hier dokumentiert, damit das nicht verloren geht.

Scope: GLOBAL für v0 — kein Projekt-/Nutzer-/Konversationsscoping.
Bewusst vertagt, nicht gelöst (siehe Decision).

Bewusst KEINE Persistenzmechanismus-Entscheidung — in-memory, Datei/
SQLite/Graph-DB bleiben laut Contract offen.
"""

from __future__ import annotations

from typing import List

from .proposition import Proposition


class Store:
    def __init__(self) -> None:
        self._propositions: List[Proposition] = []

    def add(self, proposition: Proposition) -> None:
        self._propositions.append(proposition)

    def get_candidates(self, new_proposition: Proposition) -> List[Proposition]:
        """
        Schritt 5, Candidate Retrieval — v0: exhaustive, global.

        Gibt jede bereits gespeicherte Proposition zurück, unabhängig
        von semantischer oder zeitlicher Nähe zu new_proposition.
        new_proposition selbst wird hier nicht mit zurückgegeben — sie
        ist zum Zeitpunkt des Retrievals noch nicht gespeichert (das
        passiert erst nach Relation Resolution in Schritt 8).
        """
        return list(self._propositions)

    def __len__(self) -> int:
        return len(self._propositions)