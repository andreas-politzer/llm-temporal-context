"""
Regressionstest für tcl.temporal_expression.temporal_expression_fn
gegen den Mini-Corpus (6 Fälle, siehe Temporal Continuity/
Temporal-Expression Contract v0). Prüft zusätzlich, dass das
Ergebnis tatsächlich durch normalize() geparst werden kann (nicht
nur der rohe Ausdruck selbst plausibel aussieht).
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.temporal_expression import temporal_expression_fn
from tcl.temporal_engine import normalize

REFERENCE_TIME = datetime(2026, 8, 17, 12, 0)  # Montag, zur Wochentag-Auflösung

# (name, turn_text, proposition_text, transition_type, expect_none)
CASES = [
    ("case_1_default_current", "Wir nutzen Jira.", "Wir nutzen Jira.", TransitionType.BARE, False),
    ("case_2_since", "Seit Dienstag nutzen wir Linear.", "Wir nutzen Linear.", TransitionType.TRANSITION, False),
    ("case_3_days_ago", "Wir haben vor drei Tagen gewechselt.", "Wir haben gewechselt.", TransitionType.TRANSITION, False),
    ("case_4_fixed_interval", "Von Montag bis Mittwoch war das System offline.", "Das System war offline.", TransitionType.BARE, False),
    ("case_5_continuation", "Wir nutzen weiterhin Jira.", "Wir nutzen weiterhin Jira.", TransitionType.CONTINUATION, False),
    ("case_6_out_of_vocabulary", "Im März haben wir umgestellt.", "Wir haben umgestellt.", TransitionType.TRANSITION, True),
]


def main() -> None:
    passed = 0
    failed = []
    for name, turn_text, prop_text, transition_type, expect_none in CASES:
        prop = Proposition(
            proposition_text=prop_text,
            assertion_status=AssertionStatus.ASSERTED,
            transition_type=transition_type,
        )
        result = temporal_expression_fn(turn_text, [prop])
        got_expr = result[0].raw_temporal_expression

        if expect_none:
            ok = got_expr is None
            print(f"[{'✓' if ok else '✗'} {'OK' if ok else 'FAIL'}] {name}: got={got_expr!r} (expected None)")
        else:
            if got_expr is None:
                ok = False
                print(f"[✗ FAIL] {name}: got=None (erwartete einen Ausdruck)")
            else:
                interval = normalize(got_expr, assertion_time=REFERENCE_TIME)
                has_bound = interval.start is not None or interval.end is not None
                # Wenn beide Grenzen bekannt sind, muss end >= start gelten -
                # sonst wäre es ein logisch inkonsistentes Intervall (siehe
                # der am 18.08. gefundene und behobene Wochentag-Bug).
                logically_consistent = (
                    interval.start is None or interval.end is None or interval.start <= interval.end
                )
                ok = has_bound and logically_consistent
                print(
                    f"[{'✓' if ok else '✗'} {'OK' if ok else 'FAIL'}] {name}: "
                    f"raw={got_expr!r} -> normalize() ergab {interval} "
                    f"({'erfolgreich geparst' if ok else 'NICHT korrekt (fehlend oder end < start)!'})"
                )

        if ok:
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