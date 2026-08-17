"""
Minimalprobe zur Isolierung des temporalen Markers ("jetzt"), nach
Lunas methodischem Einwand: CL-5 in test_cross_lingual_probe.py war
ein Fragment, nicht der vollständige Satz aus 3d/10d — echte vierte
Variable, unbeabsichtigt eingeführt. T1-T4 hier sind exakt die
Originalsätze aus 3d/10d, nur mit/ohne "jetzt" kontrastiert.

Zusätzlich: jeder Fall dreimal (REPEATS), weil content_relation_fn
aktuell OHNE gesetzte temperature läuft (Contract-Lücke, siehe
Vault) — bevor wir irgendeine Aussage über "jetzt verursacht X"
treffen, muss erst klar sein, ob identischer Input überhaupt
reproduzierbare Ergebnisse liefert.
"""

from tcl.proposition import AssertionStatus, Proposition
from tcl.relation import SemanticCompatibility
from tcl.content_relation import content_relation_fn

REPEATS = 3

CASES = [
    ("T1_exact_3d_with_jetzt", "Wir nutzen Jira für Projektmanagement.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    ("T2_exact_10d_with_jetzt", "We use Jira for project planning.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    ("T3_full_sentence_de_no_now_control", "Wir nutzen Jira für Projektmanagement.", "Unser Bug-Tracking-Tool ist Linear.", SemanticCompatibility.COMPATIBLE),
    ("T4_full_sentence_en_no_now_control", "We use Jira for project management.", "Unser Bug-Tracking-Tool ist Linear.", SemanticCompatibility.COMPATIBLE),
    ("T5_full_sentence_en_en_with_now", "We use Jira for project management.", "Our bug-tracking tool is now Linear.", SemanticCompatibility.COMPATIBLE),
]


def prop(text: str) -> Proposition:
    return Proposition(proposition_text=text, assertion_status=AssertionStatus.ASSERTED)


def main() -> None:
    import time

    for name, text_a, text_b, expected in CASES:
        results = []
        for i in range(REPEATS):
            got = content_relation_fn(prop(text_a), prop(text_b))
            results.append(got.value)
            time.sleep(2)
        consistent = len(set(results)) == 1
        all_expected = all(r == expected.value for r in results)
        marker = "✓" if all_expected else ("~" if consistent else "✗")
        print(f"[{marker}] {name}: {results} (expected={expected.value}, "
              f"{'konsistent' if consistent else 'INKONSISTENT über Wiederholungen'})")


if __name__ == "__main__":
    main()