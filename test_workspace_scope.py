"""
Testet Workspace-Scope für Temporal Memory (21.08.). Kostenlos,
InMemoryStore. Beweist: search_temporal_memory findet Treffer über
mehrere Conversations hinweg (workspace-weit), nicht nur innerhalb
der aktuellen Conversation - genau der Fund vom Live-Test, der diesen
Contract ausgelöst hat.
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
    store = InMemoryStore()

    print("=== Simuliert: zwei GETRENNTE Chat-Sitzungen, wie an unterschiedlichen Tagen ===")
    conv1 = store.add_conversation()  # kein workspace_id -> Default
    turn1 = store.add_turn(conv1, "Am Montag haben wir über PostgreSQL gesprochen.", datetime(2026, 8, 19, 9, 0))
    prop1 = Proposition(
        proposition_text="Wir haben über PostgreSQL gesprochen.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 19, 9, 0),
        raw_temporal_expression="on monday",
        normalized_temporal_reference=normalize("on monday", assertion_time=datetime(2026, 8, 19, 9, 0)),
        transition_type=TransitionType.BARE,
        turn_id=turn1,
    )
    store.ingest_propositions(turn1, [prop1], [])

    print("\n=== ZWEITE, komplett neue Conversation (wie ein neuer Chat) ===")
    conv2 = store.add_conversation()  # ebenfalls kein workspace_id -> DERSELBE Default
    check("Beide Conversations sind unterschiedlich", conv1 != conv2, True)

    print("\n=== Suche aus der NEUEN Conversation heraus - muss den alten Treffer trotzdem finden ===")
    results = store.search_temporal_memory("PostgreSQL")
    check("Genau ein Treffer gefunden, obwohl in anderer Conversation gespeichert", len(results), 1)
    check("time_source ist EVENT (aufgelöstes Datum)", results[0]["time_source"], "EVENT")
    check("Zeitpunkt ist Montag 17.08.", results[0]["time"], datetime(2026, 8, 17))

    print("\n=== Regressionsschutz: unbekannter Begriff liefert leere Liste ===")
    check("Kein Treffer für unbekannten Begriff", store.search_temporal_memory("Kubernetes"), [])

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()