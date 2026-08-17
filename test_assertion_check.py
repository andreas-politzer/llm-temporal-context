"""
Regressionstest für tcl.assertion_check.assertion_check_fn gegen den
Assertion-Check-Corpus (7 Fälle, Blind-Triangulation, siehe
Temporal Continuity/Assertion-Check Contract v0).
"""

from tcl.assertion_check import assertion_check_fn
from tcl.proposition import AssertionStatus, ExtractedProposition, TransitionType

# (name, turn_text, proposition_text, expected_assertion, expected_transition)
CASES = [
    ("case_1_baseline", "Wir nutzen Jira.", "Wir nutzen Jira.", AssertionStatus.ASSERTED, TransitionType.BARE),
    ("case_2_negation", "Wir nutzen kein Jira mehr.", "Wir nutzen kein Jira mehr.", AssertionStatus.ASSERTED, TransitionType.TRANSITION),
    ("case_3_uncertainty", "Ich glaube, wir nutzen noch Jira.", "Wir nutzen noch Jira.", AssertionStatus.NOT_ASSERTED, TransitionType.CONTINUATION),
    ("case_4_conditional_consequence", "Wenn das Budget reicht, wechseln wir zu Linear.", "Wir wechseln zu Linear.", AssertionStatus.NOT_ASSERTED, TransitionType.TRANSITION),
    ("case_5_conditional_condition", "Wenn das Budget reicht, wechseln wir zu Linear.", "Das Budget reicht.", AssertionStatus.NOT_ASSERTED, TransitionType.BARE),
    ("case_6_continuation", "Wir nutzen weiterhin Jira.", "Wir nutzen weiterhin Jira.", AssertionStatus.ASSERTED, TransitionType.CONTINUATION),
    ("case_7_transition_context_only", "Wir haben Jira genutzt, jetzt ist das anders: wir setzen auf Linear.", "Wir setzen auf Linear.", AssertionStatus.ASSERTED, TransitionType.TRANSITION),
]


def main() -> None:
    passed = 0
    failed = []
    for name, turn_text, prop_text, expected_assertion, expected_transition in CASES:
        extracted = [ExtractedProposition(proposition_text=prop_text, decomposition_group_id="test-group")]
        result = assertion_check_fn(turn_text, extracted)
        got = result[0]
        ok_assertion = got.assertion_status == expected_assertion
        ok_transition = got.transition_type == expected_transition
        status = "OK" if (ok_assertion and ok_transition) else "FAIL"
        marker = "✓" if status == "OK" else "✗"
        print(
            f"[{marker} {status}] {name}: "
            f"assertion={got.assertion_status.value} (expected {expected_assertion.value}), "
            f"transition={got.transition_type.value} (expected {expected_transition.value})"
        )
        if ok_assertion and ok_transition:
            passed += 1
        else:
            failed.append(name)

    print(f"\n{passed}/{len(CASES)} bestanden.")
    if failed:
        print("Fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()