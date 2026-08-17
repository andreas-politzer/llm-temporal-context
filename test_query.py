"""
    Schritt 9. Setzt voraus, dass jede übergebene id im Store existiert
    und assertion_time gesetzt hat (v0-Einschränkung, nicht geprüft).

    OFFENE FRAGE, nicht entschieden (siehe Chat 17.08.): CONTINUES-
    Relationen zwischen last_stated und einer anderen Proposition werden
    hier aktuell wie SUPERSEDES behandelt (keine offene Frage, nicht
    genannt). Das ist NICHT das Ergebnis einer durchgerechneten
    Architekturentscheidung, nur eine unreflektierte Annahme beim ersten
    Bauen. Muss noch an Minimalfällen geprüft werden, bevor sie als
    v0-Regel gilt.
    """

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.relation import SemanticCompatibility
from tcl.pipeline import process_new_proposition
from tcl.query import resolve_current_state, format_answer
from tcl.store import Store
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def make_prop(text, assertion_time, transition_type=TransitionType.BARE, raw="aktuell"):
    return Proposition(
        proposition_text=text,
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=assertion_time,
        transition_type=transition_type,
        normalized_temporal_reference=normalize(raw, assertion_time=assertion_time),
    )


def incompatible_stub(a, b):
    return SemanticCompatibility.INCOMPATIBLE


def main() -> None:
    print("=== Query, Fall 1: eindeutig auflösbar ===")
    store = Store()
    b = make_prop("Jira", datetime(2026, 8, 10, 9, 0))
    process_new_proposition(store, b, incompatible_stub)
    a = make_prop("Linear seit Dienstag", datetime(2026, 8, 13, 15, 0), TransitionType.TRANSITION, "since tuesday")
    process_new_proposition(store, a, incompatible_stub)

    result = resolve_current_state(store, [b.proposition_id, a.proposition_id])
    check("Fall 1: resolved", result.resolved, True)
    check("Fall 1: last_stated ist a (Linear)", result.last_stated.proposition_id, a.proposition_id)
    print("  ->", format_answer(result))

    print("\n=== Query, Fall 2: ein Konflikt ===")
    store2 = Store()
    p_old = make_prop("Jira", datetime(2026, 8, 10, 9, 0))
    process_new_proposition(store2, p_old, incompatible_stub)
    p_new = make_prop("Linear", datetime(2026, 8, 10, 9, 15))  # BARE, 15 Min. später -> UNDETERMINED
    process_new_proposition(store2, p_new, incompatible_stub)

    result2 = resolve_current_state(store2, [p_old.proposition_id, p_new.proposition_id])
    check("Fall 2: nicht resolved", result2.resolved, False)
    check("Fall 2: p_old in unclear", p_old in result2.unclear, True)
    check("Fall 2: contradicts leer", result2.contradicts, [])
    print("  ->", format_answer(result2))

    print("\n=== Query, Fall 3: mehrere gleichzeitige UNDETERMINED-Konflikte ===")
    store3 = Store()
    p1 = make_prop("Jira", datetime(2026, 8, 10, 9, 0))
    process_new_proposition(store3, p1, incompatible_stub)
    p2 = make_prop("GitHub Issues", datetime(2026, 8, 10, 9, 15))
    process_new_proposition(store3, p2, incompatible_stub)
    p3 = make_prop("Linear", datetime(2026, 8, 10, 9, 20))
    process_new_proposition(store3, p3, incompatible_stub)

    ids = [p1.proposition_id, p2.proposition_id, p3.proposition_id]
    result3 = resolve_current_state(store3, ids)
    check("Fall 3: nicht resolved", result3.resolved, False)
    check("Fall 3: last_stated ist p3", result3.last_stated.proposition_id, p3.proposition_id)
    print("  contradicts:", [p.proposition_text for p in result3.contradicts])
    print("  unclear:", [p.proposition_text for p in result3.unclear])
    print("  ->", format_answer(result3))

    print("\n=== Query, Fall 4: CONTRADICTS (echtes OVERLAP aus Textevidenz) ===")
    store4 = Store()
    p_since = make_prop(
        "Linear seit Dienstag", datetime(2026, 8, 13, 15, 0), TransitionType.TRANSITION, "since tuesday"
    )
    process_new_proposition(store4, p_since, incompatible_stub)
    # Freitag-Punkt liegt direkt im "seit Dienstag"-Intervall -> OVERLAP -> CONTRADICTS,
    # wie bei Case B, unabhängig vom TRANSITION-Signal auf p_since.
    p_friday = make_prop("Jira", datetime(2026, 8, 14, 10, 0))
    process_new_proposition(store4, p_friday, incompatible_stub)

    result4 = resolve_current_state(store4, [p_since.proposition_id, p_friday.proposition_id])
    check("Fall 4: nicht resolved", result4.resolved, False)
    check("Fall 4: p_since in contradicts", p_since in result4.contradicts, True)
    check("Fall 4: unclear leer", result4.unclear, [])
    print("  ->", format_answer(result4))

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()