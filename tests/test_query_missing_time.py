"""
Testet den Missing-Time-Contract aus query.py (18.08.). Kostenlos,
InMemoryStore, von Hand konstruierte Objekte.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition
from tcl.query import resolve_current_state, format_answer
from tcl.relation import PairwiseRelation, SemanticCompatibility, StateRelation, TemporalRelation
from tcl.store import InMemoryStore


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Fall 1: Regression, beide verankert, normal aufgelöst ===")
    store = InMemoryStore()
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Test", datetime(2026, 8, 18, 10, 0))
    a = Proposition(proposition_text="Vertrag A gilt.", assertion_status=AssertionStatus.ASSERTED, assertion_time=datetime(2026, 1, 1))
    b = Proposition(proposition_text="Vertrag B gilt.", assertion_status=AssertionStatus.ASSERTED, assertion_time=datetime(2026, 6, 1))
    rel_ab = PairwiseRelation(a.proposition_id, b.proposition_id, TemporalRelation.BEFORE, SemanticCompatibility.INCOMPATIBLE, StateRelation.SUPERSEDES)
    store.ingest_propositions(turn, [a, b], [rel_ab])
    result = resolve_current_state(store, [a.proposition_id, b.proposition_id])
    check("Fall 1: aufgelöst", result.resolved, True)
    check("Fall 1: B ist zuletzt behauptet", result.last_stated.proposition_id, b.proposition_id)

    print("\n=== Fall 2: NOT_ASSERTED fälschlich übergeben -> ValueError ===")
    store2 = InMemoryStore()
    conv2 = store2.add_conversation()
    turn2 = store2.add_turn(conv2, "Test", datetime(2026, 8, 18, 10, 0))
    c = Proposition(proposition_text="Verankert.", assertion_status=AssertionStatus.ASSERTED, assertion_time=datetime(2026, 1, 1))
    d = Proposition(proposition_text="Hypothetisch.", assertion_status=AssertionStatus.NOT_ASSERTED, assertion_time=datetime(2026, 1, 2))
    store2.ingest_propositions(turn2, [c, d], [])
    try:
        resolve_current_state(store2, [c.proposition_id, d.proposition_id])
        check("Fall 2: ValueError wurde geworfen", False, True)
    except ValueError as e:
        check("Fall 2: ValueError wurde geworfen", True, True)
        print(f"  Meldung: {e}")

    print("\n=== Fall 3: keine einzige Proposition verankert -> resolved=False ===")
    store3 = InMemoryStore()
    conv3 = store3.add_conversation()
    turn3 = store3.add_turn(conv3, "Test", datetime(2026, 8, 18, 10, 0))
    e = Proposition(proposition_text="Ohne Zeitpunkt A.", assertion_status=AssertionStatus.ASSERTED)
    f = Proposition(proposition_text="Ohne Zeitpunkt B.", assertion_status=AssertionStatus.ASSERTED)
    store3.ingest_propositions(turn3, [e, f], [])
    result3 = resolve_current_state(store3, [e.proposition_id, f.proposition_id])
    check("Fall 3: nicht aufgelöst", result3.resolved, False)
    print(f"  Grund: {result3.reason}")

    print("\n=== Fall 4: verankerter Kandidat wurde durch unverankerte Proposition abgelöst ===")
    store4 = InMemoryStore()
    conv4 = store4.add_conversation()
    turn4 = store4.add_turn(conv4, "Test", datetime(2026, 8, 18, 10, 0))
    g = Proposition(proposition_text="Altes Abo läuft.", assertion_status=AssertionStatus.ASSERTED, assertion_time=datetime(2026, 1, 1))
    h = Proposition(proposition_text="Neues Abo ersetzt es.", assertion_status=AssertionStatus.ASSERTED)  # kein assertion_time
    rel_gh = PairwiseRelation(g.proposition_id, h.proposition_id, TemporalRelation.UNDETERMINED, SemanticCompatibility.INCOMPATIBLE, StateRelation.SUPERSEDES)
    store4.ingest_propositions(turn4, [g, h], [rel_gh])
    result4 = resolve_current_state(store4, [g.proposition_id, h.proposition_id])
    check("Fall 4: NICHT fälschlich als aufgelöst gemeldet", result4.resolved, False)
    print(f"  Grund: {result4.reason}")

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()