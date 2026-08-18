"""
End-to-End-Test für ingest_turn: Rohtext -> Store -> Query, in einem
durchgängigen Fluss. Update 18.08.: nutzt InMemoryStore mit
conversation_id-Scoping und Audit-Trail-Persistierung von NOT_ASSERTED-
Propositionen (Decision: Persistenz-Architektur).
"""

from datetime import datetime

from tcl.ingest import ingest_turn
from tcl.query import resolve_current_state, format_answer
from tcl.store import InMemoryStore


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Voller Fluss, Fall 1: Jira -> Linear, SUPERSEDES, Query beantwortet korrekt ===")
    store = InMemoryStore()
    conv = store.add_conversation()
    ingest_turn("Wir nutzen aktuell Jira.", datetime(2026, 8, 10, 10, 0), store, conv)
    ingest_turn("Seit Dienstag nutzen wir Linear.", datetime(2026, 8, 13, 15, 0), store, conv)

    check("Fall 1: Store enthält beide Propositionen", len(store), 2)
    ids = store._propositions_by_conversation[conv]  # nur zu Testzwecken direkter Zugriff
    result = resolve_current_state(store, ids)
    check("Fall 1: eindeutig aufgelöst", result.resolved, True)
    print("  ->", format_answer(result))

    print("\n=== Voller Fluss, Konditional wird gespeichert, aber ohne Relationen (NEU seit 18.08.) ===")
    store2 = InMemoryStore()
    conv2 = store2.add_conversation()
    ingest_turn("Wenn das Budget reicht, wechseln wir zu Linear.", datetime(2026, 8, 17, 9, 0), store2, conv2)
    check("Konditional: 2 Propositionen gespeichert (Audit-Trail), keine Relationen", len(store2), 2)
    check("Konditional: keine Relationen entstanden", len(store2._relations), 0)

    print("\n=== Voller Fluss, gemischter Turn: eine ASSERTED, eine NOT_ASSERTED-Proposition ===")
    store3 = InMemoryStore()
    conv3 = store3.add_conversation()
    ingest_turn(
        "Wir nutzen Jira. Wenn das Budget reicht, wechseln wir zu Linear.",
        datetime(2026, 8, 17, 9, 0),
        store3,
        conv3,
    )
    check("Gemischt: alle 3 Propositionen gespeichert (1 ASSERTED + 2 NOT_ASSERTED)", len(store3), 3)
    check("Gemischt: nur 0 Relationen (nur 1 ASSERTED, kein Vergleichspartner)", len(store3._relations), 0)

    print("\n=== Scope-Test (NEU): zwei Conversations bleiben getrennt ===")
    store4 = InMemoryStore()
    conv_a = store4.add_conversation()
    conv_b = store4.add_conversation()
    ingest_turn("Wir nutzen aktuell Jira.", datetime(2026, 8, 10, 10, 0), store4, conv_a)
    ingest_turn("Wir nutzen aktuell Linear.", datetime(2026, 8, 10, 10, 0), store4, conv_b)
    check("Scope: insgesamt 2 Propositionen im Store", len(store4), 2)
    check("Scope: KEINE Relation zwischen den zwei Conversations", len(store4._relations), 0)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()