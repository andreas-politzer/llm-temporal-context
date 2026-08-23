"""
Query / Current-State Resolution — Architecture Contract v0, Schritt 9.

Update 18.08. (Lifecycle-Decay Contract): resolve_current_state bekommt
jetzt einen optionalen query_time-Parameter (Abfragezeitpunkt, externes
Kontext-Metadatum wie assertion_time - NICHT vom LLM erzeugt). Damit
kann eine Proposition mit bekanntem, überschrittenem Gültigkeitsende
(normalized_temporal_reference.end < query_time) als verfallen erkannt
werden, auch wenn nie eine neue Proposition sie explizit abgelöst hat -
der ursprüngliche Motivationsfall des Projekts (Zertifikat "gültig bis
Juni 2026", abgefragt im August). Offene Intervalle (kein Ende gesetzt)
verfallen NIE von selbst - nur SUPERSEDES kann sie ablösen.

Kein Raten in beide Richtungen: eine verfallene, nicht abgelöste
Proposition führt zu resolved=False mit explizitem Decay-Grund, nicht
zu einer stillschweigenden "gilt noch"-Antwort und auch nicht zu einer
erfundenen "gilt nicht mehr"-Aussage.

query_time ist optional (Default None) - ohne query_time wird KEIN
Decay geprüft, Verhalten bleibt wie vor dem 18.08. (Rückwärtskompatibilität
mit bestehenden Tests, die query_time nicht kennen).

Negative Verantwortung (unverändert): bewertet oder überschreibt KEINE
Relationen, liest ausschließlich, was Schritt 6/7 bereits abgelegt haben.
Decay-Prüfung ist rein deterministisch (Datumsvergleich), kein LLM.
"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from .proposition import Proposition
from .relation import StateRelation

_MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def _format_month_year(dt: datetime) -> str:
    return f"{_MONTHS_DE[dt.month - 1]} {dt.year}"


@dataclass(frozen=True)
class QueryResult:
    resolved: bool
    last_stated: Optional[Proposition] = None
    contradicts: List[Proposition] = field(default_factory=list)
    unclear: List[Proposition] = field(default_factory=list)
    temporally_unanchored: List[Proposition] = field(default_factory=list)
    decayed: List[Proposition] = field(default_factory=list)
    reason: Optional[str] = None


def _is_decayed(proposition: Proposition, query_time: Optional[datetime]) -> bool:
    if query_time is None:
        return False
    ref = proposition.normalized_temporal_reference
    if ref is None or ref.end is None:
        return False  # offenes Intervall verfällt nie von selbst
    return ref.end < query_time


def resolve_current_state(
    store, proposition_ids: List[str], query_time: Optional[datetime] = None
) -> QueryResult:
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

    for candidate in propositions:
        if candidate.proposition_id == last_stated.proposition_id:
            continue
        rel = store.get_relation_between(last_stated.proposition_id, candidate.proposition_id)
        was_superseded = (
            rel is not None
            and rel.state_relation == StateRelation.SUPERSEDES
            and rel.proposition_a_id == last_stated.proposition_id
        )
        if was_superseded:
            return QueryResult(
                resolved=False,
                temporally_unanchored=[p for p in propositions if p.assertion_time is None],
                reason=(
                    f'"{last_stated.proposition_text}" wurde laut gespeicherter Relation '
                    f'bereits durch "{candidate.proposition_text}" abgelöst, deren genauer '
                    f'Zeitpunkt aber unbekannt ist — kein eindeutiger aktueller Stand feststellbar.'
                ),
            )

    # Decay-Prüfung: last_stated selbst könnte trotz "zeitlich letzte
    # Behauptung" bereits über sein bekanntes Gültigkeitsende hinaus sein.
    if _is_decayed(last_stated, query_time):
        end = last_stated.normalized_temporal_reference.end
        return QueryResult(
            resolved=False,
            last_stated=last_stated,
            reason=(
                f'Die bekannte Gültigkeit ist abgelaufen: Zuletzt bekannter Stand war '
                f'"{last_stated.proposition_text}" (gültig bis {_format_month_year(end)}), '
                f'aktuelle Abfrage: {_format_month_year(query_time)}. Ob es seither eine '
                f'Verlängerung oder Änderung gab, ist nicht bekannt.'
            ),
        )

    others = [p for p in propositions if p.proposition_id != last_stated.proposition_id]

    contradicts: List[Proposition] = []
    unclear: List[Proposition] = []
    unresolved: List[Proposition] = []
    anchored_gap: List[Proposition] = []

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

    temporally_unanchored = [p for p in others if p.assertion_time is None]
    decayed = [p for p in others if _is_decayed(p, query_time)]

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
            decayed=decayed,
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
        decayed=decayed,
    )


def format_answer(result: QueryResult) -> str:
    if not result.resolved and result.last_stated is None:
        return f"Nicht auflösbar: {result.reason}"

    if not result.resolved and result.reason and not result.contradicts and not result.unclear:
        # Deckt Decay- und Supersede-durch-unverankert-Fälle ab: reason
        # trägt hier bereits die vollständige Aussage.
        return result.reason

    if result.resolved and not result.temporally_unanchored and not result.decayed:
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
    if result.decayed:
        named = ", ".join(p.proposition_text for p in result.decayed)
        parts.append(f"Bereits abgelaufen (informativ): {named}.")
    if result.reason:
        parts.append(result.reason)
    return " ".join(parts)

def classify_moment(interval, query_time: datetime) -> str:
    """
    Beantwortet eine andere Frage als resolve_current_state: nicht
    "was gilt unter mehreren Propositionen", sondern "wie verhält
    sich EIN Zeitpunkt zu JETZT". Grundlage für Projection/upcoming
    (Temporal-Context-Frame Contract v0, 23.08.).

    Gibt zurück: "upcoming" | "due" | "past" | "unknown".
    """
    if interval is None or interval.start is None:
        return "unknown"

    event_date = interval.start.date()
    query_date = query_time.date()

    if event_date > query_date:
        return "upcoming"
    elif event_date == query_date:
        return "due"
    else:
        return "past"