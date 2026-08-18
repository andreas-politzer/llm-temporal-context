"""
End-to-End-Test für ingest_turn gegen PostgresStore. Nutzt ausschließlich
öffentliche StoreProtocol-Methoden (get_all_propositions, get_candidates,
get_relation_between) - keine internen Attribute, damit der Test für
InMemoryStore UND PostgresStore identisch funktioniert.
"""

from datetime import datetime

from tcl.ingest import ingest_turn
from tcl.postgres_store import PostgresStore
from tcl.proposition import AssertionStatus
from tcl.query import resolve_current_state, format_answer


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Voller Fluss, Fall 1: Anbieterwechsel, SUPERSEDES ===")
    store = PostgresStore()
    conv = store.add_conversation()
    ingest_turn("Wir arbeiten aktuell mit Anbieter A.", datetime(2026, 8, 10, 10, 0), store, conv)
    ingest_turn("Seit Dienstag arbeiten wir mit Anbieter B.", datetime(2026, 8, 13, 15, 0), store, conv)

    props = store.get_all_propositions(conv)
    check("Fall 1: 2 Propositionen in dieser Conversation", len(props), 2)
    ids = [p.proposition_id for p in props]
    result = resolve_current_state(store, ids)
    check("Fall 1: eindeutig aufgelöst", result.resolved, True)
    print("  ->", format_answer(result))

    print("\n=== Voller Fluss, Konditional: gespeichert, aber kein Candidate ===")
    conv2 = store.add_conversation()
    ingest_turn("Wenn der neue Vertrag unterschrieben wird, wechseln wir zu Anbieter C.", datetime(2026, 8, 17, 9, 0), store, conv2)
    props2 = store.get_all_propositions(conv2)
    check("Konditional: 2 Propositionen gespeichert (Audit-Trail)", len(props2), 2)
    check("Konditional: beide NOT_ASSERTED", all(p.assertion_status == AssertionStatus.NOT_ASSERTED for p in props2), True)
    check("Konditional: kein einziger ASSERTED-Candidate", len(store.get_candidates(conv2, None)), 0)

    print("\n=== Voller Fluss, gemischter Turn: eine ASSERTED, zwei NOT_ASSERTED ===")
    conv3 = store.add_conversation()
    ingest_turn(
        "Wir arbeiten mit Anbieter A. Wenn der neue Vertrag unterschrieben wird, wechseln wir zu Anbieter C.",
        datetime(2026, 8, 17, 9, 0), store, conv3,
    )
    props3 = store.get_all_propositions(conv3)
    check("Gemischt: 3 Propositionen gespeichert", len(props3), 3)
    check("Gemischt: genau 1 davon ASSERTED (Candidate)", len(store.get_candidates(conv3, None)), 1)

    print("\n=== Scope-Test: zwei Conversations bleiben getrennt ===")
    conv_a = store.add_conversation()
    conv_b = store.add_conversation()
    ingest_turn("Wir arbeiten aktuell mit Anbieter A.", datetime(2026, 8, 10, 10, 0), store, conv_a)
    ingest_turn("Wir arbeiten aktuell mit Anbieter B.", datetime(2026, 8, 10, 10, 0), store, conv_b)
    check("Scope: Conversation A hat genau 1 Proposition", len(store.get_all_propositions(conv_a)), 1)
    check("Scope: Conversation B hat genau 1 Proposition", len(store.get_all_propositions(conv_b)), 1)
    id_a = store.get_all_propositions(conv_a)[0].proposition_id
    id_b = store.get_all_propositions(conv_b)[0].proposition_id
    check("Scope: KEINE Relation zwischen den zwei Conversations", store.get_relation_between(id_a, id_b), None)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()