"""
Regressionstest für den echten Live-Fund vom 18.08.: "Sicherheitszertifikat
gültig bis 30.06.2026" konnte nicht ins normalize()-Vokabular übersetzt
werden, Decay griff deshalb nie - Claude Desktop kaschierte das durch
eigenes Weltwissen, ohne dass der Layer selbst die Lücke erkannte.

Testet den kompletten Pfad: raw_temporal_expression -> normalize() ->
normalized_temporal_reference.end -> _is_decayed() -> resolve_current_state()
== resolved=False, exakt wie von Andy/Luna gefordert.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.query import resolve_current_state, format_answer
from tcl.store import InMemoryStore
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== normalize() erkennt das Datum korrekt ===")
    interval = normalize("until 30.06.2026", assertion_time=datetime(2026, 1, 1))
    check("normalized end == 2026-06-30", interval.end, datetime(2026, 6, 30))
    check("normalized start bleibt None (kein Startdatum bekannt)", interval.start, None)

    print("\n=== Kompletter Zertifikat-Fall, genau wie im Live-Test ===")
    store = InMemoryStore()
    conv = store.add_conversation()
    turn = store.add_turn(conv, "Sicherheitszertifikat-Turn", datetime(2026, 1, 1, 10, 0))

    cert = Proposition(
        proposition_text="Das Sicherheitszertifikat ist bis zum 30.06.2026 gültig.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 1, 1, 10, 0),
        raw_temporal_expression="until 30.06.2026",
        normalized_temporal_reference=normalize("until 30.06.2026", assertion_time=datetime(2026, 1, 1, 10, 0)),
        transition_type=TransitionType.BARE,
    )
    store.ingest_propositions(turn, [cert], [])

    print("\n=== Abfrage während der Gültigkeit (März 2026) ===")
    result_valid = resolve_current_state(store, [cert.proposition_id], query_time=datetime(2026, 3, 1))
    check("Noch gültig: aufgelöst", result_valid.resolved, True)

    print("\n=== Abfrage nach Ablauf (18.08.2026, wie im echten Live-Test) ===")
    result_expired = resolve_current_state(store, [cert.proposition_id], query_time=datetime(2026, 8, 18))
    check("Abgelaufen: NICHT aufgelöst", result_expired.resolved, False)
    print(f"  -> {format_answer(result_expired)}")

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()