"""
Pipeline-Orchestrierung — verkabelt Store (Schritt 5), Temporal Engine
(Schritt 6) und resolve_state_relation (Schritt 7) zu einem Ablauf für
eine neu ankommende Proposition.

WICHTIG, siehe Chat 17.08.: content_relation wird bewusst NICHT hier
berechnet. Laut Architecture Contract v0, Schritt 7a, ist das Aufgabe
der semantischen/LLM-Ebene. Diese Pipeline enthält kein LLM und keine
Domänen-Heuristik dafür — content_relation wird als externe Abhängigkeit
injiziert (content_relation_fn), nicht simuliert. Kein Interims-Mock:
sobald eine echte LLM-Anbindung existiert, wird genau hier eine echte
Implementierung von content_relation_fn eingesetzt, ohne dass sich an
dieser Pipeline-Funktion etwas ändern muss.

Konvention (wie in test_known_cases.py): transition_type_a gehört zur
älteren/bereits gespeicherten Proposition (Kandidat), transition_type_b
zur neuen. compare_intervals() wird in derselben Reihenfolge aufgerufen.
"""

from __future__ import annotations

from typing import Callable, List

from .proposition import Proposition
from .relation import PairwiseRelation, SemanticCompatibility, resolve_state_relation
from .store import Store
from .temporal_engine import compare_intervals

ContentRelationFn = Callable[[Proposition, Proposition], SemanticCompatibility]


def process_new_proposition(
    store: Store,
    new_proposition: Proposition,
    content_relation_fn: ContentRelationFn,
) -> List[PairwiseRelation]:
    """
    Architecture Contract v0, Schritte 5-8 für EINE neue Proposition.

    Vorbedingung: new_proposition muss assertion_status=ASSERTED haben.
    NOT_ASSERTED-Propositionen verlassen die Pipeline bereits nach
    Schritt 2 (Assertion Check) und dürfen diese Funktion nie erreichen
    — kein Storage, keine Relation Resolution. Wird das verletzt, ist
    das ein Vertragsbruch des Aufrufers, keine Situation, die hier
    behandelt wird (kein Guard, kein stiller Early-Return — siehe Chat
    17.08.: das würde Verantwortung aus Schritt 2 in Schritt 5
    hineinziehen). Erzwungene Prüfung folgt erst, wenn Schritt 1-4
    tatsächlich implementiert sind und einen echten Aufrufer haben.

    content_relation_fn(candidate, new_proposition) -> SemanticCompatibility
    ist von außen vorgegeben (semantische/LLM-Ebene, siehe Modul-
    Docstring) — kein Aufruf hier, keine eingebaute Heuristik.

    Schritt 8: new_proposition wird erst NACH der Relation Resolution
    gegen alle Kandidaten gespeichert, damit sie sich nicht selbst als
    Kandidat vorgelegt bekommt.
    """
    candidates = store.get_candidates(new_proposition)

    relations: List[PairwiseRelation] = []
    for candidate in candidates:
        temporal_relation = compare_intervals(
            candidate.normalized_temporal_reference,
            new_proposition.normalized_temporal_reference,
        )
        content_relation = content_relation_fn(candidate, new_proposition)
        state_relation = resolve_state_relation(
            temporal_relation,
            content_relation,
            transition_type_a=candidate.transition_type,
            transition_type_b=new_proposition.transition_type,
        )
        relations.append(
            PairwiseRelation(
                proposition_a_id=candidate.proposition_id,
                proposition_b_id=new_proposition.proposition_id,
                temporal_relation=temporal_relation,
                content_relation=content_relation,
                state_relation=state_relation,
            )
        )
        store.add_relation(relations[-1])

    store.add(new_proposition)
    return relations