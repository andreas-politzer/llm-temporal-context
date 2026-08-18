"""
process_turn — End-to-End-Verkabelung von Schritt 1-4 des Architecture
Contract v0 für EINEN Turn. Erste vollständige Pipeline von Rohtext bis
zu vollständig angereicherten Propositionen (bereit für Schritt 5+,
siehe tcl/pipeline.py für die Fortsetzung).

CONTRACT:
Input: turn_text (Rohtext) + assertion_time (Kontext-Metadatum, von
außen - z.B. der tatsächliche Zeitstempel der Nutzeräußerung. Wird
NICHT von einem LLM-Schritt erzeugt, siehe Temporal-Expression
Contract v0).
Output: list[Proposition], vollständig (assertion_status,
transition_type, raw_temporal_expression, normalized_temporal_reference
alle gesetzt, decomposition_group_id turn-basiert von Schritt 1).

Reihenfolge ist eine echte Abhängigkeitskette, kein künstliches
Sequenzieren: Schritt 2 braucht den Output von Schritt 1 (die
Propositionen selbst), Schritt 3 braucht den von Schritt 2
(assertion_status beeinflusst z.B. bei Konditionalen, welche
Propositionen überhaupt zeitlich sinnvoll eingeordnet werden können -
wobei aktuell auch NOT_ASSERTED-Propositionen einen Zeitausdruck
bekommen, siehe offene Frage unten).

GUI-Hinweis (18.08.): drei sequenzielle API-Aufrufe pro Turn -> dreifache
Latenz gegenüber einem Einzelaufruf. Für eine spätere Oberfläche mit
Live-Feedback könnte das spürbar sein. Nicht heute gelöst - Kandidat für
Streaming von Zwischenständen (z.B. "Propositionen erkannt..." bevor
der Rest fertig ist), wenn eine GUI ansteht.

OFFENE FRAGE, hier bewusst nicht entschieden: Sollten NOT_ASSERTED-
Propositionen (z.B. aus Konditionalen) überhaupt durch Schritt 3
laufen? Sie werden laut Architecture Contract v0 "nach Schritt 2
NICHT gespeichert" - aber diese Funktion deckt nur Schritt 1-4 ab,
nicht das Verwerfen selbst (das wäre Aufgabe des Aufrufers vor
Schritt 5/pipeline.py). Aktuell laufen ALLE Propositionen durch
Schritt 3, auch NOT_ASSERTED - unnötiger API-Aufwand für Propositionen,
die ohnehin nie gespeichert werden. Kandidat für Optimierung, nicht
heute umgesetzt (Robustheit/Kosten-Vorzeitigkeit vermeiden, siehe
bisheriges Prinzip).
"""

from __future__ import annotations

from datetime import datetime

from .assertion_check import assertion_check_fn
from .extraction import extract_propositions_fn
from .proposition import Proposition
from .temporal_engine import normalize
from .temporal_expression import temporal_expression_fn


def process_turn(turn_text: str, assertion_time: datetime) -> list[Proposition]:
    """
    Schritte 1-4 in einem Durchlauf. Siehe Modul-Docstring für Contract
    und offene Punkte.
    """
    extracted = extract_propositions_fn(turn_text)
    with_assertion = assertion_check_fn(turn_text, extracted)
    with_temporal_expr = temporal_expression_fn(turn_text, with_assertion)

    result = []
    for prop in with_temporal_expr:
        normalized = normalize(prop.raw_temporal_expression, assertion_time=assertion_time)
        result.append(
            Proposition(
                proposition_text=prop.proposition_text,
                assertion_status=prop.assertion_status,
                assertion_time=assertion_time,
                raw_temporal_expression=prop.raw_temporal_expression,
                normalized_temporal_reference=normalized,
                transition_type=prop.transition_type,
                decomposition_group_id=prop.decomposition_group_id,
            )
        )
    return result