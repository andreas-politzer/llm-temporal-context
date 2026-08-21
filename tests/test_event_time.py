"""
Regressionstest für get_event_time / "on <weekday>" (19.08.). Ersetzt
den bisherigen reinen Live-Test durch einen automatisierten Beweis.
Kostenlos, InMemoryStore, kein API-Aufruf.

WICHTIGE GRENZE, nicht durch diesen Test aufgehoben: Dies bleibt
Notizbuch-Verhalten - die Proposition muss explizit über
ingest_proposition gespeichert werden, nichts passiert automatisch.
Der Test beweist nur, dass das Notizbuch korrekt arbeitet, nicht dass
es zu etwas anderem als einem Notizbuch geworden ist.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.store import InMemoryStore
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    wednesday = datetime(2026, 8, 19, 12, 24)

    print("=== 1. Engine allein: 'on monday' korrekt aufgelöst ===")
    interval = normalize("on monday", assertion_time=wednesday)
    check("on monday -> 17.08. als Punkt (start)", interval.start, datetime(2026, 8, 17))
    check("on monday -> 17.08. als Punkt (end)", interval.end, datetime(2026, 8, 17))

    print("\n=== 2. Volle Kette: Proposition speichern -> get_propositions_for_turn liefert Event-Zeit ===")
    store = InMemoryStore()
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Am Montag haben wir über PostgreSQL gesprochen.", wednesday)

    prop = Proposition(
        proposition_text="Wir haben über PostgreSQL gesprochen.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=wednesday,
        raw_temporal_expression="on monday",
        normalized_temporal_reference=normalize("on monday", assertion_time=wednesday),
        transition_type=TransitionType.BARE,
        turn_id=turn,
    )
    store.ingest_propositions(turn, [prop], [])

    fetched = store.get_propositions_for_turn(turn)
    check("Genau eine Proposition für diesen Turn gefunden", len(fetched), 1)
    check("Event-Start korrekt = Montag 17.08.", fetched[0].normalized_temporal_reference.start, datetime(2026, 8, 17))

    print("\n=== 3. Regressionsschutz: raw_temporal_expression=None liefert weiterhin kein Datum ===")
    turn2 = store.add_turn(conv, "Wir nutzen Jira.", wednesday)
    prop2 = Proposition(
        proposition_text="Wir nutzen Jira.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=wednesday,
        raw_temporal_expression=None,
        normalized_temporal_reference=normalize(None, assertion_time=wednesday),
        transition_type=TransitionType.BARE,
        turn_id=turn2,
    )
    store.ingest_propositions(turn2, [prop2], [])
    fetched2 = store.get_propositions_for_turn(turn2)
    check("Ohne Zeitausdruck: kein Event-Datum (start bleibt None)", fetched2[0].normalized_temporal_reference.start, None)

    print("\n=== 4. Message-Level-Timestamping: add_turn ohne assertion_time setzt Server-Zeit ===")
    turn3 = store.add_turn(conv, "Test ohne explizite Zeit.")
    turn3_time = store.get_turn_assertion_time(turn3)
    check("assertion_time wurde server-seitig gesetzt (nicht None)", turn3_time is not None, True)

    print("\nAlle Checks bestanden.")
    print("\nWICHTIGE ERINNERUNG: Dies bleibt explizites Notizbuch-Verhalten.")
    print("Keine automatische Erfassung ohne expliziten ingest_proposition-Aufruf.")


if __name__ == "__main__":
    main()