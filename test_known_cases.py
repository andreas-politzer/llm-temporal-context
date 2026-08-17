"""
Validiert die deterministische Engine gegen Fälle, die am 16.08.2026
bereits von Claude, Gemini und Luna unabhängig klassifiziert wurden.
Kein neuer Blindtest — reine Reproduktion bekannter, bereits vereinbarter
Urteile, jetzt mit Code statt mit drei Sprachmodellen.

Update 17.08.2026: gegen den finalisierten Architecture Contract v0
aktualisiert (siehe Decisions/2026-08-17 State-Relation -
Storage-Query-Trennung und Transition-Dominanz, inkl. Addendum). Das
frühere ConsistencyStatus (CONSISTENT/CONTRADICTORY/UNDETERMINED) ist
durch StateRelation (CONTINUES/SUPERSEDES/CONTRADICTS/UNDETERMINED)
ersetzt und aus relation.py entfernt (per grep bestätigt unbenutzt).
Fall 3 wird nicht mehr durch hartkodiertes OVERLAP vorbeigemogelt,
sondern verwendet die tatsächlich berechnete temporal_relation.

Nicht abgedeckt (siehe temporal_engine.py-Docstring): Fälle mit "niemals"
(R-1, Fall X4) — die brauchen ein Negations-/Universalitätsmodell, das v0
bewusst noch nicht hat. R-1 prüft deshalb weiterhin nur temporal_relation,
keine state_relation.
"""

from datetime import datetime

