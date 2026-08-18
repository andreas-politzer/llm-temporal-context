"""
Testet Lifecycle-Decay-Handling in query.py (18.08.). Kostenlos,
InMemoryStore, von Hand konstruierte Objekte. Fünf Minimalfälle aus
Temporal Continuity/Lifecycle-Decay Contract v0.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition
from tcl.query import resolve_current_state, format_answer
from tcl.relation import PairwiseRelation, SemanticCompatibility, StateRelation, TemporalRelation
from tcl.store import InMemoryStore
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def bounded_prop(text, start, end, assertion_time):
    from tcl.proposition import TemporalInterval
    return Proposition(
        proposition_text=text, assertion_status=AssertionStatus.ASSERTED,
        assertion_time=assertion_time,
        normalized_temporal_reference=TemporalInterval(start=start, end=end),
    )


def open_prop(text, start, assertion_time):
    from tcl.proposition import TemporalInterval
    return Proposition(
        proposition_text=text, assertion_status=AssertionStatus.ASSERTED,
        assertion_time=assertion_time,
        normalized_temporal_reference=TemporalInterval(start=start, end=None),
    )


def main() -> None:
    print("=== Fall 1: verfallen, nicht abgelöst ===")
    store = InMemoryStore()
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Test", datetime(2026, 1, 1))
    a = bounded_prop("Der Vertrag mit Anbieter A läuft bis Juni 2026.", datetime(2026, 1, 1), datetime(2026, 6, 30), datetime(2026, 1, 1))
    store.ingest_propositions(turn, [a], [])
    result1 = resolve_current_state(store, [a.proposition_id], query_time=datetime(2026, 8, 18))
    check("Fall 1: nicht aufgelöst (verfallen)", result1.resolved, False)
    print(f"  -> {format_answer(result1)}")

    print("\n=== Fall 2: offenes Intervall verfällt nie ===")
    store2 = InMemoryStore()
    conv2 = store2.add_conversation()
    turn2 = store2.add_turn(conv2, "Test", datetime(2026, 1, 1))
    b = open_prop("Seit Dienstag arbeiten wir mit Anbieter B.", datetime(2026, 1, 6), datetime(2026, 1, 6))
    store2.ingest_propositions(turn2, [b], [])
    result2 = resolve_current_state(store2, [b.proposition_id], query_time=datetime(2026, 8, 18))
    check("Fall 2: weiterhin aufgelöst (kein Decay)", result2.resolved, True)

    print("\n=== Fall 3: begrenzt, Abfragezeit noch innerhalb ===")
    store3 = InMemoryStore()
    conv3 = store3.add_conversation()
    turn3 = store3.add_turn(conv3, "Test", datetime(2026, 1, 1))
    c = bounded_prop("Der Vertrag mit Anbieter A läuft bis Juni 2026.", datetime(2026, 1, 1), datetime(2026, 6, 30), datetime(2026, 1, 1))
    store3.ingest_propositions(turn3, [c], [])
    result3 = resolve_current_state(store3, [c.proposition_id], query_time=datetime(2026, 3, 1))
    check("Fall 3: aufgelöst (noch nicht verfallen)", result3.resolved, True)

    print("\n=== Fall 4: begrenzt UND explizit abgelöst ===")
    store4 = InMemoryStore()
    conv4 = store4.add_conversation()
    turn4a = store4.add_turn(conv4, "Test", datetime(2026, 1, 1))
    turn4b = store4.add_turn(conv4, "Test", datetime(2026, 5, 1))
    d1 = bounded_prop("Der Vertrag mit Anbieter A läuft bis Juni 2026.", datetime(2026, 1, 1), datetime(2026, 6, 30), datetime(2026, 1, 1))
    store4.ingest_propositions(turn4a, [d1], [])
    d2 = open_prop("Seit Mai arbeiten wir mit Anbieter C.", datetime(2026, 5, 1), datetime(2026, 5, 1))
    rel = PairwiseRelation(d1.proposition_id, d2.proposition_id, TemporalRelation.OVERLAP, SemanticCompatibility.INCOMPATIBLE, StateRelation.SUPERSEDES)
    store4.ingest_propositions(turn4b, [d2], [rel])
    result4 = resolve_current_state(store4, [d1.proposition_id, d2.proposition_id], query_time=datetime(2026, 8, 18))
    check("Fall 4: aufgelöst (C ist der Stand)", result4.resolved, True)
    check("Fall 4: last_stated ist Anbieter C", result4.last_stated.proposition_id, d2.proposition_id)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()