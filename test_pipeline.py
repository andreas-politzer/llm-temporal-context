"""
End-to-End-Test der verkabelten Pipeline (Store + Engine + Relation
Resolution). content_relation_fn ist hier ein reiner TEST-Stub, keine
Produktionslogik — er simuliert, was später die LLM-Ebene liefern
würde, mit einer trivialen, fest verdrahteten Zuordnung. Das gehört
NICHT in pipeline.py oder relation.py, nur hierher.

Reproduziert Fall 1 (SUPERSEDES) und Case B (CONTRADICTS) end-to-end,
nicht mehr isoliert wie in test_known_cases.py.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.relation import SemanticCompatibility, StateRelation
from tcl.pipeline import process_new_proposition
from tcl.store import Store
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got.value if hasattr(got, 'value') else got}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def jira_linear_content_relation_stub(a: Proposition, b: Proposition) -> SemanticCompatibility:
    """TEST-ONLY: fest verdrahtet für dieses Testszenario, keine echte Semantik."""
    return SemanticCompatibility.INCOMPATIBLE


def main() -> None:
    print("=== End-to-End, Fall 1 (saubere Ablösung) ===")
    store = Store()
    jira = Proposition(
        proposition_text="Wir verwenden aktuell Jira.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 10, 10, 0),
        transition_type=TransitionType.BARE,
        normalized_temporal_reference=normalize("aktuell", assertion_time=datetime(2026, 8, 10, 10, 0)),
    )
    store.add(jira)

    linear = Proposition(
        proposition_text="Seit Dienstag verwenden wir Linear.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 13, 15, 0),
        transition_type=TransitionType.TRANSITION,
        normalized_temporal_reference=normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0)),
    )
    relations = process_new_proposition(store, linear, jira_linear_content_relation_stub)
    check("Fall 1 end-to-end: genau eine Relation (gegen jira)", len(relations), 1)
    check("Fall 1 end-to-end: state_relation -> SUPERSEDES", relations[0].state_relation, StateRelation.SUPERSEDES)
    check("Store enthält jetzt beide Propositionen", len(store), 2)

    print("\n=== End-to-End, Case B (echtes OVERLAP überstimmt TRANSITION) ===")
    store2 = Store()
    linear2 = Proposition(
        proposition_text="Seit Dienstag verwenden wir Linear.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 13, 15, 0),
        transition_type=TransitionType.TRANSITION,
        normalized_temporal_reference=normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0)),
    )
    store2.add(linear2)

    jira_friday = Proposition(
        proposition_text="Wir verwenden aktuell Jira.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 14, 10, 0),
        transition_type=TransitionType.BARE,
        normalized_temporal_reference=normalize("aktuell", assertion_time=datetime(2026, 8, 14, 10, 0)),
    )
    relations2 = process_new_proposition(store2, jira_friday, jira_linear_content_relation_stub)
    check("Case B end-to-end: state_relation -> CONTRADICTS trotz TRANSITION auf Kandidat", relations2[0].state_relation, StateRelation.CONTRADICTS)

    print("\n=== End-to-End, Fall 3 (echter Widerspruch bleibt UNDETERMINED) ===")
    store3 = Store()
    jira_early = Proposition(
        proposition_text="Wir verwenden aktuell Jira.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 10, 9, 0),
        transition_type=TransitionType.BARE,
        normalized_temporal_reference=normalize("aktuell", assertion_time=datetime(2026, 8, 10, 9, 0)),
    )
    store3.add(jira_early)

    linear_15min_later = Proposition(
        proposition_text="Wir verwenden aktuell Linear.",
        assertion_status=AssertionStatus.ASSERTED,
        assertion_time=datetime(2026, 8, 10, 9, 15),
        transition_type=TransitionType.BARE,
        normalized_temporal_reference=normalize("aktuell", assertion_time=datetime(2026, 8, 10, 9, 15)),
    )
    relations3 = process_new_proposition(store3, linear_15min_later, jira_linear_content_relation_stub)
    check(
        "Fall 3 end-to-end: BARE/BARE, 15 Min. auseinander -> UNDETERMINED, keine Ablösung erfunden",
        relations3[0].state_relation,
        StateRelation.UNDETERMINED,
    )

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()