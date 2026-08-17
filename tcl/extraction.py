"""
extract_propositions_fn — Schritt 1 des Architecture Contract v0
(Proposition Extraction), siehe Temporal Continuity/Proposition-
Extraction Contract v0 (finalisiert 17.08., 18 Minimalfälle über
zwei Blind-Triangulationsrunden).

CONTRACT:
Input: ein Turn-Text (eine vollständige Nutzeräußerung, ggf. mehrere
Sätze — NICHT satzweise vorverarbeitet).
Output: list[ExtractedProposition] — nur Text + Turn-Provenienz.

decomposition_group_id wird NICHT vom LLM erzeugt, sondern
deterministisch in Python vergeben (eine ID pro Aufruf) - da die Gruppe
per Entscheidung immer turn-basiert ist, braucht das LLM diese
Entscheidung gar nicht zu treffen. Kleineres, robusteres Schema.

Negative Verantwortung (siehe Contract):
- KEINE Vorwegnahme von assertion_status (Schritt 2)
- KEINE Vorwegnahme von transition_type (Schritt 2)
- KEINE Vorwegnahme von raw_temporal_expression (Schritt 3)
- KEINE Datumsarithmetik (normalize() bleibt in temporal_engine.py,
  wird hier NICHT aufgerufen)
- KEINE Vorwegnahme von state_relation (Schritt 7)

Nutzt Tool-Use wie content_relation_fn (siehe dortige Lehre 17.08.:
reine Prompt-Instruktionen gegen Freitext-Ausbrüche reichen nicht
zuverlässig, erzwungene Struktur über die API schon).
"""

from __future__ import annotations

import uuid

from .proposition import ExtractedProposition

_SYSTEM_PROMPT = """Du zerlegst eine Nutzeräußerung (Turn) in einzelne Propositionen — eigenständige, unterscheidbare Sachverhalts-/Zustandsbehauptungen.

SPLITTING-REGEL:
Zerlege den Turn in mehrere Propositionen, wenn er mehrere eigenständige, unterscheidbare Sachverhaltsbehauptungen enthält. Das gilt UNABHÄNGIG davon, ob:
- die Behauptungen zeitlich versetzt sind (z.B. "war X, ist jetzt Y")
- sie kausal verknüpft sind (z.B. "X, weil Y")
- der Turn insgesamt hypothetisch/konditional ist (z.B. "wenn X, dann Y" -> zwei Propositionen: die Bedingung UND die Konsequenz, getrennt. Bewerte NICHT, ob das tatsächlich zutrifft — das ist hier nicht deine Aufgabe.)
- es sich um mehrere Sätze im selben Turn handelt, auch wenn sie thematisch nichts miteinander zu tun haben (z.B. "Wir nutzen Jira. Der Kaffee ist alle." -> zwei Propositionen)

KEINE Zerlegung bei reiner Wiederholung oder sprachlicher Verstärkung, die keinen neuen Ausschluss oder keine neue Information enthält (z.B. "Wir nutzen Jira. Wir nutzen Jira." -> eine Proposition). Eine Präzisierung, die etwas explizit ausschließt, das die erste Aussage offenließ (z.B. "Wir nutzen Jira. Wir nutzen wirklich nur Jira." -> zwei Propositionen, da "nur" eine Alternative ausschließt), gilt dagegen als eigenständige neue Proposition.

WICHTIG, was du NICHT tun sollst:
- Entscheide NICHT, ob eine Proposition tatsächlich behauptet wird oder nur hypothetisch ist (das ist eine separate, hier nicht gefragte Frage).
- Entscheide NICHT, ob eine Proposition eine andere ablöst, ihr widerspricht oder sie fortsetzt.
- Berechne KEINE Datumsangaben oder Zeitintervalle — gib nur den Proposition-Text wieder, so wie er im Turn steht (ggf. leicht geglättet für Lesbarkeit, aber ohne Interpretation).

Gib jede Proposition als eigenständigen, in sich verständlichen Text wieder (löse Anaphern wie "es"/"er"/"sie" auf, wo eindeutig möglich)."""


def extract_propositions_fn(turn_text: str) -> list[ExtractedProposition]:
    """
    Erfordert ANTHROPIC_API_KEY und das Paket 'anthropic'.
    """
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0,
        system=_SYSTEM_PROMPT,
        tools=[
            {
                "name": "extract_propositions",
                "description": "Gib die Liste der extrahierten Propositionen zurück.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "propositions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Jede einzelne Proposition als eigenständiger Text.",
                        },
                    },
                    "required": ["propositions"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "extract_propositions"},
        messages=[{"role": "user", "content": turn_text}],
    )

    tool_use_block = next(block for block in message.content if block.type == "tool_use")
    group_id = str(uuid.uuid4())
    return [
        ExtractedProposition(proposition_text=text, decomposition_group_id=group_id)
        for text in tool_use_block.input["propositions"]
    ]