from tcl.proposition import TransitionType
from tcl.relation import (
    TemporalRelation,
    SemanticCompatibility,
    StateRelation,
    resolve_state_relation,
)
from tcl.temporal_engine import normalize, compare_intervals


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got.value if hasattr(got, 'value') else got}, "
          f"expected={expected.value if hasattr(expected, 'value') else expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== Reference-Time-Test, Fall 1 (saubere Ablösung) ===")
    # T1 [Montag 10:00]: "Wir verwenden aktuell Jira." (BARE)
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear." (TRANSITION)
    #
    # Hinweis: identisch zu Case A weiter unten (vermutlich unbeabsichtigte
    # Redundanz aus der Testentstehung, siehe Decision-Addendum 17.08.,
    # hier bewusst nicht konsolidiert, um an bestehender Struktur nichts
    # ungefragt wegzunehmen).
    monday = datetime(2026, 8, 10, 10, 0)   # Montag
    thursday = datetime(2026, 8, 13, 15, 0)  # Donnerstag
    a1 = normalize("aktuell", assertion_time=monday)
    a2 = normalize("since tuesday", assertion_time=thursday)
    rel = compare_intervals(a1, a2)
    check("Fall 1: Montag-Punkt vs. seit-Dienstag-Intervall", rel, TemporalRelation.BEFORE)
    # NEU (17.08.): volle state_relation-Kette, vorher nie geprüft.
    state = resolve_state_relation(
        rel,
        SemanticCompatibility.INCOMPATIBLE,
        transition_type_a=TransitionType.BARE,
        transition_type_b=TransitionType.TRANSITION,  # "seit Dienstag"
    )
    check("Fall 1: TRANSITION-Signal auf Linear-Proposition -> SUPERSEDES", state, StateRelation.SUPERSEDES)

    print("\n=== Reference-Time-Test, Fall 3 (Widerspruch, enge Assertion-Zeit) ===")
    # T1 [Montag 09:00]: "Wir verwenden aktuell Jira." (BARE)
    # T2 [Montag 09:15]: "Wir verwenden aktuell Linear." (BARE)
    t1 = datetime(2026, 8, 10, 9, 0)
    t2 = datetime(2026, 8, 10, 9, 15)
    b1 = normalize("aktuell", assertion_time=t1)
    b2 = normalize("aktuell", assertion_time=t2)
    rel = compare_intervals(b1, b2)
    # zwei sehr nah beieinanderliegende Punkte -> im v0-Punktmodell BEFORE,
    # nicht OVERLAP (Punkte ohne Ausdehnung überlappen nie exakt)
    check("Fall 3: zwei Punkte, 15 Min. auseinander", rel, TemporalRelation.BEFORE)
    # GEÄNDERT (17.08.): vorher wurde hier hartkodiert OVERLAP an das
    # inzwischen entfernte resolve_consistency übergeben, unabhängig
    # vom tatsächlich berechneten rel (=BEFORE) - genau die Art verdeckter
    # Default-Persistenz-Annahme, die die Architekturrunde vom 17.08.
    # explizit verworfen hat. Jetzt wird das reale rel verwendet, und
    # ohne TRANSITION-Signal auf beiden Seiten bleibt das Ergebnis
    # UNDETERMINED - kein Widerspruch wird künstlich behauptet, aber
    # auch keine Ablösung. Siehe Decision 2026-08-17.
    state = resolve_state_relation(
        rel,
        SemanticCompatibility.INCOMPATIBLE,
        transition_type_a=TransitionType.BARE,
        transition_type_b=TransitionType.BARE,
    )
    check(
        "Fall 3: BEFORE (real) + INCOMPATIBLE + kein TRANSITION -> UNDETERMINED (nicht mehr CONTRADICTORY)",
        state,
        StateRelation.UNDETERMINED,
    )

    print("\n=== Minimalpaar-Test, Case A (konsistent) ===")
    # T1 [Montag 10:00]: "Wir verwenden aktuell Jira." (assertion_time BEKANNT)
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear."
    c1 = normalize("aktuell", assertion_time=datetime(2026, 8, 10, 10, 0))
    c2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))
    rel = compare_intervals(c1, c2)
    check("Case A: Montag vor Dienstag-Wechsel", rel, TemporalRelation.BEFORE)
    state = resolve_state_relation(
        rel,
        SemanticCompatibility.INCOMPATIBLE,
        transition_type_a=TransitionType.BARE,
        transition_type_b=TransitionType.TRANSITION,
    )
    check("Case A: TRANSITION-Signal -> SUPERSEDES", state, StateRelation.SUPERSEDES)

    print("\n=== Minimalpaar-Test, Case B (Widerspruch — Architekturtest) ===")
    # T1 [Freitag 10:00]: "Wir verwenden aktuell Jira." (BARE)
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear." (TRANSITION)
    #
    # Dieser Fall war der entscheidende Fund vom 17.08.: d2 trägt ein
    # explizites TRANSITION-Signal, TROTZDEM ist das korrekte Ergebnis
    # CONTRADICTS, nicht SUPERSEDES - weil die Engine hier ECHTES,
    # textlich fundiertes OVERLAP berechnet (Freitag-Punkt liegt direkt
    # im "seit Dienstag"-Intervall). Eine ursprünglich zu grob
    # formulierte "TRANSITION dominiert immer"-Regel hätte das falsch
    # klassifiziert. Siehe Decision 2026-08-17, Addendum.
    d1 = normalize("aktuell", assertion_time=datetime(2026, 8, 14, 10, 0))  # Freitag
    d2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))  # Donnerstag
    rel = compare_intervals(d1, d2)
    check("Case B: Freitag liegt nach dem Dienstag-Wechsel", rel, TemporalRelation.OVERLAP)
    state = resolve_state_relation(
        rel,
        SemanticCompatibility.INCOMPATIBLE,
        transition_type_a=TransitionType.BARE,
        transition_type_b=TransitionType.TRANSITION,  # "seit Dienstag" - wird trotzdem überstimmt
    )
    check(
        "Case B: echtes OVERLAP überstimmt TRANSITION-Signal -> CONTRADICTS",
        state,
        StateRelation.CONTRADICTS,
    )

    print("\n=== Minimalpaar-Test, Case C (nicht bestimmbar) ===")
    # T1 [Zeitpunkt unbekannt]: "Wir verwenden aktuell Jira." (BARE)
    # T2 [Donnerstag 15:00]: "Seit Dienstag verwenden wir Linear." (TRANSITION)
    e1 = normalize("aktuell", assertion_time=None)
    e2 = normalize("since tuesday", assertion_time=datetime(2026, 8, 13, 15, 0))
    rel = compare_intervals(e1, e2)
    check("Case C: fehlende assertion_time -> UNDETERMINED", rel, TemporalRelation.UNDETERMINED)
    # NEU (17.08.): bemerkenswerter, aber korrekter Nebeneffekt der
    # finalisierten Regel - obwohl die Engine die Zeitordnung nicht
    # kennt (e1 hat keine assertion_time), dominiert das explizite
    # TRANSITION-Signal auf e2 mangels gegenteiliger Evidenz. Die
    # Extraction weiß mehr als die reine Intervall-Arithmetik.
    state = resolve_state_relation(
        rel,
        SemanticCompatibility.INCOMPATIBLE,
        transition_type_a=TransitionType.BARE,
        transition_type_b=TransitionType.TRANSITION,
    )
    check(
        "Case C: UNDETERMINED-Zeitordnung + TRANSITION-Signal -> SUPERSEDES",
        state,
        StateRelation.SUPERSEDES,
    )

    print("\n=== R-1: fixiertes Intervall trotz unbekannter Assertion Time ===")
    # T1 [unbekannt]: "From Monday through Wednesday, we never used Linear."
    #   -> hier NICHT die "never"-Semantik testen (nicht unterstützt),
    #      sondern nur die reine Intervall-Extraktion von "Monday through
    #      Wednesday" gegen ein Referenzdatum. Keine state_relation-Prüfung
    #      hier - Negation ist bewusst außerhalb des v0-Scopes (siehe
    #      Decision-Addendum 17.08., unverändert gültig).
    # T2 [Donnerstag 15:00]: "Since Tuesday, we have been using Linear."
    thursday_ref = datetime(2026, 8, 13, 15, 0)
    f1 = normalize("from monday through wednesday", assertion_time=thursday_ref)
    f2 = normalize("since tuesday", assertion_time=thursday_ref)
    rel = compare_intervals(f1, f2)
    check("R-1: Montag-Mittwoch überlappt mit seit-Dienstag", rel, TemporalRelation.OVERLAP)
    print(
        "  Hinweis: die eigentliche 'never'-Aussage (Negation) wird hier "
        "bewusst NICHT modelliert - nur die reine Intervall-Überlappung, "
        "die Voraussetzung für die spätere state_relation-Einstufung ist."
    )

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()
