"""
Query / Current-State Resolution — Architecture Contract v0, Schritt 9.

Update 18.08.: Missing-Time-Handling vollständig durchdacht (siehe
Decision Persistenz-Architektur). Kein stiller Fallback auf "aktuell"
bei fehlendem assertion_time - das wäre genau die falsche Sicherheit,
die dieser Layer verhindern soll. Stattdessen: bereits gespeicherte
Relationen (auch über TRANSITION-Dominanz bei fehlendem Zeitbezug,
siehe Case C in test_known_cases.py) werden genutzt, wo vorhanden.
Nur wenn WEDER Zeitbezug NOCH eine gespeicherte Relation existiert,
wird das Ergebnis ehrlich als nicht auflösbar markiert - kein Crash,
kein Raten.

Negative Verantwortung (unverändert): bewertet oder überschreibt KEINE
Relationen, liest ausschließlich, was Schritt 6/7 bereits abgelegt haben.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .proposition import Proposition
from .relation import StateRelation


@dataclass(frozen=True)
class QueryResult:
    resolved: bool
    last_stated: Optional[Proposition] = None
    contradicts: List[Proposition] = field(default_factory=list)
    unclear: List[Proposition] = field(default_factory=list)
    temporally_unanchored: List[Proposition] = field(default_factory=list)
    reason: Optional[str] = None


def resolve_current_state(store, proposition_ids: List[str]) -> QueryResult:
    propositions = [store.get_by_id(pid) for pid in proposition_ids]
    if any(p is None for p in propositions):
        raise ValueError("Eine übergebene proposition_id existiert nicht im Store")

    anchored = [p for p in propositions if p.assertion_time is not None]
    unanchored = [p for p in propositions if p.assertion_time is None]

    if not anchored:
        return QueryResult(
            resolved=False,
            reason="Keine der betrachteten Propositionen hat einen bekannten Zeitpunkt — die zeitliche Reihenfolge ist vollständig unbekannt.",
            temporally_unanchored=unanchored,
        )

    last_stated = max(anchored, key=lambda p: p.assertion_time)

    # Prüfen, ob der gewählte last_stated-Kandidat bereits von einer ANDEREN
    # Proposition supersedet wurde (auch einer zeitlich unverankerten) -
    # sonst würde eine bereits bekannte Ablösung ignoriert, nur weil ihr
    # Zeitpunkt unbekannt ist. Siehe Fund 18.08.
    for candidate in propositions:
        if candidate.proposition_id == last_stated.proposition_id:
            continue
        rel = store.get_relation_between(last_stated.proposition_id, candidate.proposition_id)
        # Richtung prüfen: last_stated wurde nur dann abgelöst, wenn last_stated
        # die ÄLTERE Seite ist (proposition_a) und candidate sie supersedet (b).
        # Andersrum (last_stated supersedet candidate) ist genau das erwartete,
        # korrekte Ergebnis, kein Problem.
        was_superseded = (
            rel is not None
            and rel.state_relation == StateRelation.SUPERSEDES
            and rel.proposition_a_id == last_stated.proposition_id
        )
        if was_superseded:
            # last_stated wurde nachweislich abgelöst - kann nicht als
            # "zuletzt behauptet" gelten, auch wenn die Ablöse-Proposition
            # selbst keinen bekannten Zeitpunkt hat.
            return QueryResult(
                resolved=False,
                temporally_unanchored=[p for p in propositions if p.assertion_time is None],
                reason=(
                    f'"{last_stated.proposition_text}" wurde laut gespeicherter Relation '
                    f'bereits durch "{candidate.proposition_text}" abgelöst, deren genauer '
                    f'Zeitpunkt aber unbekannt ist — kein eindeutiger aktueller Stand feststellbar.'
                ),
            )

    others = [p for p in propositions if p.proposition_id != last_stated.proposition_id]

    contradicts: List[Proposition] = []
    unclear: List[Proposition] = []
    unresolved: List[Proposition] = []
    anchored_gap = []

    for other in others:
        relation = store.get_relation_between(last_stated.proposition_id, other.proposition_id)
        if relation is None:
            if other.assertion_time is None:
                unresolved.append(other)
            else:
                anchored_gap.append(other)
            continue

        if relation.state_relation == StateRelation.CONTRADICTS:
            contradicts.append(other)
        elif relation.state_relation == StateRelation.UNDETERMINED:
            unclear.append(other)
        # SUPERSEDES und CONTINUES: keine offene Frage

        if other.assertion_time is None:
            # informativ, unabhängig vom Relationsergebnis: Zeitpunkt bleibt unbekannt
            unclear_or_contradicts = other in contradicts or other in unclear
            pass  # wird unten gesammelt

    temporally_unanchored = [p for p in others if p.assertion_time is None]

    if anchored_gap:
        ids = ", ".join(p.proposition_id for p in anchored_gap)
        raise ValueError(
            f"Keine gespeicherte Relation zwischen {last_stated.proposition_id} "
            f"und zeitlich verankerten Propositionen ({ids}). Entweder ein "
            f"Pipeline-Vertragsbruch (Schritt 8), oder eine NOT_ASSERTED-Proposition "
            f"wurde an resolve_current_state übergeben (Vorbedingung: nur ASSERTED-"
            f"Propositionen, analog zur Vorbedingung von process_new_proposition)."
        )

    if unresolved:
        names = ", ".join(p.proposition_text for p in unresolved)
        return QueryResult(
            resolved=False,
            last_stated=last_stated,
            contradicts=contradicts,
            unclear=unclear,
            temporally_unanchored=temporally_unanchored,
            reason=(
                f"Mindestens eine Proposition ohne bekannten Zeitpunkt konnte nicht "
                f"eingeordnet werden, da keine Relation zu ihr vorliegt: {names}"
            ),
        )

    resolved = not contradicts and not unclear
    return QueryResult(
        resolved=resolved,
        last_stated=last_stated,
        contradicts=contradicts,
        unclear=unclear,
        temporally_unanchored=temporally_unanchored,
    )


def format_answer(result: QueryResult) -> str:
    if not result.resolved and result.last_stated is None:
        return f"Nicht auflösbar: {result.reason}"

    if result.resolved and not result.temporally_unanchored:
        return f"Zuletzt behaupteter Stand: {result.last_stated.proposition_text}"

    parts = [f"Zuletzt behaupteter Stand: {result.last_stated.proposition_text}."]
    if result.contradicts:
        named = ", ".join(p.proposition_text for p in result.contradicts)
        parts.append(f"Im Widerspruch dazu: {named}.")
    if result.unclear:
        named = ", ".join(p.proposition_text for p in result.unclear)
        parts.append(f"Beziehung ungeklärt zu: {named}.")
    if result.temporally_unanchored:
        named = ", ".join(p.proposition_text for p in result.temporally_unanchored)
        parts.append(f"Zeitpunkt unbekannt bei: {named}.")
    if result.reason:
        parts.append(result.reason)
    return " ".join(parts)