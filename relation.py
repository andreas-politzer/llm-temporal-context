"""
PairwiseRelation — Konsistenz ist eine Relation, kein Attribut einer
einzelnen Proposition (empirisch etabliert im Reference-Time-Test und
den Fall-D-Ergebnissen des Cross-Turn-Tests, 16.08.2026).

Bekannter, bewusst offener Punkt (siehe Chat, nicht Teil von v0):
Relationen sind hier strikt paarweise. Aggregation über 3+ gleichzeitig
relevante Propositionen ist nicht Teil dieses Moduls — das ist Aufgabe
des noch zu bauenden Query Layer, nicht der Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TemporalRelation(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    DISJOINT = "DISJOINT"
    UNDETERMINED = "UNDETERMINED"


class SemanticCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNDETERMINED = "UNDETERMINED"


class ConsistencyStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    CONTRADICTORY = "CONTRADICTORY"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class PairwiseRelation:
    proposition_a_id: str
    proposition_b_id: str
    temporal_relation: TemporalRelation
    semantic_compatibility: SemanticCompatibility
    consistency_status: ConsistencyStatus


def resolve_consistency(
    temporal_relation: TemporalRelation,
    semantic_compatibility: SemanticCompatibility,
) -> ConsistencyStatus:
    """
    Kombiniert Engine-Ergebnis (temporal_relation) und LLM-Ergebnis
    (semantic_compatibility) zu einem Konsistenzstatus.

    Regel, direkt aus dem X4a/X4b- und Fall-D-Befund abgeleitet:
    Ein Widerspruch entsteht nur, wenn sich die Propositionen zeitlich
    ÜBERLAPPEN und inhaltlich UNVEREINBAR sind. Zeitliche Trennung
    (BEFORE/AFTER/DISJOINT) macht inhaltlich unvereinbare Werte
    unproblematisch (Supersession-Fall, kein Widerspruch).
    """
    if (
        temporal_relation == TemporalRelation.UNDETERMINED
        or semantic_compatibility == SemanticCompatibility.UNDETERMINED
    ):
        return ConsistencyStatus.UNDETERMINED

    if (
        temporal_relation == TemporalRelation.OVERLAP
        and semantic_compatibility == SemanticCompatibility.INCOMPATIBLE
    ):
        return ConsistencyStatus.CONTRADICTORY

    return ConsistencyStatus.CONSISTENT
