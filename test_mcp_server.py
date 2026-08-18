"""
Simuliert den kompletten MCP-Tool-Fluss OHNE echten MCP-Host: ruft die
mit @mcp.tool() dekorierten Funktionen direkt als normale Python-
Funktionen auf (der Dekorator registriert nur, ändert die Funktion
selbst nicht). Ersetzt das "aufrufende Modell" durch von Hand
geschriebene Urteile - reine Plumbing-Prüfung, kostenlos, kein API-Key
nötig, analog zu test_store_contract.py.
"""

from datetime import datetime

from tcl.proposition import AssertionStatus, TransitionType
from tcl.relation import SemanticCompatibility

from tcl.server import (
    start_conversation,
    begin_turn,
    get_candidates_for_review,
    ingest_proposition,
    query_current_state,
)


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== MCP-Fluss: erste Proposition, kein Kandidat, direkt speichern ===")
    conv = start_conversation()
    turn1 = begin_turn(conv, "Der Vertrag mit Anbieter A läuft bis Juni 2026.", "2026-01-01T10:00:00")

    candidates1 = get_candidates_for_review(conv, "Der Vertrag mit Anbieter A läuft bis Juni 2026.")
    check("Erste Proposition: keine Kandidaten (Store ist leer)", candidates1, [])

    result1 = ingest_proposition(
        turn_id=turn1, conversation_id=conv,
        proposition_text="Der Vertrag mit Anbieter A läuft bis Juni 2026.",
        assertion_status=AssertionStatus.ASSERTED, transition_type=TransitionType.BARE,
        raw_temporal_expression=None,  # kein festes Vokabular-Muster hier, bewusst None
        assertion_time="2026-01-01T10:00:00", judgments={},
    )
    check("Erste Proposition: gespeichert, keine Relationen", result1, {"stored": True, "relations": []})

    print("\n=== MCP-Fluss: zweite Proposition, ein Kandidat, Modell-Urteil simuliert ===")
    turn2 = begin_turn(conv, "Seit Mai arbeiten wir mit Anbieter C.", "2026-05-01T09:00:00")

    candidates2 = get_candidates_for_review(conv, "Seit Mai arbeiten wir mit Anbieter C.")
    check("Zweite Proposition: genau 1 Kandidat gefunden", len(candidates2), 1)
    candidate_id = candidates2[0]["proposition_id"]

    # Simuliertes Modell-Urteil, wie es sonst das aufrufende Modell liefern würde
    judgments = {candidate_id: SemanticCompatibility.INCOMPATIBLE}

    result2 = ingest_proposition(
        turn_id=turn2, conversation_id=conv,
        proposition_text="Seit Mai arbeiten wir mit Anbieter C.",
        assertion_status=AssertionStatus.ASSERTED, transition_type=TransitionType.TRANSITION,
        raw_temporal_expression="since monday",  # Näherung, nur damit normalize() etwas parsen kann
        assertion_time="2026-05-01T09:00:00", judgments=judgments,
    )
    check("Zweite Proposition: 1 Relation berechnet", len(result2["relations"]), 1)
    check("Zweite Proposition: state_relation ist SUPERSEDES", result2["relations"][0]["state_relation"], "SUPERSEDES")

    print("\n=== MCP-Fluss: Query ===")
    all_ids = [candidate_id]
    # zweite Proposition-ID herausfinden: über erneuten Kandidaten-Aufruf
    # (sie ist jetzt selbst ein Kandidat für eine hypothetische dritte Proposition)
    candidates3 = get_candidates_for_review(conv, "irrelevanter Platzhalter")
    all_ids = [c["proposition_id"] for c in candidates3]
    check("Query-Vorbereitung: 2 Propositionen insgesamt im Store", len(all_ids), 2)

    query_result = query_current_state(conv, all_ids, "2026-08-18T12:00:00")
    check("Query: aufgelöst", query_result["resolved"], True)
    print(f"  -> {query_result['answer']}")

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()