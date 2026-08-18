"""
ingest_turn — letztes Kettenglied: verkabelt process_turn (Schritt 1-4)
mit pipeline.process_new_proposition (Schritt 5-8). Erster wirklich
vollständiger Fluss von Rohtext bis zum Store.

CONTRACT-PUNKT, hier durchgesetzt: NOT_ASSERTED-Propositionen verlassen
die Pipeline nach Schritt 2 (Assertion Check) - kein Storage, keine
Relation Resolution (siehe Architecture Contract v0, Schritt 2-Box).
process_turn selbst prüft das nicht (siehe dessen Docstring: deckt nur
Schritt 1-4 ab). Diese Funktion ist der erste Ort, an dem der Filter
tatsächlich angewendet wird - vorher gab es dafür noch keinen
Aufrufer.
"""

from __future__ import annotations

from datetime import datetime

from .content_relation import content_relation_fn as default_content_relation_fn
from .pipeline import ContentRelationFn, process_new_proposition
from .proposition import AssertionStatus
from .relation import PairwiseRelation
from .store import Store
from .turn_processor import process_turn


def ingest_turn(
    turn_text: str,
    assertion_time: datetime,
    store: Store,
    content_relation_fn: ContentRelationFn = default_content_relation_fn,
) -> list[PairwiseRelation]:
    """
    Schritte 1-8 in einem Durchlauf für EINEN Turn.

    Filtert NOT_ASSERTED-Propositionen VOR dem Store-Zugriff heraus -
    sie durchlaufen Schritt 1-4 (werden extrahiert und klassifiziert,
    das ist nötig, um überhaupt zu wissen, dass sie NOT_ASSERTED sind),
    aber niemals Schritt 5-8.

    Gibt die Relationen aller tatsächlich gespeicherten (ASSERTED)
    Propositionen zurück, in der Reihenfolge, in der sie verarbeitet
    wurden.
    """
    all_propositions = process_turn(turn_text, assertion_time)
    asserted_propositions = [
        p for p in all_propositions if p.assertion_status == AssertionStatus.ASSERTED
    ]

    all_relations: list[PairwiseRelation] = []
    for proposition in asserted_propositions:
        relations = process_new_proposition(store, proposition, content_relation_fn)
        all_relations.extend(relations)

    return all_relations