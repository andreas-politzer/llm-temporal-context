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
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

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
def begin_turn(conversation_id: str, turn_text: str, assertion_time: str) -> str:
    """
    Persistiert einen neuen Turn (IMMER, Audit-Trail-Prinzip).
    assertion_time als ISO-8601-String (z.B. "2026-08-18T14:00:00").
    Gibt die turn_id zurück - wird für die folgenden Tool-Aufrufe gebraucht.
    """
    return _store.add_turn(conversation_id, turn_text, datetime.fromisoformat(assertion_time))


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
    assertion_status: str,
    transition_type: str,
    raw_temporal_expression: Optional[str],
    assertion_time: str,
    judgments: dict[str, str],
) -> dict:
    """
    Speichert EINE vom aufrufenden Modell bereits vollständig
    klassifizierte Proposition. Bei assertion_status="NOT_ASSERTED":
    wird ohne Relationen gespeichert (Audit-Trail), judgments wird
    ignoriert. Bei "ASSERTED": judgments MUSS für jede proposition_id
    aus einem vorherigen get_candidates_for_review-Aufruf einen Wert
    ("COMPATIBLE"/"INCOMPATIBLE"/"UNDETERMINED") enthalten.

    raw_temporal_expression: einer der festen Vokabular-Werte aus dem
    Temporal-Expression Contract v0 ("aktuell", "since <weekday>",
    "from <weekday> through <weekday>", "<N> days/weeks ago") oder null,
    falls kein passender Ausdruck erkennbar war.

    Gibt eine Zusammenfassung der berechneten Relationen zurück (bei
    ASSERTED) oder eine Bestätigung (bei NOT_ASSERTED).
    """
    status = AssertionStatus(assertion_status)
    t_type = TransitionType(transition_type)
    normalized = normalize(raw_temporal_expression, assertion_time=datetime.fromisoformat(assertion_time))

    proposition = Proposition(
        proposition_text=proposition_text,
        assertion_status=status,
        assertion_time=datetime.fromisoformat(assertion_time),
        raw_temporal_expression=raw_temporal_expression,
        normalized_temporal_reference=normalized,
        transition_type=t_type,
        decomposition_group_id=turn_id,
    )

    if status == AssertionStatus.NOT_ASSERTED:
        _store.ingest_propositions(turn_id, [proposition], [])
        return {"stored": True, "relations": []}

    judgments_typed = {k: SemanticCompatibility(v) for k, v in judgments.items()}
    relations = process_new_proposition_with_judgments(
        _store, conversation_id, turn_id, proposition, judgments_typed
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

if __name__ == "__main__":
    mcp.run()