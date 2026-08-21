"""
Gezielte Fallfamilie zur Eingrenzung von Fund 7 (Content-Relation
Mini-Corpus, siehe Vault) — ist 10d ein Cross-Lingual-Contract-Befund
oder ein einzelner Ausreißer?

Isoliert drei mögliche Ursachen:
  - reines Sprachproblem (CL-1 vs CL-2, CL-3 vs CL-4)
  - Formulierungsproblem ("planning" vs "management")
  - Sprachmischung selbst (CL-6, CL-7 — beide Richtungen, im
    Unterschied zum Original-Vorschlag mit nur einer Richtung)

Alle sieben Fälle behalten das "jetzt" aus dem Original-Fall 10d bei
(CL-5/CL-6/CL-7), um keine unbeabsichtigte dritte Variable einzuführen.
"""

from tcl.proposition import AssertionStatus, Proposition
from tcl.relation import SemanticCompatibility
from tcl.content_relation import content_relation_fn


def prop(text: str) -> Proposition:
    return Proposition(proposition_text=text, assertion_status=AssertionStatus.ASSERTED)


CASES = [
    ("CL_1_de_de_management", "Jira für Projektmanagement.", "Linear für Bug-Tracking.", SemanticCompatibility.COMPATIBLE),
    ("CL_2_en_en_management", "Jira for project management.", "Linear for bug tracking.", SemanticCompatibility.COMPATIBLE),
    ("CL_3_de_de_planning", "Jira für Projektplanung.", "Linear ist Bug-Tracking-Tool.", SemanticCompatibility.COMPATIBLE),
    ("CL_4_en_en_planning", "Jira for project planning.", "Linear is our bug-tracking tool.", SemanticCompatibility.COMPATIBLE),
    ("CL_5_de_de_with_jetzt", "Jira für Projektmanagement.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    ("CL_6_en_de_mixed", "Jira for project management.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    ("CL_7_de_en_mixed_reversed", "Jira für Projektmanagement.", "Our bug-tracking tool is now Linear.", SemanticCompatibility.COMPATIBLE),
]


def main() -> None:
    import time

    passed = 0
    failed = []
    for name, text_a, text_b, expected in CASES:
        got = content_relation_fn(prop(text_a), prop(text_b))
        status = "OK" if got == expected else "FAIL"
        marker = "✓" if status == "OK" else "✗"
        print(f"[{marker} {status}] {name}: got={got.value}, expected={expected.value}")
        if got == expected:
            passed += 1
        else:
            failed.append(name)
        time.sleep(2)  # rein diagnostisch, nur hier im Testskript, nicht in content_relation.py

    print(f"\n{passed}/{len(CASES)} bestanden.")
    if failed:
        print("Fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()