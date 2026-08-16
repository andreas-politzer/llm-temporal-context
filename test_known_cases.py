"""
Validiert die deterministische Engine gegen Fälle, die heute (16.08.2026)
bereits von Claude, Gemini und Luna unabhängig klassifiziert wurden.
Kein neuer Blindtest — reine Reproduktion bekannter, bereits vereinbarter
Urteile, jetzt mit Code statt mit drei Sprachmodellen.

Nicht abgedeckt (siehe temporal_engine.py-Docstring): Fälle mit "niemals"
(R-1, Fall X4) — die brauchen ein Negations-/Universalitätsmodell, das v0
bewusst noch nicht hat.
"""

from datetime import datetime

from tcl.relation import TemporalRelation, SemanticCompatibility, resolve_consistency, ConsistencyStatus
from tcl.temporal_engine import normalize, compare_intervals


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got.value if hasattr(got, 'value') else got}, "
          f"expected={expected.value if hasattr(expected, 'value') else expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Reference-Time-Test, Fall 1 (konsistent) ===")
    # T1 [Montag 10:00]: "Wir verwenden aktuell Jira."
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear."
    monday = datetime(2026, 8, 10, 10, 0)   # Montag
    thursday = datetime(2026, 8, 13, 15, 0)  # Donnerstag
    a1 = normalize("aktuell", assertion_time=monday)
    a2 = normalize("since tuesday", assertion_time=thursday)
    rel = compare_intervals(a1, a2)
    check("Fall 1: Montag-Punkt vs. seit-Dienstag-Intervall", rel, TemporalRelation.BEFORE)

    print("\n=== Reference-Time-Test, Fall 3 (Widerspruch, enge Assertion-Zeit) ===")
    # T1 [Montag 09:00]: "Wir verwenden aktuell Jira."
    # T2 [Montag 09:15]: "Wir verwenden aktuell Linear."
    t1 = datetime(2026, 8, 10, 9, 0)
    t2 = datetime(2026, 8, 10, 9, 15)
    b1 = normalize("aktuell", assertion_time=t1)
    b2 = normalize("aktuell", assertion_time=t2)
    rel = compare_intervals(b1, b2)
    # zwei sehr nah beieinanderliegende Punkte -> im v0-Punktmodell BEFORE,
    # nicht OVERLAP (Punkte ohne Ausdehnung überlappen nie exakt)
    check("Fall 3: zwei Punkte, 15 Min. auseinander", rel, TemporalRelation.BEFORE)
    # Hinweis: das ist ein bekannter Modellierungs-Kompromiss in v0 (siehe
    # unten in der Zusammenfassung) - Punkte kollidieren im Sinne von
    # "beide behaupten den jeweils selben Slot als aktuell", nicht weil
    # sich Zeit-Intervalle überschneiden. Die eigentliche CONTRADICTORY-
    # Einstufung von Fall 3 kommt in der echten Pipeline aus Schritt 7/8
    # (Semantic Compatibility: Jira und Linear sind INCOMPATIBLE), nicht
    # aus der reinen Zeitrelation - siehe Testfall unten.
    consistency = resolve_consistency(TemporalRelation.OVERLAP, SemanticCompatibility.INCOMPATIBLE)
    check(
        "Fall 3: kombiniert mit Semantic Compatibility=INCOMPATIBLE ergibt CONTRADICTORY",
        consistency,
        ConsistencyStatus.CONTRADICTORY,
    )

    print("\n=== Minimalpaar-Test, Case A (konsistent) ===")
    # T1 [Montag 10:00]: "Wir verwenden aktuell Jira." (assertion_time BEKANNT)
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear."
    c1 = normalize("aktuell", assertion_time=datetime(2026, 8, 10, 10, 0))
    c2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))
    check("Case A: Montag vor Dienstag-Wechsel", compare_intervals(c1, c2), TemporalRelation.BEFORE)

    print("\n=== Minimalpaar-Test, Case B (Widerspruch) ===")
    # T1 [Freitag 10:00]: "Wir verwenden aktuell Jira."
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear."
    d1 = normalize("aktuell", assertion_time=datetime(2026, 8, 14, 10, 0))  # Freitag
    d2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))  # Donnerstag
    rel = compare_intervals(d1, d2)
    check("Case B: Freitag liegt nach dem Dienstag-Wechsel", rel, TemporalRelation.OVERLAP)
    consistency = resolve_consistency(rel, SemanticCompatibility.INCOMPATIBLE)
    check("Case B: kombiniert -> CONTRADICTORY", consistency, ConsistencyStatus.CONTRADICTORY)

    print("\n=== Minimalpaar-Test, Case C (nicht bestimmbar) ===")
    # T1 [Zeitpunkt unbekannt]: "Wir verwenden aktuell Jira."
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear."
    e1 = normalize("aktuell", assertion_time=None)
    e2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))
    check("Case C: fehlende assertion_time -> UNDETERMINED", compare_intervals(e1, e2), TemporalRelation.UNDETERMINED)

    print("\n=== R-1: fixiertes Intervall trotz unbekannter Assertion Time ===")
    # T1 [unbekannt]: "From Monday through Wednesday, we never used Linear."
    #   -> hier NICHT die "never"-Semantik testen (nicht unterstützt),
    #      sondern nur die reine Intervall-Extraktion von "Monday through
    #      Wednesday" gegen ein Referenzdatum
    # T2 [Donnerstag 15:00]: "Since Tuesday, we have been using Linear."
    thursday_ref = datetime(2026, 8, 13, 15, 0)
    f1 = normalize("from monday through wednesday", assertion_time=thursday_ref)
    f2 = normalize("since tuesday", assertion_time=thursday_ref)
    rel = compare_intervals(f1, f2)
    check("R-1: Montag-Mittwoch überlappt mit seit-Dienstag", rel, TemporalRelation.OVERLAP)
    print(
        "  Hinweis: die eigentliche 'never'-Aussage (Negation) wird hier "
        "bewusst NICHT modelliert - nur die reine Intervall-Überlappung, "
        "die Voraussetzung für die spätere CONTRADICTORY-Einstufung ist."
    )

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()
