"""
ingest_turn — letztes Kettenglied: verkabelt process_turn (Schritt 1-4)
mit InMemoryStore (Schritt 5-8), inklusive Audit-Trail-Persistierung
(Decision 2026-08-18): Turn wird IMMER gespeichert, auch NOT_ASSERTED-
Propositionen werden gespeichert (mit Status, ohne Relationen) - nur
ASSERTED-Propositionen durchlaufen Relation Resolution.

Update 18.08.: conversation_id ist jetzt Pflicht-Parameter (Scope für
Candidate Retrieval, siehe Decision). Wird vom Aufrufer verwaltet
(z.B. eine Conversation pro laufender Nutzer-Session) - diese Funktion
erzeugt keine neue Conversation, sie erwartet eine bestehende id.
"""

from __future__ import annotations

from datetime import datetime

from .content_relation import content_relation_fn as default_content_relation_fn
from .pipeline import ContentRelationFn, process_new_proposition
from .proposition import AssertionStatus
from .relation import PairwiseRelation
from .store_protocol import StoreProtocol
from .turn_processor import process_turn


def ingest_turn(
    turn_text: str,
    assertion_time: datetime,
    store: StoreProtocol,
    conversation_id: str,
    content_relation_fn: ContentRelationFn = default_content_relation_fn,
) -> list[PairwiseRelation]:
    """
    Schritte 1-8 in einem Durchlauf für EINEN Turn, innerhalb einer
    gegebenen Conversation.

    Turn wird immer gespeichert (Audit-Trail). ASSERTED-Propositionen
    durchlaufen die volle Pipeline (Relation Resolution + Storage).
    NOT_ASSERTED-Propositionen werden ebenfalls gespeichert, aber ohne
    Relationen und ohne Candidate Retrieval - sie sind reine
    Audit-Information, kein Teil des aktuellen Zustands.

    Gibt die Relationen aller tatsächlich verarbeiteten (ASSERTED)
    Propositionen zurück.
    """
    turn_id = store.add_turn(conversation_id, turn_text, assertion_time)

    all_propositions = process_turn(turn_text, assertion_time)
    asserted = [p for p in all_propositions if p.assertion_status == AssertionStatus.ASSERTED]
    not_asserted = [p for p in all_propositions if p.assertion_status == AssertionStatus.NOT_ASSERTED]

    # NOT_ASSERTED: direkt und ohne Relationen persistieren (Audit-Trail)
    if not_asserted:
        store.ingest_propositions(turn_id, not_asserted, [])

    # ASSERTED: volle Pipeline, eine Proposition nach der anderen
    # (jede sieht die vorherigen als mögliche Kandidaten)
    all_relations: list[PairwiseRelation] = []
    for proposition in asserted:
        relations = process_new_proposition(
            store, conversation_id, turn_id, proposition, content_relation_fn
        )
        all_relations.extend(relations)

    return all_relations