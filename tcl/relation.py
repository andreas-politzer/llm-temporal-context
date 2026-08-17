"""
PairwiseRelation — Konsistenz ist eine Relation, kein Attribut einer
einzelnen Proposition (empirisch etabliert im Reference-Time-Test und
den Fall-D-Ergebnissen des Cross-Turn-Tests, 16.08.2026).

Bekannter, bewusst offener Punkt (siehe Chat, nicht Teil von v0):
Relationen sind hier strikt paarweise. Aggregation über 3+ gleichzeitig
relevante Propositionen ist nicht Teil dieses Moduls — das ist Aufgabe
des noch zu bauenden Query Layer, nicht der Engine.

Update 17.08.2026 (Architecture Contract v0, Schritt 7; siehe
Decisions/2026-08-17 State-Relation - Storage-Query-Trennung und
Transition-Dominanz, inkl. Addendum): das ursprüngliche
resolve_consistency() / ConsistencyStatus reichte nicht aus, um saubere
Zustandsablösung (Supersession) von echtem Widerspruch zu unterscheiden,
ohne eine domänenabhängige Zeitlücken-Heuristik einzuführen.
StateRelation / resolve_state_relation() ersetzen das fachlich
vollständig. Per grep (17.08.) bestätigt unbenutzt außerhalb dieses
Moduls und deshalb entfernt, nicht nur deprecated.

DISJOINT bleibt weiterhin ein unbenutztes Feld (siehe Session Handoff
17.08.: "DISJOINT ist definiert, wird aber nie erzeugt"). compare_intervals()
in temporal_engine.py erzeugt es an keiner Stelle. Das wurde in der
heutigen Architekturrunde bewusst NICHT mitbehandelt — eigener,
noch offener Punkt, keine Lösung hier vorweggenommen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .proposition import TransitionType


class TemporalRelation(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    DISJOINT = "DISJOINT"  # weiterhin nie erzeugt, siehe Modul-Docstring
    UNDETERMINED = "UNDETERMINED"


class SemanticCompatibility(str, Enum):
    """Entspricht content_relation im Architecture Contract v0, Schritt 7a."""

    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNDETERMINED = "UNDETERMINED"


class StateRelation(str, Enum):
    """
    Architecture Contract v0, Schritt 7b. Ersetzt ConsistencyStatus
    vollständig (nicht additiv) — Eigenschaft des PAARS, nicht einer
    einzelnen Proposition.
    """

    CONTINUES = "CONTINUES"
    SUPERSEDES = "SUPERSEDES"
    CONTRADICTS = "CONTRADICTS"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class PairwiseRelation:
    proposition_a_id: str
    proposition_b_id: str
    temporal_relation: TemporalRelation
    content_relation: SemanticCompatibility
    state_relation: StateRelation


def resolve_state_relation(
    temporal_relation: TemporalRelation,
    content_relation: SemanticCompatibility,
    transition_type_a: TransitionType = TransitionType.BARE,
    transition_type_b: TransitionType = TransitionType.BARE,
) -> StateRelation:
    """
    Architecture Contract v0, Schritt 7b — finalisierte Fassung.

    Validiert gegen die zwei einzigen Fälle in test_known_cases.py, die
    tatsächlich eine volle Consistency-Prüfung durchführen:

    - Fall 3 (zwei "aktuell"-Propositionen, 15 Min. auseinander, kein
      TRANSITION-Signal): temporal_relation=BEFORE (real berechnet, kein
      OVERLAP), content=INCOMPATIBLE, kein TRANSITION -> UNDETERMINED.
      Keine Zeitlücken-Heuristik nötig, keine Default-Persistenz.

    - Case B (Freitag "aktuell Jira" vs. Donnerstag "seit Dienstag
      Linear", d2 trägt TRANSITION): temporal_relation=OVERLAP (real,
      aus Textevidenz "seit Dienstag" + Punkt direkt im Intervall) ->
      CONTRADICTS, UNABHÄNGIG vom TRANSITION-Signal auf d2. Echte
      Überlappung widerlegt die Transition-Behauptung. Das war der
      Fund, der die ursprünglich zu grobe "TRANSITION dominiert immer"-
      Regel korrigiert hat.

    Regel:

      content_relation == UNDETERMINED
          -> UNDETERMINED

      content_relation == COMPATIBLE
          -> CONTINUES (kein Konflikt, keine Ablösung nötig)

      content_relation == INCOMPATIBLE:
          temporal_relation == OVERLAP (aus echter Text-/Intervall-
          Evidenz — seit Verwerfen von Default-Persistenz entsteht
          OVERLAP nie mehr synthetisch)
              -> CONTRADICTS, unabhängig von transition_type

          sonst (BEFORE/AFTER/UNDETERMINED/DISJOINT — Engine hat keine
          positive Überlappungs-Evidenz):
              trägt a ODER b transition_type=TRANSITION -> SUPERSEDES
              sonst -> UNDETERMINED (keine Zeitlücken-Heuristik)

    Wichtiger Nebeneffekt dieser Regel (siehe Case C in
    test_known_cases.py): Auch bei temporal_relation=UNDETERMINED (z.B.
    weil assertion_time einer Proposition fehlt) kann ein explizites
    TRANSITION-Signal SUPERSEDES begründen — die Engine muss die
    Zeitordnung nicht kennen, wenn die Extraction bereits einen
    Zustandsbruch behauptet.

    Bindet KEIN konkretes Propositions-Paar — das ist bereits durch die
    Aufrufstelle (Schritt 5/6) geschehen. transition_type=TRANSITION ist
    hier Evidenz, keine vorab feststehende Relation (siehe proposition.py).
    """
    if content_relation == SemanticCompatibility.UNDETERMINED:
        return StateRelation.UNDETERMINED

    if content_relation == SemanticCompatibility.COMPATIBLE:
        return StateRelation.CONTINUES

    # content_relation == INCOMPATIBLE
    if temporal_relation == TemporalRelation.OVERLAP:
        return StateRelation.CONTRADICTS

    if (
        transition_type_a == TransitionType.TRANSITION
        or transition_type_b == TransitionType.TRANSITION
    ):
        return StateRelation.SUPERSEDES

    return StateRelation.UNDETERMINED
