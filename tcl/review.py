"""
review.py — die Zwei-Schritt-Orchestrierung für Schritt 7a (Content
Relation) in der MCP-Architektur. Siehe MCP-Interface Contract v0.

Ablauf:
1. get_candidates_for_review(): Server liefert dem aufrufenden Modell
   die Kandidatenliste für eine neue Proposition zurück.
2. Aufrufendes Modell beurteilt SELBST, ob jede Kandidat-Proposition
   COMPATIBLE/INCOMPATIBLE/UNDETERMINED zur neuen Proposition ist.
3. Modell ruft ingest_with_judgments() mit den fertigen Urteilen auf.

Der Server selbst führt an KEINER Stelle einen eigenen LLM-Aufruf aus -
reine Datenaufbereitung und -entgegennahme.
"""

from __future__ import annotations

from typing import TypedDict

from .proposition import Proposition


class CandidateForReview(TypedDict):
    proposition_id: str
    proposition_text: str


def get_candidates_for_review(store, conversation_id: str, new_proposition: Proposition) -> list[CandidateForReview]:
    """
    Schritt 1 der Zwei-Schritt-Interaktion. Gibt NUR das zurück, was
    das aufrufende Modell für sein eigenes content_relation-Urteil
    braucht - proposition_id (für die spätere Zuordnung) und
    proposition_text (für die semantische Beurteilung). Keine internen
    Felder (transition_type etc.) - die gehen das Modell an dieser
    Stelle nichts an, das ist Aufgabe von Schritt 7b, nicht 7a.
    """
    candidates = store.get_candidates(conversation_id, new_proposition)
    return [
        CandidateForReview(proposition_id=c.proposition_id, proposition_text=c.proposition_text)
        for c in candidates
    ]