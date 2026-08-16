"""
Deterministische Temporal Engine.

Kernregel des Tages (Rollentrennung-Test, 16.08.2026): das LLM extrahiert
nur assertion_time + raw_temporal_expression. JEDE Datumsarithmetik
passiert hier, nicht im Modell.

Wichtiger, ehrlicher Scope-Hinweis: normalize() versteht absichtlich nur
das kleine Vokabular, das im heutigen Testkorpus tatsächlich vorkam
("currently"/"aktuell", "since X", "from X through Y", "N weeks/days
ago", ein festes Datum). Das ist kein allgemeiner NLU-Parser für
natürliche Sprache — echte raw_temporal_expression-Vielfalt braucht ein
LLM zur Extraktion, nur die anschließende Umrechnung in Kalenderdaten ist
hier deterministisch. Ausdrücklich nicht abgedeckt: Aussagen mit "niemals"
(erfordern ein Negations-/Universalitäts-Modell, nicht nur ein Intervall
— siehe R-1-Diskussion im Chat, bewusst nicht in v0).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from .proposition import TemporalInterval
from .relation import TemporalRelation

_WEEKDAYS = {
    "monday": 0, "montag": 0,
    "tuesday": 1, "dienstag": 1,
    "wednesday": 2, "mittwoch": 2,
    "thursday": 3, "donnerstag": 3,
    "friday": 4, "freitag": 4,
    "saturday": 5, "samstag": 5,
    "sunday": 6, "sonntag": 6,
}


def _weekday_on_or_before(reference: datetime, weekday_name: str) -> Optional[datetime]:
    target = _WEEKDAYS.get(weekday_name.lower())
    if target is None:
        return None
    delta = (reference.weekday() - target) % 7
    return (reference - timedelta(days=delta)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def normalize(raw_temporal_expression: str, assertion_time: Optional[datetime]) -> TemporalInterval:
    """
    Übersetzt einen rohen, extrahierten Zeitausdruck + Äußerungszeitpunkt
    in ein normalisiertes Intervall. Rein regelbasiert, kein LLM-Aufruf.
    """
    if raw_temporal_expression is None:
        return TemporalInterval(start=None, end=None)

    text = raw_temporal_expression.strip().lower()

    # "currently" / "aktuell" -> Punkt am Äußerungszeitpunkt
    if text in ("currently", "aktuell", "nach wie vor", "still", "weiterhin"):
        if assertion_time is None:
            return TemporalInterval(start=None, end=None)  # UNDETERMINED-Fall
        return TemporalInterval(start=assertion_time, end=assertion_time)

    # "since <weekday>" -> offenes, ANDAUERNDES Intervall [weekday, ...]
    # WICHTIG: end=None, nicht end=assertion_time - "seit Dienstag" heißt
    # "ab Dienstag und andauernd", nicht "nur bis zum Moment der Aussage".
    # (Bug gefunden und korrigiert beim ersten Testlauf gegen Case B.)
    m = re.match(r"since (\w+)", text)
    if m and assertion_time is not None:
        start = _weekday_on_or_before(assertion_time, m.group(1))
        if start is not None:
            return TemporalInterval(start=start, end=None)

    # "from <weekday> through <weekday>" -> fest fixiertes Intervall,
    # UNABHÄNGIG von assertion_time (das ist genau der R-1-Befund)
    m = re.match(r"from (\w+) (?:through|to|until) (\w+)", text)
    if m:
        # Referenzpunkt für die Wochentag-Auflösung: falls assertion_time
        # fehlt, versuchen wir es trotzdem NICHT zu raten -> UNDETERMINED,
        # außer beide Wochentage sind eindeutig genug (v0: hier bewusst
        # konservativ, braucht assertion_time als grobe Woche-Referenz)
        if assertion_time is not None:
            start = _weekday_on_or_before(assertion_time, m.group(1))
            end = _weekday_on_or_before(assertion_time, m.group(2))
            if start is not None and end is not None:
                return TemporalInterval(start=start, end=end)

    # "<N> weeks/days ago" -> Punkt, relativ zu assertion_time
    m = re.match(r"(\d+)\s+(day|days|week|weeks)\s+ago", text)
    if m and assertion_time is not None:
        n = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(weeks=n) if unit.startswith("week") else timedelta(days=n)
        point = assertion_time - delta
        return TemporalInterval(start=point, end=point)

    return TemporalInterval(start=None, end=None)  # nicht erkannt -> UNDETERMINED


def compare_intervals(a: TemporalInterval, b: TemporalInterval) -> TemporalRelation:
    """
    Reine Intervall-Arithmetik. Keine Textinterpretation mehr an dieser
    Stelle — a und b sind bereits normalisiert.

    Definitionen (final geklärt im Chat, 16.08.2026):
      BEFORE       — a endet vor b beginnt
      AFTER        — a beginnt nach b endet
      OVERLAP      — a und b teilen einen zeitlichen Bereich
      DISJOINT     — keine Überlappung, aber Richtung nicht bestimmbar
      UNDETERMINED — nicht genug Information für irgendeine Aussage
    """
    if a is None or b is None:
        return TemporalRelation.UNDETERMINED

    a_start, a_end = a.start, a.end
    b_start, b_end = b.start, b.end

    # Vollständig bestimmt: klare BEFORE/AFTER/OVERLAP-Berechnung möglich
    if None not in (a_start, a_end, b_start, b_end):
        if a_end < b_start:
            return TemporalRelation.BEFORE
        if b_end < a_start:
            return TemporalRelation.AFTER
        return TemporalRelation.OVERLAP  # Intervalle überschneiden sich

    # Teilweise offene Intervalle (z.B. "seit Dienstag", kein Enddatum):
    # ein offenes Ende wird als "andauernd bis mindestens jetzt" behandelt,
    # daher weiterhin vergleichbar, wenn der jeweils andere Rand bekannt ist
    if a_start is not None and a_end is None and b_start is not None and b_end is not None:
        # a läuft ab a_start unbegrenzt weiter; b ist [b_start, b_end]
        if b_end < a_start:
            return TemporalRelation.AFTER
        return TemporalRelation.OVERLAP
    if b_start is not None and b_end is None and a_start is not None and a_end is not None:
        if a_end < b_start:
            return TemporalRelation.BEFORE
        return TemporalRelation.OVERLAP

    return TemporalRelation.UNDETERMINED
