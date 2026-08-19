"""
MCP-Server für den Temporal Context Layer. Siehe MCP-Interface Contract
v0 (18.08.). Fünf Tools, die exakt die Zwei-Schritt-Interaktion für
Schritt 7a abbilden — der Server selbst führt an KEINER Stelle einen
eigenen LLM-Aufruf aus, alle semantische Arbeit (Extraction, Assertion
Check, Temporal Expression, Content Relation) macht das aufrufende
Modell selbst, bevor/während es diese Tools nutzt.

decomposition_group_id: für v0 identisch mit turn_id (siehe Decision
2026-08-18: "aktuell 1:1-Entsprechung, könnte später divergieren" -
hier bewusst genutzt, um dem aufrufenden Modell keine eigene
Gruppen-ID-Erzeugung aufzubürden).
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Bootstrap: mcp dev lädt diese Datei eigenständig, nicht als Teil des
# tcl-Pakets - Projekt-Root muss selbst auf sys.path, damit absolute
# Importe (tcl.xxx) funktionieren, unabhängig von der Lademethode.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import MCPServer

from tcl.proposition import AssertionStatus, Proposition, TransitionType
from tcl.pipeline import process_new_proposition_with_judgments
from tcl.relation import SemanticCompatibility
from tcl.review import get_candidates_for_review as _get_candidates_for_review
from tcl.postgres_store import PostgresStore
from tcl.temporal_engine import normalize
from tcl.query import resolve_current_state, format_answer

mcp = MCPServer("temporal-context-layer")

_store = PostgresStore()  # 18.08.: von InMemoryStore umgehängt, siehe Contract


@mcp.tool()
def start_conversation() -> str:
    """Startet eine neue Conversation (Scope-Grenze für Retrieval). Gibt die conversation_id zurück."""
    return _store.add_conversation()


@mcp.tool()
def begin_turn(conversation_id: str, turn_text: str) -> str:
    """
    Persistiert einen neuen Turn (IMMER, Audit-Trail-Prinzip). Der
    Zeitpunkt wird NICHT vom aufrufenden Modell übergeben, sondern
    server-seitig aus der echten Systemzeit gesetzt (autoritative
    Quelle, 19.08. — verhindert erfundene Uhrzeiten wie Mitternacht).
    Gibt die turn_id zurück.
    """
    return _store.add_turn(conversation_id, turn_text)


@mcp.tool()
def get_candidates_for_review(conversation_id: str, proposition_text: str) -> list[dict]:
    """
    Schritt 1 der Content-Relation-Beurteilung: gibt die Liste bereits
    gespeicherter, ASSERTED Propositionen dieser Conversation zurück.
    Das aufrufende Modell muss für JEDEN Kandidaten selbst beurteilen,
    ob er zur neuen Proposition COMPATIBLE, INCOMPATIBLE oder
    UNDETERMINED ist (siehe Regeln im Content-Relation Mini-Corpus v0),
    bevor es ingest_proposition aufruft.
    """
    dummy = Proposition(proposition_text=proposition_text, assertion_status=AssertionStatus.ASSERTED)
    candidates = _get_candidates_for_review(_store, conversation_id, dummy)
    return [dict(c) for c in candidates]


@mcp.tool()
def ingest_proposition(
    turn_id: str,
    conversation_id: str,
    proposition_text: str,
    assertion_status: AssertionStatus,
    transition_type: TransitionType,
    raw_temporal_expression: Optional[str],
    judgments: dict[str, SemanticCompatibility],
) -> dict:
    """
    Speichert EINE vom aufrufenden Modell bereits vollständig
    klassifizierte Proposition.

    assertion_status:
    - ASSERTED: Proposition wird als aktueller Fakt behauptet.
    - NOT_ASSERTED: Proposition wird nicht als Fakt behauptet.

    transition_type:
    - BARE: keine Vorzustandsreferenz; Standard für eine erstmalige,
      schlichte Behauptung.
    - CONTINUATION: betont die Fortdauer eines bestehenden Zustands,
      z.B. "weiterhin" oder "nach wie vor".
    - TRANSITION: markiert einen Bruch mit einem vorherigen Zustand,
      z.B. "seit X", "nicht mehr" oder "jetzt statt".

    raw_temporal_expression: einer der festen Vokabular-Werte aus dem
    Temporal-Expression Contract v0 ("aktuell", "since <weekday>",
    "from <weekday> through <weekday>", "<N> days/weeks ago", "until
    <TT.MM.JJJJ>", "on <weekday>" — z.B. "on monday" für einen einzelnen,
    bestimmten vergangenen Tag) oder null, falls kein passender Ausdruck
    erkennbar war.

    Bei NOT_ASSERTED wird ohne Relationen gespeichert (Audit-Trail);
    judgments wird ignoriert.

    Bei ASSERTED muss judgments für jede proposition_id aus einem
    vorherigen get_candidates_for_review-Aufruf einen Wert
    ("COMPATIBLE"/"INCOMPATIBLE"/"UNDETERMINED") enthalten.

    Gibt eine Zusammenfassung der berechneten Relationen zurück
    (bei ASSERTED) oder eine Bestätigung (bei NOT_ASSERTED).
    """
    assertion_time = _store.get_turn_assertion_time(turn_id)
    normalized = normalize(raw_temporal_expression, assertion_time=assertion_time)
    proposition = Proposition(
        proposition_text=proposition_text,
        assertion_status=assertion_status,
        assertion_time=assertion_time,
        raw_temporal_expression=raw_temporal_expression,
        normalized_temporal_reference=normalized,
        transition_type=transition_type,
        decomposition_group_id=turn_id,
    )

    if assertion_status == AssertionStatus.NOT_ASSERTED:
        _store.ingest_propositions(turn_id, [proposition], [])
        return {"stored": True, "relations": []}

    relations = process_new_proposition_with_judgments(
        _store,
        conversation_id,
        turn_id,
        proposition,
        judgments,
    )

    return {
        "stored": True,
        "relations": [
            {
                "with_proposition_id": r.proposition_a_id,
                "state_relation": r.state_relation.value,
            }
            for r in relations
        ],
    }


@mcp.tool()
def query_current_state(conversation_id: str, proposition_ids: list[str], query_time: str) -> dict:
    """
    Beantwortet "was gilt aktuell" für die übergebenen Propositionen.
    query_time als ISO-8601-String - der Abfragezeitpunkt (nicht der
    Zeitpunkt, zu dem etwas behauptet wurde).
    """
    result = resolve_current_state(_store, proposition_ids, query_time=datetime.fromisoformat(query_time))
    return {
        "resolved": result.resolved,
        "answer": format_answer(result),
    }

@mcp.tool()
def search_temporal_memory(conversation_id: str, search_term: str) -> list[dict]:
    """
    Temporal Memory: "Wann haben wir über X gesprochen?" Reine
    Textsuche über bereits gespeicherte Turns dieser Conversation,
    KEIN LLM-Aufruf, findet nur wörtlich vorkommende Begriffe (mit
    einfacher Wortform-Erkennung), keine Paraphrasen. Gibt eine Liste
    von Treffern zurück, jeweils mit Turn-Text und Zeitpunkt, sortiert
    von früh nach spät.
    """
    return _store.search_turns(conversation_id, search_term)

@mcp.tool()
def get_event_time(turn_id: str) -> list[dict]:
    """
    Ergänzung zu search_temporal_memory: liefert für einen gefundenen
    Turn die dazugehörigen Propositionen MIT aufgelöstem, absolutem
    Ereignisdatum (normalized_temporal_reference) — z.B. "am Montag"
    wird hier zu "2026-08-17", nicht mehr relativ.

    WICHTIG für die Antwortformulierung: Nenne dem Nutzer das absolute
    Ereignisdatum aus diesem Tool, NICHT die relative Formulierung aus
    dem rohen Turn-Text von search_temporal_memory — eine relative
    Angabe wie "am Montag" wird mit der Zeit mehrdeutig, ein absolutes
    Datum bleibt es nicht.
    """
    props = _store.get_propositions_for_turn(turn_id)
    return [
        {
            "proposition_text": p.proposition_text,
            "event_start": p.normalized_temporal_reference.start.isoformat() if p.normalized_temporal_reference and p.normalized_temporal_reference.start else None,
            "event_end": p.normalized_temporal_reference.end.isoformat() if p.normalized_temporal_reference and p.normalized_temporal_reference.end else None,
        }
        for p in props
    ]

if __name__ == "__main__":
    mcp.run()