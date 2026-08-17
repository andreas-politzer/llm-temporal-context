"""
assertion_check_fn — Schritt 2 des Architecture Contract v0
(Assertion Check + transition_type), siehe Temporal Continuity/
Assertion-Check Contract v0 (finalisiert 17.08., 7 Minimalfälle,
Blind-Triangulation).

CONTRACT:
Input: (turn_text, list[ExtractedProposition]) — der Original-Turn ist
PFLICHT als Kontextquelle, nicht optional. Schritt 1 entfernt bei der
Zerlegung bewusst Information wie Konditionalität aus den einzelnen
Proposition-Texten; ohne Turn-Kontext könnte Schritt 2 das nicht mehr
erkennen (siehe Contract, Konditional-Fall).

Output: list[Proposition] — assertion_status und transition_type
gesetzt, assertion_time/raw_temporal_expression bleiben None (Schritt
3, hier nicht Aufgabe), decomposition_group_id von ExtractedProposition
übernommen.

Ein API-Aufruf pro Turn (nicht pro Proposition) — alle Propositionen
eines Turns teilen ohnehin denselben Kontext, unnötig sie einzeln
abzufragen.

Negative Verantwortung: KEINE Vorwegnahme von raw_temporal_expression/
assertion_time (Schritt 3), KEINE state_relation (Schritt 7).
"""

from __future__ import annotations

from .proposition import AssertionStatus, ExtractedProposition, Proposition, TransitionType

_SYSTEM_PROMPT = """Du bewertest für jede extrahierte Proposition eines Turns zwei unabhängige Eigenschaften: assertion_status und transition_type.

ASSERTION_STATUS (ASSERTED oder NOT_ASSERTED):
- ASSERTED: Die Proposition wird im Turn als aktuell zutreffender Fakt behauptet.
- NOT_ASSERTED: Die Proposition wird NICHT als Fakt behauptet — z.B. weil sie:
  - Teil eines Konditionalsatzes ist (sowohl Bedingung ALS AUCH Konsequenz sind NOT_ASSERTED, nicht nur die Konsequenz)
  - nur eine Vermutung/unsichere Aussage ist (z.B. "ich glaube", "vielleicht")
Eine verneinte Aussage ("wir nutzen kein X mehr") ist ASSERTED — der neue (negative) Zustand wird als Fakt behauptet, nur eben negativ formuliert.

TRANSITION_TYPE (BARE, CONTINUATION, oder TRANSITION):
- BARE: schlichte Zustandsbehauptung, kein Bezug zu einem Vorzustand.
- CONTINUATION: betont explizit die Fortdauer eines bestehenden Zustands (Signalwörter wie "weiterhin", "noch", "nach wie vor").
- TRANSITION: markiert einen Bruch mit einem vorherigen Zustand (Signalwörter wie "nicht mehr", "seit X", "jetzt statt", "ist das anders").

WICHTIG: Nutze für BEIDE Bewertungen den GESAMTEN Turn-Text als Kontext, nicht nur die isolierte Proposition — die Proposition kann Marker verloren haben, die nur im Turn noch sichtbar sind (z.B. bei einem aus einem Konditionalsatz extrahierten Konsequenz-Teil).

assertion_status und transition_type sind UNABHÄNGIG voneinander zu bestimmen — eine Proposition kann z.B. gleichzeitig NOT_ASSERTED und CONTINUATION sein (eine unsichere Vermutung über einen fortdauernden Zustand)."""


def assertion_check_fn(turn_text: str, extracted_propositions: list[ExtractedProposition]) -> list[Proposition]:
    """
    Erfordert ANTHROPIC_API_KEY und das Paket 'anthropic'.
    """
    import anthropic

    client = anthropic.Anthropic()

    props_list = "\n".join(f"{i + 1}. {p.proposition_text}" for i, p in enumerate(extracted_propositions))
    user_message = f'Turn: "{turn_text}"\n\nPropositionen:\n{props_list}'

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0,
        system=_SYSTEM_PROMPT,
        tools=[
            {
                "name": "classify_propositions",
                "description": "Gib assertion_status und transition_type für jede Proposition zurück, in derselben Reihenfolge.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "classifications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "assertion_status": {"type": "string", "enum": ["ASSERTED", "NOT_ASSERTED"]},
                                    "transition_type": {"type": "string", "enum": ["BARE", "CONTINUATION", "TRANSITION"]},
                                },
                                "required": ["assertion_status", "transition_type"],
                            },
                        },
                    },
                    "required": ["classifications"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "classify_propositions"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next(block for block in message.content if block.type == "tool_use")
    classifications = tool_use_block.input["classifications"]

    if len(classifications) != len(extracted_propositions):
        raise ValueError(
            f"Anzahl Klassifikationen ({len(classifications)}) stimmt nicht mit "
            f"Anzahl Propositionen ({len(extracted_propositions)}) überein"
        )

    result = []
    for extracted, classification in zip(extracted_propositions, classifications):
        result.append(
            Proposition(
                proposition_text=extracted.proposition_text,
                assertion_status=AssertionStatus(classification["assertion_status"]),
                transition_type=TransitionType(classification["transition_type"]),
                decomposition_group_id=extracted.decomposition_group_id,
            )
        )
    return result