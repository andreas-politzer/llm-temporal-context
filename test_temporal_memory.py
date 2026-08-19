"""
Testet search_turns gegen InMemoryStore und PostgresStore — reine
Textsuche, kein LLM, kostenlos. Nutzt bewusst KEIN Zertifikat-Beispiel
mehr (siehe Andys Bitte, 18.08.) — stattdessen ein Meeting/Termin-Fall.
"""

from datetime import datetime

from tcl.store import InMemoryStore


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def run_temporal_memory_tests(store, store_name: str) -> None:
    print(f"\n{'=' * 20} Temporal Memory gegen {store_name} {'=' * 20}")

    conv = store.add_conversation()
    store.add_turn(conv, "Wir haben ein Meeting am Montag geplant.", datetime(2026, 8, 10, 9, 0))
    store.add_turn(conv, "Der Server läuft stabil.", datetime(2026, 8, 12, 14, 0))
    store.add_turn(conv, "Das Meeting wurde auf Mittwoch verschoben.", datetime(2026, 8, 13, 11, 0))

    hits = store.search_turns(conv, "Meeting")
    check(f"{store_name}: findet beide Meeting-Erwähnungen", len(hits), 2)
    check(f"{store_name}: sortiert nach Zeit (erste zuerst)", hits[0]["turn_text"], "Wir haben ein Meeting am Montag geplant.")

    no_hits = store.search_turns(conv, "Budget")
    check(f"{store_name}: kein Treffer für unerwähnten Begriff", no_hits, [])

    print(f"{store_name}: alle Checks bestanden.")


def main() -> None:
    run_temporal_memory_tests(InMemoryStore(), "InMemoryStore")

    try:
        from tcl.postgres_store import PostgresStore
        run_temporal_memory_tests(PostgresStore(), "PostgresStore")
    except Exception as e:
        print(f"\n⚠ PostgresStore-Test übersprungen/fehlgeschlagen: {e}")
        raise


if __name__ == "__main__":
    main()