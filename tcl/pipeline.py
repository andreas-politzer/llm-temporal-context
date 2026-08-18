"""
Pipeline-Orchestrierung — verkabelt Store (Schritt 5), Temporal Engine
(Schritt 6) und resolve_state_relation (Schritt 7) zu einem Ablauf für
eine neu ankommende Proposition.

Update 18.08. (Decision: Persistenz-Architektur): process_new_proposition
speichert nicht mehr einzeln, sondern sammelt alle Relationen und
übergibt sie am Ende atomar an store.ingest_propositions(). Braucht
jetzt conversation_id (Scope für Candidate Retrieval) und turn_id
(für die Zuordnung der Proposition).

WICHTIG, unverändert seit 17.08.: content_relation wird bewusst NICHT
hier berechnet - Aufgabe der semantischen/LLM-Ebene, als externe
Abhängigkeit injiziert (content_relation_fn), nicht simuliert.

Vorbedingung: new_proposition muss assertion_status=ASSERTED haben.
NOT_ASSERTED-Propositionen durchlaufen diese Funktion nicht - sie
werden separat, ohne Relation Resolution, über store.ingest_propositions()
gespeichert (siehe tcl/ingest.py).
"""

from __future__ import annotations

from typing import Callable

from .proposition import Proposition
from .relation import PairwiseRelation, SemanticCompatibility, resolve_state_relation
from .store import InMemoryStore
from .temporal_engine import compare_intervals

ContentRelationFn = Callable[[Proposition, Proposition], SemanticCompatibility]


def process_new_proposition(
    store: InMemoryStore,
    conversation_id: str,
    turn_id: str,
    new_proposition: Proposition,
    content_relation_fn: ContentRelationFn,
) -> list[PairwiseRelation]:
    """
    Architecture Contract v0, Schritte 5-8 für EINE neue Proposition.
    Speichert jetzt atomar über ingest_propositions() (siehe Modul-
    Docstring), statt einzeln über add()/add_relation() wie vor dem
    18.08.

    Vorbedingung: new_proposition muss assertion_status=ASSERTED haben.
    NOT_ASSERTED-Propositionen verlassen die Pipeline bereits nach
    Schritt 2 (Assertion Check) und dürfen diese Funktion nie erreichen
    — kein Storage, keine Relation Resolution. Wird das verletzt, ist
    das ein Vertragsbruch des Aufrufers, keine Situation, die hier
    behandelt wird (kein Guard, kein stiller Early-Return — das würde
    Verantwortung aus Schritt 2 in Schritt 5 hineinziehen, siehe Chat
    17.08.).

    content_relation_fn(candidate, new_proposition) -> SemanticCompatibility
    ist von außen vorgegeben (semantische/LLM-Ebene) — kein Aufruf
    hier, keine eingebaute Heuristik.

    Schritt 8: new_proposition wird erst NACH der Relation Resolution
    gegen alle Kandidaten gespeichert, damit sie sich nicht selbst als
    Kandidat vorgelegt bekommt.
    """
    candidates = store.get_candidates(conversation_id, new_proposition)

    relations: list[PairwiseRelation] = []
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

    store.ingest_propositions(turn_id, [new_proposition], relations)
    return relations