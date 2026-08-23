"""
Testet get_recent_events / get_temporal_context_frame (22.08.).
Kostenlos, InMemoryStore, kein API-Key nötig.
"""

from datetime import datetime, timedelta

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.store import InMemoryStore
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    store = InMemoryStore()
    now = datetime(2026, 8, 22, 14, 0)

    print("=== Sieben Ereignisse anlegen, über mehrere Tage/Conversations verteilt ===")
    for i, (days_ago, text) in enumerate([
        (0, "Heute: workspace_id Bugfix diskutiert."),
        (1, "Gestern: note_moment implementiert."),
        (2, "Vorgestern: Workspace-Scope-Fund gemacht."),
        (3, "Vor 3 Tagen: Read/Write-Architektur besprochen."),
        (4, "Vor 4 Tagen: Message-Level Timestamping gefixt."),
        (5, "Vor 5 Tagen: on-weekday-Vokabular ergänzt."),
        (6, "Vor 6 Tagen: Temporal Memory gebaut."),
    ]):
        conv = store.add_conversation()  # jedes Ereignis in eigener "Sitzung"
        turn = store.add_turn(conv, text, now - timedelta(days=days_ago))
        prop = Proposition(
            proposition_text=text,
            assertion_status=AssertionStatus.ASSERTED,
            assertion_time=now - timedelta(days=days_ago),
            raw_temporal_expression=f"{days_ago} days ago" if days_ago > 0 else "aktuell",
            normalized_temporal_reference=normalize(
                f"{days_ago} days ago" if days_ago > 0 else "aktuell",
                assertion_time=now - timedelta(days=days_ago),
            ),
            transition_type=TransitionType.BARE,
            turn_id=turn,
        )
        store.ingest_propositions(turn, [prop], [])

    print("\n=== get_recent_events: nur die neuesten 5, absteigend sortiert ===")
    events = store.get_recent_events(limit=5)
    check("Genau 5 Ereignisse zurückgegeben (limit greift)", len(events), 5)
    check("Neuestes Ereignis zuerst", events[0]["text"], "Heute: workspace_id Bugfix diskutiert.")
    check("Fünftneuestes Ereignis zuletzt in der Liste", events[4]["text"], "Vor 4 Tagen: Message-Level Timestamping gefixt.")
    check("Alle time_source == EVENT (alle hatten raw_temporal_expression)", all(e["time_source"] == "EVENT" for e in events), True)

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()