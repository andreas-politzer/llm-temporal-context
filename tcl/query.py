"""
Query / Current-State Resolution — Architecture Contract v0, Schritt 9.

Vereinbarte v0-Regel (Chat 17.08., Minimalfälle mit Luna durchgerechnet):

Für eine explizit übergebene Menge von proposition_ids: Sei L die
zeitlich letzte Proposition (nach assertion_time) darin. Jede andere
Proposition, zu der L per gespeicherter Relation SUPERSEDES trägt, gilt
als abgelöst und wird nicht genannt (auch nicht bei mehreren
gleichzeitigen Konflikten anderswo — Ablösung ist keine offene Frage,
unabhängig davon, was sonst noch strittig ist).

Von den verbleibenden (nicht abgelösten) Propositionen: Ist die Menge
leer, ist L der eindeutige, zuletzt behauptete Stand. Sonst wird L
zusammen mit den verbleibenden genannt, GETRENNT gruppiert nach
CONTRADICTS ("im Widerspruch") und UNDETERMINED ("Beziehung ungeklärt")
— nie in einer gemeinsamen Liste vermischt, weil beides unterschiedliche
Aussagen sind (starke Evidenz für Widerspruch vs. schlicht fehlende
Evidenz).

CONTINUES-Relationen zwischen L und einer anderen Proposition werden
wie SUPERSEDES behandelt (keine offene Frage) — bewusste Vereinfachung,
nicht in den Minimalfällen explizit durchgerechnet, siehe Docstring
der Funktion unten.

Negative Verantwortung (siehe Architecture Contract v0, Schritt 9):
Diese Funktion bewertet oder überschreibt KEINE Relationen. Sie liest
ausschließlich, was Schritt 6/7 bereits im Store abgelegt haben.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .proposition import Proposition
from .relation import StateRelation
from .store import Store


@dataclass(frozen=True)
class QueryResult:
    last_stated: Proposition
    resolved: bool
    contradicts: List[Proposition] = field(default_factory=list)
    unclear: List[Proposition] = field(default_factory=list)


def resolve_current_state(store: Store, proposition_ids: List[str]) -> QueryResult:
    """
    Schritt 9. Setzt voraus, dass jede übergebene id im Store existiert
    und assertion_time gesetzt hat (v0-Einschränkung, nicht geprüft).

    CONTINUES-Relationen zwischen last_stated und einer anderen
    Proposition werden wie SUPERSEDES behandelt (keine offene Frage,
    nicht genannt). Begründet, nicht nur angenommen (siehe Chat
    17.08.): SUPERSEDES und CONTINUES sind beide Aussagen über "keine
    offene Frage" (Zustand abgelöst bzw. bestätigt/irrelevant), im
    Unterschied zu CONTRADICTS/UNDETERMINED, die beide "offene Frage"
    bedeuten. Für "was gilt aktuell" (diese Funktion) ist das die
    relevante Unterscheidung, nicht "was ist historisch passiert".
    Geprüft an zwei Minimalfällen: echte Bestätigung desselben Werts
    ("weiterhin Jira") und thematisch unabhängige Propositionen
    ("Wetter war schön") landen beide korrekt bei COMPATIBLE, beide
    ohne offene Frage für den aktuellen Zustand.
    """
    propositions = [store.get_by_id(pid) for pid in proposition_ids]
    if any(p is None for p in propositions):
        raise ValueError("Eine übergebene proposition_id existiert nicht im Store")
    if any(p.assertion_time is None for p in propositions):
        raise ValueError(
            "resolve_current_state setzt bekannte assertion_time voraus "
            "(v0-Einschränkung, unbekannte Zeitpunkte nicht behandelt)"
        )

    last_stated = max(propositions, key=lambda p: p.assertion_time)
    others = [p for p in propositions if p.proposition_id != last_stated.proposition_id]

    contradicts: List[Proposition] = []
    unclear: List[Proposition] = []

    for other in others:
        relation = store.get_relation_between(last_stated.proposition_id, other.proposition_id)
        if relation is None:
            raise ValueError(
                f"Keine gespeicherte Relation zwischen {last_stated.proposition_id} "
                f"und {other.proposition_id} — Vertragsbruch der Pipeline (Schritt 8)"
            )
        if relation.state_relation == StateRelation.CONTRADICTS:
            contradicts.append(other)
        elif relation.state_relation == StateRelation.UNDETERMINED:
            unclear.append(other)
        # SUPERSEDES und CONTINUES: keine offene Frage, nicht genannt

    resolved = not contradicts and not unclear
    return QueryResult(last_stated=last_stated, resolved=resolved, contradicts=contradicts, unclear=unclear)


def format_answer(result: QueryResult) -> str:
    """Reine Formatierungshilfe, keine Bewertungslogik — Text folgt Schritt-9-Policy."""
    if result.resolved:
        return f"Zuletzt behaupteter Stand: {result.last_stated.proposition_text}"

    parts = [f"Zuletzt behaupteter Stand: {result.last_stated.proposition_text}."]
    if result.contradicts:
        named = ", ".join(p.proposition_text for p in result.contradicts)
        parts.append(f"Im Widerspruch dazu: {named}.")
    if result.unclear:
        named = ", ".join(p.proposition_text for p in result.unclear)
        parts.append(f"Beziehung ungeklärt zu: {named}.")
    return " ".join(parts)