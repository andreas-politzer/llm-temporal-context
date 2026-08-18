"""
Schließt die letzte offene Lücke: get_all_propositions() wurde bisher
nur gegen PostgresStore getestet. Prüft hier, dass InMemoryStore
dasselbe Verhalten zeigt - identischer Contract, beide Implementierungen.
Komplett kostenlos, kein LLM-Aufruf, keine Domäne (rein strukturell).
"""

from tcl.proposition import AssertionStatus, Proposition
from tcl.store import InMemoryStore


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    store = InMemoryStore()
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Testeingabe", __import__("datetime").datetime(2026, 8, 18, 10, 0))

    asserted = Proposition(proposition_text="Eine behauptete Aussage.", assertion_status=AssertionStatus.ASSERTED)
    not_asserted = Proposition(proposition_text="Eine hypothetische Aussage.", assertion_status=AssertionStatus.NOT_ASSERTED)
    store.ingest_propositions(turn, [asserted, not_asserted], [])

    all_props = store.get_all_propositions(conv)
    check("get_all_propositions: beide Propositionen sichtbar (ASSERTED + NOT_ASSERTED)", len(all_props), 2)

    candidates = store.get_candidates(conv, asserted)
    check("get_candidates: nur die ASSERTED-Proposition", len(candidates), 1)

    conv2 = store.add_conversation()
    check("get_all_propositions: leere Conversation liefert leere Liste", store.get_all_propositions(conv2), [])

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()