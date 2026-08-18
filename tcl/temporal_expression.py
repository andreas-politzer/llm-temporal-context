"""
temporal_expression_fn — Schritt 3 des Architecture Contract v0
(Temporal Expression Extraction), siehe Temporal Continuity/
Temporal-Expression Contract v0.

CONTRACT:
Input: (turn_text, list[Proposition] aus Schritt 2).
Output: list[Proposition] mit raw_temporal_expression gesetzt (oder
None, falls kein passender Ausdruck).

assertion_time wird NICHT hier erzeugt — reines Kontext-Metadatum von
außen, siehe Architecture Contract v0, Schritt 3.

WICHTIGE EIGENHEIT von tcl/temporal_engine.py::normalize(): das
erwartete Vokabular ist SPRACHLICH GEMISCHT — Struktur-Schlüsselwörter
sind hart englisch ("since", "from ... through/to/until ...",
"... days/weeks ago"), aber Wochentagsnamen dürfen deutsch ODER
englisch sein (_WEEKDAYS-Dict enthält beide). "aktuell"/"currently"/
"nach wie vor"/"still"/"weiterhin" sind alle gleichwertig (Punkt am
assertion_time - auch "weiterhin", trotz semantisch andauerndem
Charakter, wird intern wie ein Punkt behandelt, nicht wie ein offenes
Intervall - bestehendes normalize()-Verhalten, hier nicht verändert).

v0-Entscheidung (17.08.): unmarkierte Propositionen bekommen "aktuell"
als Default (Konsistenz mit der gesamten bisherigen Testreihe, die das
implizit voraussetzte). Ausdrücke außerhalb des bekannten Vokabulars
werden NICHT übersetzt oder geraten - raw_temporal_expression bleibt
None, normalize() macht daraus UNDETERMINED (kein Vokabular-Ausbau
heute, bewusst zurückgestellt).

Negative Verantwortung: KEINE eigene Datumsarithmetik (normalize()
selbst wird hier NICHT aufgerufen - das bleibt Schritt 4).
"""

from __future__ import annotations

from .proposition import Proposition

_SYSTEM_PROMPT = """Du extrahierst für jede Proposition eines Turns den passenden zeitlichen Ausdruck (raw_temporal_expression) aus einem FEST VORGEGEBENEN Vokabular.

Deine Antwort für jede Proposition MUSS EXAKT eine der folgenden vier Formen sein, oder ein leerer String — NIEMALS etwas anderes, NIEMALS der Proposition-Text selbst, NIEMALS der ursprüngliche Zeitausdruck aus dem Turn wörtlich wiedergegeben:

1. "aktuell" — für Propositionen ohne expliziten Zeitmarker (Default) ODER mit "aktuell"/"jetzt"/"nach wie vor"/"still"/"weiterhin"/"currently" im Text.
2. "since <wochentag>" — bei explizitem "seit <Wochentag>". "since" bleibt IMMER englisch, der Wochentag darf deutsch oder englisch sein.
3. "from <wochentag> through <wochentag>" — bei einem festen Zeitraum zwischen zwei Wochentagen. "from"/"through" bleiben IMMER englisch.
4. "<N> days ago" oder "<N> weeks ago" — bei "vor N Tagen/Wochen". "days"/"weeks"/"ago" bleiben IMMER englisch, nur die Zahl wird eingesetzt.
5. "until DD.MM.YYYY" — bei einem konkreten Ablauf-/Gültigkeitsdatum im Text (z.B. "gültig bis 30.06.2026", "läuft bis zum 30. Juni 2026"). "until" bleibt IMMER englisch, das Datum wird als DD.MM.YYYY eingesetzt (deutsche Reihenfolge Tag.Monat.Jahr), unabhängig davon, wie das Datum im Originaltext geschrieben war.
6. "" (leerer String) — wenn der Zeitausdruck NICHT in eine der obigen vier Formen (2/3/4/5) passt (z.B. "im März", "letztes Jahr" ohne konkretes Datum)...
- Proposition "Wir nutzen Jira." (kein Marker im Turn) → FALSCH: "Wir nutzen Jira." → RICHTIG: "aktuell"
- Turn enthält "im März" → FALSCH: "im März" → RICHTIG: "" (leerer String, weil außerhalb des Vokabulars)

Deine Antwort ist IMMER entweder exakt eine der vier Vokabular-Formen oder ein leerer String — nie freier Text, nie eine Kopie aus dem Input."""


def temporal_expression_fn(turn_text: str, propositions: list[Proposition]) -> list[Proposition]:
    """
    Erfordert ANTHROPIC_API_KEY und das Paket 'anthropic'.
    """
    import anthropic

    client = anthropic.Anthropic()

    props_list = "\n".join(f"{i + 1}. {p.proposition_text}" for i, p in enumerate(propositions))
    user_message = f'Turn: "{turn_text}"\n\nPropositionen:\n{props_list}'

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0,
        system=_SYSTEM_PROMPT,
        tools=[
            {
                "name": "extract_temporal_expressions",
                "description": "Gib den raw_temporal_expression für jede Proposition zurück, in derselben Reihenfolge. Leerer String, falls keiner passt.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expressions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["expressions"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "extract_temporal_expressions"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next(block for block in message.content if block.type == "tool_use")
    expressions = tool_use_block.input["expressions"]

    if len(expressions) != len(propositions):
        raise ValueError(
            f"Anzahl Ausdrücke ({len(expressions)}) stimmt nicht mit "
            f"Anzahl Propositionen ({len(propositions)}) überein"
        )

    result = []
    for prop, expr in zip(propositions, expressions):
        result.append(
            Proposition(
                proposition_text=prop.proposition_text,
                assertion_status=prop.assertion_status,
                transition_type=prop.transition_type,
                decomposition_group_id=prop.decomposition_group_id,
                raw_temporal_expression=expr if expr else None,
            )
        )
    return result