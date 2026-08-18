"""
End-to-End-Test für process_turn (Schritt 1-4 in einem Durchlauf).
Nutzt bewusst bereits einzeln geprüfte Fälle aus den drei Bausteinen -
testet die VERKABELUNG, nicht die einzelnen Regeln (die sind schon
validiert, siehe test_extraction.py, test_assertion_check.py,
test_temporal_expression.py).
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, TransitionType
from tcl.turn_processor import process_turn

REFERENCE_TIME = datetime(2026, 8, 17, 12, 0)


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== E2E, Fall 1: Selbst-Transition, zwei Propositionen ===")
    props = process_turn("Es war lange zuverlässig, ist es aber nicht mehr.", REFERENCE_TIME)
    check("Fall 1: Anzahl Propositionen", len(props), 2)
    check("Fall 1: beide gleiche decomposition_group_id", len({p.decomposition_group_id for p in props}), 1)
    check("Fall 1: P2 hat TRANSITION", props[1].transition_type, TransitionType.TRANSITION)
    check("Fall 1: beide haben normalized_temporal_reference gesetzt", all(p.normalized_temporal_reference is not None for p in props), True)

    print("\n=== E2E, Fall 2: Konditional, beide NOT_ASSERTED ===")
    props2 = process_turn("Wenn das Budget reicht, wechseln wir zu Linear.", REFERENCE_TIME)
    check("Fall 2: Anzahl Propositionen", len(props2), 2)
    check("Fall 2: beide NOT_ASSERTED", all(p.assertion_status == AssertionStatus.NOT_ASSERTED for p in props2), True)

    print("\n=== E2E, Fall 3: seit-Ausdruck korrekt normalisiert ===")
    props3 = process_turn("Seit Dienstag nutzen wir Linear.", REFERENCE_TIME)
    check("Fall 3: Anzahl Propositionen", len(props3), 1)
    check("Fall 3: transition_type TRANSITION", props3[0].transition_type, TransitionType.TRANSITION)
    check("Fall 3: normalized_temporal_reference hat offenen Start (seit-Intervall)", props3[0].normalized_temporal_reference.end, None)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()