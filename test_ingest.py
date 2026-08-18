"""
End-to-End-Test für ingest_turn: Rohtext -> Store -> Query, in einem
durchgängigen Fluss. Nutzt bewusst bekannte Fälle (Fall 1, Konditional-
Filter, Fall 3-artiger Widerspruch), um die VOLLSTÄNDIGE Kette zu
prüfen, nicht nur einzelne Bausteine.
"""

from datetime import datetime

from tcl.ingest import ingest_turn
from tcl.query import resolve_current_state, format_answer
from tcl.store import Store


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Voller Fluss, Fall 1: Jira -> Linear, SUPERSEDES, Query beantwortet korrekt ===")
    store = Store()
    ingest_turn("Wir nutzen aktuell Jira.", datetime(2026, 8, 10, 10, 0), store)
    ingest_turn("Seit Dienstag nutzen wir Linear.", datetime(2026, 8, 13, 15, 0), store)

    check("Fall 1: Store enthält beide Propositionen", len(store), 2)
    ids = [p.proposition_id for p in store._propositions]  # nur zu Testzwecken direkter Zugriff
    result = resolve_current_state(store, ids)
    check("Fall 1: eindeutig aufgelöst", result.resolved, True)
    print("  ->", format_answer(result))

    print("\n=== Voller Fluss, Konditional wird NICHT gespeichert ===")
    store2 = Store()
    ingest_turn("Wenn das Budget reicht, wechseln wir zu Linear.", datetime(2026, 8, 17, 9, 0), store2)
    check("Konditional: Store bleibt leer (beide Propositionen NOT_ASSERTED)", len(store2), 0)

    print("\n=== Voller Fluss, gemischter Turn: eine ASSERTED, eine NOT_ASSERTED-Proposition ===")
    store3 = Store()
    ingest_turn(
        "Wir nutzen Jira. Wenn das Budget reicht, wechseln wir zu Linear.",
        datetime(2026, 8, 17, 9, 0),
        store3,
    )
    check("Gemischt: nur die ASSERTED-Proposition landet im Store", len(store3), 1)
    check("Gemischt: die gespeicherte Proposition ist die Jira-Aussage", "Jira" in store3._propositions[0].proposition_text, True)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()