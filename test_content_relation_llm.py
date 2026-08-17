"""
Regressionstest für tcl.content_relation.content_relation_fn gegen den
Mini-Corpus (28 Fälle, Runde 1 + 2, siehe
[[Temporal Continuity/Content-Relation Mini-Corpus v0]]).

WICHTIG: braucht ANTHROPIC_API_KEY und das Paket 'anthropic', macht
echte API-Aufrufe (28 Stück) - kein Mock, kein Stub. Nicht Teil der
deterministischen Test-Suite (test_known_cases.py etc.), bewusst
getrennt, weil die Ergebnisse nicht exakt reproduzierbar sind wie bei
der Engine.

Der ursprüngliche Fall 12 aus Runde 1 ist HIER NICHT enthalten - seine
damalige Mehrheitsantwort beruhte auf einer fehlerhaften Instruktion
und ist keine gültige Ground Truth. Nur die Runde-2-Nachprüfung zählt.

Bei einem FAIL: nicht nur Accuracy zählen, sondern prüfen, WELCHE
Invariante/Regel verletzt wurde (siehe Kommentar je Fall).
"""

from tcl.proposition import AssertionStatus, Proposition
from tcl.relation import SemanticCompatibility
from tcl.content_relation import content_relation_fn


def prop(text: str) -> Proposition:
    return Proposition(proposition_text=text, assertion_status=AssertionStatus.ASSERTED)


# (name, text_a, text_b, expected) — expected ist der Runde-1/2-Konsens aus dem Vault-Corpus
CASES = [
    # Runde 1 (Fall 12 ausgeschlossen, siehe Modul-Docstring)
    ("case_1_bare_symmetric", "Wir nutzen Jira.", "Wir nutzen Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_2_confirmation", "Wir nutzen aktuell Jira.", "Wir nutzen weiterhin Jira.", SemanticCompatibility.COMPATIBLE),
    ("case_3_paraphrase", "Wir nutzen Jira.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_4_unrelated_domain", "Wir nutzen Jira.", "Das Wetter war gestern schön.", SemanticCompatibility.COMPATIBLE),
    ("case_5_explicit_parallel", "Wir nutzen Jira.", "Wir nutzen zusätzlich Linear für Kundenanfragen.", SemanticCompatibility.COMPATIBLE),
    ("case_6_negation_compatible", "Wir nutzen kein Jira mehr.", "Wir nutzen Linear.", SemanticCompatibility.COMPATIBLE),
    ("case_7_quantitative_conflict", "Der Preis liegt bei 49 €.", "Der Preis liegt bei 59 €.", SemanticCompatibility.INCOMPATIBLE),
    ("case_8_vague_opposite", "Das Team ist klein.", "Das Team ist groß.", SemanticCompatibility.INCOMPATIBLE),
    ("case_9_refinement", "Das Team wächst.", "Das Team hat jetzt 12 Mitglieder.", SemanticCompatibility.COMPATIBLE),
    ("case_10_cross_lingual", "We use Jira.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_11_weak_domain_link", "Es lief heute gut.", "Der Umsatz stieg um 5 %.", SemanticCompatibility.COMPATIBLE),
    ("case_13_weak_domain_link_2", "Wir nutzen Jira.", "Das Projekt läuft nach Plan.", SemanticCompatibility.COMPATIBLE),
    ("case_14_different_predicates", "Jira ist unser Ticketsystem.", "Jira ist schwer zu bedienen.", SemanticCompatibility.COMPATIBLE),
    ("case_15_same_tool_diff_purpose", "Wir nutzen Jira für Bug-Tracking.", "Wir nutzen Jira für Projektmanagement.", SemanticCompatibility.COMPATIBLE),
    # Runde 2 — Familie A (Slot-Identifikation)
    ("case_1a_explicit_slot", "Wir nutzen Jira als Bug-Tracking-Tool.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_1b_weak_context_both_sides", "Wir nutzen Jira. Die Ticket-Warteschlange wächst.", "Wir nutzen Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_1d_explicit_exclusion", "Wir nutzen Jira für Bug-Tracking.", "Wir nutzen Linear für Vertriebs-Pipelines.", SemanticCompatibility.COMPATIBLE),
    ("case_3a_explicit_slot", "Jira ist unser Bug-Tracking-Tool.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_3b_anchor_on_one_side", "Wir nutzen Jira. Die Bug-Liste wächst täglich.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_3d_explicit_exclusion", "Wir nutzen Jira für Projektmanagement.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    ("case_10a_explicit_slot_crosslingual", "Jira is our bug-tracking tool.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_10b_weak_context_both_sides_crosslingual", "We use Jira. The bug queue keeps growing.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("case_10d_explicit_exclusion_crosslingual", "We use Jira for project planning.", "Unser Bug-Tracking-Tool ist jetzt Linear.", SemanticCompatibility.COMPATIBLE),
    # Runde 2 — Familie B (Domänen-Nähe, sollte irrelevant sein)
    ("case_11a_strong_domain_link", "Der Verkaufstag lief heute gut.", "Der Umsatz stieg um 5 %.", SemanticCompatibility.COMPATIBLE),
    ("case_11c_no_domain_link", "Es lief heute gut.", "Der Server wurde neu gestartet.", SemanticCompatibility.COMPATIBLE),
    ("case_13a_strong_domain_link", "Wir nutzen Jira für dieses Projekt.", "Das Projekt läuft nach Plan.", SemanticCompatibility.COMPATIBLE),
    ("case_13c_no_domain_link", "Wir nutzen Jira.", "Der Kaffee in der Küche ist alle.", SemanticCompatibility.COMPATIBLE),
    # Der wichtigste Einzelfall — eigener Architekturtest, siehe Fund 3
    ("temporal_separation_must_not_imply_compatibility", "Früher haben wir Jira genutzt.", "Wir nutzen jetzt Linear.", SemanticCompatibility.INCOMPATIBLE),
    ("domain_marital_status", "Sie ist verheiratet.", "Sie ist ledig.", SemanticCompatibility.INCOMPATIBLE),
    ("domain_pet_names_unrelated", "Der Hund heißt Rex.", "Die Katze heißt Minka.", SemanticCompatibility.COMPATIBLE),
    ("domain_world_knowledge_control", "Wir wohnen in Hamburg.", "Wir wohnen in Köln.", SemanticCompatibility.INCOMPATIBLE),
]


def main() -> None:
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

    print(f"\n{passed}/{len(CASES)} bestanden.")
    if failed:
        print("Fehlgeschlagen (Invariante prüfen, nicht nur Prompt anpassen):")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()