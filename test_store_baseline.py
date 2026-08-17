"""
Baseline-Test für Store.get_candidates().

Wichtig, um Missverständnisse zu vermeiden: Das hier ist KEIN Recall-Test
im eigentlichen Sinn. Bei Exhaustive Retrieval (siehe store.py-Docstring)
gibt es keinen Filter, der einen Kandidaten ausschließen könnte — ein
Test, der prüft, ob ein Paraphrasen- oder Gruppen-Paar "gefunden" wird,
kann bei dieser Implementierung nicht scheitern. Zweck dieser Datei ist
stattdessen, die v0-Baseline ("Full Retrieval = 100% Recall") explizit
zu dokumentieren, gegen die künftige Filterstrategien sich messen
müssen — und zu zeigen, dass decomposition_group_id unter Exhaustive
Retrieval ohne Sondercode automatisch erfüllt ist.
"""

from tcl.proposition import Proposition, AssertionStatus
from tcl.store import Store


def check(name: str, got: bool, expected: bool) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Baseline: Paraphrasen-Paar wird trotz unterschiedlichem Wortlaut vorgelegt ===")
    # Das ursprüngliche Gegenbeispiel gegen einen naiven subject-Filter
    # (siehe Chat 17.08.) — unter Exhaustive Retrieval kein Problem,
    # weil kein Filter existiert, der es verursachen könnte.
    store = Store()
    p1 = Proposition(proposition_text="Wir nutzen Jira.", assertion_status=AssertionStatus.ASSERTED)
    store.add(p1)

    p2 = Proposition(
        proposition_text="Unser Bug-Tracking-Tool ist jetzt Linear.",
        assertion_status=AssertionStatus.ASSERTED,
    )
    candidates = store.get_candidates(p2)
    check(
        "Paraphrasen-Paar: p1 ist Kandidat für p2, trotz unterschiedlichem subject-Wortlaut",
        p1 in candidates,
        True,
    )

    print("\n=== Baseline: decomposition_group_id-Paar automatisch enthalten ===")
    group_id = "grp-1"
    store2 = Store()
    q1 = Proposition(
        proposition_text="war lange zuverlässig",
        assertion_status=AssertionStatus.ASSERTED,
        decomposition_group_id=group_id,
    )
    store2.add(q1)
    q2 = Proposition(
        proposition_text="ist es aber nicht mehr",
        assertion_status=AssertionStatus.ASSERTED,
        decomposition_group_id=group_id,
    )
    candidates2 = store2.get_candidates(q2)
    check(
        "Gruppen-Paar: q1 ist Kandidat für q2, ohne eigenen Codepfad in get_candidates()",
        q1 in candidates2,
        True,
    )

    print("\n=== Baseline: offensichtlich irrelevante Proposition wird trotzdem vorgelegt ===")
    # Das ist bewusst gewollt, kein Bug — Kosten sind der Preis für
    # garantierten Recall, nicht ein Zeichen fehlender Filterung.
    store3 = Store()
    r1 = Proposition(proposition_text="Das Wetter war gestern schön.", assertion_status=AssertionStatus.ASSERTED)
    store3.add(r1)
    r2 = Proposition(proposition_text="Wir nutzen Jira.", assertion_status=AssertionStatus.ASSERTED)
    candidates3 = store3.get_candidates(r2)
    check(
        "Thematisch irrelevante Proposition ist trotzdem Kandidat (v0 filtert bewusst nicht)",
        r1 in candidates3,
        True,
    )

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()