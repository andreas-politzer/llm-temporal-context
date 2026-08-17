"""
Regressionstest für tcl.extraction.extract_propositions_fn gegen den
Proposition-Extraction-Corpus (16 Fälle aus zwei Blind-Triangulations-
runden, siehe Temporal Continuity/Proposition-Extraction Contract v0).

v0-Einschränkung: geprüft wird nur die ANZAHL der Propositionen, nicht
der exakte Wortlaut (der variiert legitim durch Paraphrasierung).
Texte werden zur manuellen Durchsicht ausgegeben. decomposition_group_id
wird nicht vom LLM getestet (deterministisch in Python vergeben, siehe
extraction.py) - nur geprüft, dass alle Propositionen eines Aufrufs
dieselbe Gruppe teilen (Interna-Check, kein LLM-Verhalten).
"""

from tcl.extraction import extract_propositions_fn

# (name, turn_text, expected_count)
CASES = [
    ("case_1_baseline", "Wir nutzen Jira.", 1),
    ("case_2_self_transition", "Es war lange zuverlässig, ist es aber nicht mehr.", 2),
    ("case_3_enumeration", "Wir nutzen Jira und Slack.", 2),
    ("case_4_causal", "Wir nutzen Jira, weil es sich bewährt hat.", 2),
    ("case_5_conditional", "Wenn das Budget reicht, wechseln wir zu Linear.", 2),
    ("case_6_independent_timepoints", "Gestern war es kalt, heute ist es mild.", 2),
    ("case_7_multi_sentence_turn", "Wir haben lange Jira genutzt. Das hat gut funktioniert. Seit letzter Woche sind wir auf Linear.", 3),
    ("case_8_unrelated_topics", "Wir nutzen Jira. Der Kaffee in der Küche ist alle.", 2),
    ("case_9_different_subjects", "Anna nutzt Jira, Ben nutzt Linear.", 2),
    ("case_10_precision_exclusion", "Wir nutzen Jira. Wir nutzen wirklich nur Jira.", 2),
    ("gid_1_strong_link", "Wir nutzen Jira. Jira ist manchmal langsam.", 2),
    ("gid_2_loose_link", "Das Meeting war heute lang. Wir haben über das Budget gesprochen.", 2),
    ("gid_3_unrelated_reversed", "Ben hat heute Geburtstag. Wir nutzen Jira.", 2),
    ("cond_2_consistency_check", "Falls die Migration klappt, sparen wir viel Zeit.", 2),
    ("rep_1_pure_repetition", "Wir nutzen Jira. Wir nutzen Jira.", 1),
    ("rep_3_new_information", "Wir nutzen Jira. Wir nutzen es seit drei Jahren.", 2),
]


def main() -> None:
    passed = 0
    failed = []
    for name, turn_text, expected_count in CASES:
        propositions = extract_propositions_fn(turn_text)
        got_count = len(propositions)
        status = "OK" if got_count == expected_count else "FAIL"
        marker = "✓" if status == "OK" else "✗"
        print(f"[{marker} {status}] {name}: got={got_count}, expected={expected_count}")
        for p in propositions:
            print(f"    - {p.proposition_text}")
        group_ids = {p.decomposition_group_id for p in propositions}
        if len(group_ids) > 1:
            print(f"    ⚠ WARNUNG: uneinheitliche group_id innerhalb eines Aufrufs: {group_ids}")
        if got_count == expected_count:
            passed += 1
        else:
            failed.append(name)
        print()

    print(f"{passed}/{len(CASES)} bestanden (nur Anzahl geprüft, Wortlaut manuell prüfen).")
    if failed:
        print("Fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()