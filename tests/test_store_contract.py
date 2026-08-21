"""
Contract-Tests gegen StoreProtocol — laufen identisch gegen
InMemoryStore und PostgresStore (Decision 2026-08-18). Konstruiert
Proposition/PairwiseRelation-Objekte von Hand, ruft KEINE LLM-Funktionen
auf — reines Speicherverhalten, kostenlos, kein API-Key nötig.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.relation import PairwiseRelation, SemanticCompatibility, StateRelation, TemporalRelation


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def make_proposition(text: str, assertion_status=AssertionStatus.ASSERTED) -> Proposition:
    return Proposition(proposition_text=text, assertion_status=assertion_status, transition_type=TransitionType.BARE)


def run_contract_tests(store, store_name: str) -> None:
    print(f"\n{'=' * 20} Contract-Tests gegen {store_name} {'=' * 20}")

    print("\n--- Conversation-Isolation ---")
    conv_a = store.add_conversation()
    conv_b = store.add_conversation()
    turn_a = store.add_turn(conv_a, "Beispiel A", datetime(2026, 8, 18, 10, 0))
    turn_b = store.add_turn(conv_b, "Beispiel B", datetime(2026, 8, 18, 10, 0))

    prop_a = make_proposition("Aussage in Conversation A")
    prop_b = make_proposition("Aussage in Conversation B")
    store.ingest_propositions(turn_a, [prop_a], [])
    store.ingest_propositions(turn_b, [prop_b], [])

    candidates_for_a = store.get_candidates(conv_a, make_proposition("neue Aussage"))
    check(f"{store_name}: Conversation A sieht nur ihre eigene Proposition", len(candidates_for_a), 1)
    check(f"{store_name}: Conversation A sieht NICHT Propositionen aus B", candidates_for_a[0].proposition_id == prop_b.proposition_id, False)

    print("\n--- NOT_ASSERTED: gespeichert, aber kein Candidate ---")
    conv_c = store.add_conversation()
    turn_c = store.add_turn(conv_c, "Hypothetische Aussage", datetime(2026, 8, 18, 10, 0))
    not_asserted_prop = make_proposition("Hypothetische Proposition", assertion_status=AssertionStatus.NOT_ASSERTED)
    store.ingest_propositions(turn_c, [not_asserted_prop], [])

    fetched = store.get_by_id(not_asserted_prop.proposition_id)
    check(f"{store_name}: NOT_ASSERTED-Proposition ist abrufbar (gespeichert)", fetched is not None, True)

    candidates_for_c = store.get_candidates(conv_c, make_proposition("neue Aussage"))
    check(f"{store_name}: NOT_ASSERTED taucht NICHT als Candidate auf", len(candidates_for_c), 0)

    print("\n--- Relation-Persistenz ---")
    conv_d = store.add_conversation()
    turn_d1 = store.add_turn(conv_d, "Erste Aussage", datetime(2026, 8, 18, 9, 0))
    turn_d2 = store.add_turn(conv_d, "Zweite Aussage", datetime(2026, 8, 18, 11, 0))

    prop_d1 = make_proposition("Vertrag läuft.")
    store.ingest_propositions(turn_d1, [prop_d1], [])

    prop_d2 = make_proposition("Vertrag ist beendet.")
    relation = PairwiseRelation(
        proposition_a_id=prop_d1.proposition_id,
        proposition_b_id=prop_d2.proposition_id,
        temporal_relation=TemporalRelation.AFTER,
        content_relation=SemanticCompatibility.INCOMPATIBLE,
        state_relation=StateRelation.SUPERSEDES,
    )
    store.ingest_propositions(turn_d2, [prop_d2], [relation])

    fetched_relation = store.get_relation_between(prop_d1.proposition_id, prop_d2.proposition_id)
    check(f"{store_name}: Relation ist abrufbar", fetched_relation is not None, True)
    check(f"{store_name}: Relation hat korrekten state_relation-Wert", fetched_relation.state_relation, StateRelation.SUPERSEDES)

    print(f"\n{store_name}: alle Contract-Checks bestanden.")


def run_atomicity_probe(store, store_name: str) -> None:
    """
    Kein harter Pass/Fail-Test - deckt eine bewusst noch offene Frage
    auf: Was passiert, wenn ingest_propositions mit einer Relation
    aufgerufen wird, die auf eine NICHT existierende proposition_id
    zeigt? Bei PostgreSQL sollte der Foreign-Key-Constraint das
    verhindern (Transaktion rollt zurück, auch die gültige Proposition
    verschwindet wieder). InMemoryStore hat aktuell KEINE
    Fremdschlüssel-Prüfung - Diskrepanz wird hier sichtbar gemacht,
    nicht versteckt.
    """
    print(f"\n--- Atomaritäts-Probe (informativ, kein Pass/Fail) gegen {store_name} ---")
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Atomaritätstest", datetime(2026, 8, 18, 10, 0))
    valid_prop = make_proposition("Gültige Proposition")
    broken_relation = PairwiseRelation(
        proposition_a_id=valid_prop.proposition_id,
        proposition_b_id="00000000-0000-0000-0000-000000000000",  # existiert nicht
        temporal_relation=TemporalRelation.AFTER,
        content_relation=SemanticCompatibility.INCOMPATIBLE,
        state_relation=StateRelation.CONTRADICTS,
    )
    try:
        store.ingest_propositions(turn, [valid_prop], [broken_relation])
        still_there = store.get_by_id(valid_prop.proposition_id) is not None
        print(f"  {store_name}: KEIN Fehler geworfen. Gültige Proposition trotzdem gespeichert: {still_there}")
        if still_there:
            print(f"  ⚠ {store_name} prüft keine referenzielle Integrität - Atomaritäts-Garantie nicht durchgesetzt.")
    except Exception as e:
        still_there = store.get_by_id(valid_prop.proposition_id) is not None
        print(f"  {store_name}: Fehler geworfen ({type(e).__name__}). Gültige Proposition noch da: {still_there}")
        if not still_there:
            print(f"  ✓ {store_name}: Transaktion korrekt zurückgerollt, echte Atomarität.")


def main() -> None:
    from tcl.store import InMemoryStore

    run_contract_tests(InMemoryStore(), "InMemoryStore")
    run_atomicity_probe(InMemoryStore(), "InMemoryStore")

    try:
        from tcl.postgres_store import PostgresStore

        pg_store = PostgresStore()
        run_contract_tests(pg_store, "PostgresStore")
        run_atomicity_probe(PostgresStore(), "PostgresStore")
    except Exception as e:
        print(f"\n⚠ PostgresStore-Tests übersprungen/fehlgeschlagen: {e}")
        raise


if __name__ == "__main__":
    main()