"""
content_relation_fn — Schritt 7a des Architecture Contract v0, erste
echte LLM-Implementierung.

CONTRACT (siehe [[Temporal Continuity/Content-Relation Mini-Corpus v0]]):
Input: zwei Propositionen (proposition_text als Kontext, keine externe
Weltkenntnis, kein assertion_time). Output: exakt COMPATIBLE |
INCOMPATIBLE | UNDETERMINED.

Invarianten:
  1. Keine temporale Schlussfolgerung — Zeitmarker nur zur Slot-
     Identifikation, nie als Kompatibilitätsargument. Empirisch
     verletzt beobachtet (Gemini, Fall 12, Runde 2) — deshalb als
     eigener, benannter Regressionstest gesichert, nicht nur als
     Prompt-Hoffnung.
  2. Kein Zugriff auf assertion_time (Funktion bekommt es nicht mal
     übergeben).
  3. Keine externe Weltkenntnis über den Propositionstext hinaus.

Bewusst NICHT Teil dieser ersten Implementierung: Multi-Call-Voting,
zusätzliche Temporal-Logik, Confidence-System, automatische Reparatur.
"""

from __future__ import annotations

import json

from .proposition import Proposition
from .relation import SemanticCompatibility

_SYSTEM_PROMPT = """Du bewertest, ob zwei Aussagen (Propositionen) inhaltlich zueinander COMPATIBLE, INCOMPATIBLE oder UNDETERMINED sind.

Gehe GENAU in dieser Reihenfolge vor. Sobald ein Schritt zutrifft, wende ihn an und stoppe — prüfe die folgenden Schritte nicht mehr.

SCHRITT 1 — Explizite Zwecktrennung (hat Vorrang vor allem Weiteren):
Nennen A und B jeweils EXPLIZIT einen unterschiedlichen Zweck/Verwendung für dasselbe Objekt (z. B. "X für Zweck A" / "X für Zweck B")? Wenn ja -> COMPATIBLE. Das gilt auch sprachübergreifend. Fasse die genannten Zwecke dabei NICHT zu einem gemeinsamen Oberbegriff zusammen (z. B. "Projektmanagement" und "Bug-Tracking" bleiben getrennt, auch wenn beides zu "Software-Tools" gehört).
Nennt NUR EINE Seite einen Zweck, die andere nur den nackten Namen ohne Zweck? Dann greift dieser Schritt NICHT — weiter zu Schritt 2.

SCHRITT 2 — Gemeinsamer Slot erkennbar?
Ein "Slot" ist eine Eigenschaft/ein Wertebereich, den beide Aussagen für dieselbe Entität beanspruchen (z. B. "primäres Tool", "Wohnort", "Familienstand").
a) Slot ist auf MINDESTENS EINER Seite explizit benannt oder durch allgemein bekanntes Kategoriewissen sofort erkennbar (z. B.: zwei genannte Städte sind offensichtlich beide "Wohnort"-Kandidaten; zwei bekannte Software-Tools derselben Art sind offensichtlich beide "Tool"-Kandidaten) -> Slot gilt als identifiziert, weiter zu Schritt 3.
b) Slot ist auf KEINER Seite explizit benannt UND nicht durch Kategoriewissen sofort erkennbar, sondern nur durch schwachen, beidseitig nur indirekten Kontext-Hinweis vermutbar -> UNDETERMINED.
c) Kein erkennbarer gemeinsamer Slot -> COMPATIBLE (Default).

Wichtig für 2a: Nutze NUR Kategoriewissen, das sofort und ohne jede Spekulation feststeht. Erfinde NIEMALS einen zusätzlichen, im Text nicht genannten Zweck oder eine Eigenschaft, nur um Unsicherheit zu konstruieren oder aufzulösen.

SCHRITT 3 — Werte vergleichen (nur wenn Schritt 2a zutraf):
Sind die Werte für den identifizierten Slot in A und B unterschiedlich und schließen sich gegenseitig aus (z. B. zwei verschiedene Tools als "das eine genutzte Tool", zwei verschiedene Preise für "den einen Preis")? -> INCOMPATIBLE.
Ist der Wert gleich oder eine widerspruchsfreie Präzisierung? -> COMPATIBLE.
WICHTIG bei Negation: Verneint eine Aussage EINEN bestimmten Wert (z. B. "kein X mehr", "nicht mehr X"), schließt das NUR diesen einen Wert aus, nicht automatisch jeden anderen möglichen Wert. Eine Negation von X ist COMPATIBLE mit einer Aussage über einen anderen Wert Y (Y ungleich X) — es sei denn, die andere Aussage behauptet zusätzlich explizit, dass X ebenfalls gilt.
TEMPORALE MARKER — gilt für ALLE Schritte oben:
Enthält A oder B eine zeitliche Formulierung ("früher", "jetzt", "seit X", "nicht mehr")? Nutze das AUSSCHLIESSLICH in Schritt 1/2 zur Identifikation, ob A und B über denselben Slot sprechen. Diese Formulierung darf NIEMALS selbst der Grund für COMPATIBLE oder INCOMPATIBLE sein. Insbesondere: "früher X, jetzt Y" ist bei gleichem Slot INCOMPATIBLE (Schritt 3), nicht automatisch COMPATIBLE nur weil die Zeitpunkte verschieden sind — ob es sich um eine Ablösung oder einen echten Widerspruch handelt, wird an anderer Stelle im System entschieden, nicht hier.

Antworte AUSSCHLIESSLICH mit validem JSON, keine Erklärung außerhalb des JSON. Das "reasoning"-Feld darf NUR das Endergebnis in maximal 15 Wörtern nennen (z. B. "Schritt 3: gleicher Slot, ausschließende Werte") — zeige NIEMALS Zwischenschritte, Abwägungen oder Selbstkorrekturen ("eigentlich... nein...") im JSON:
{"classification": "COMPATIBLE" | "INCOMPATIBLE" | "UNDETERMINED", "reasoning": "kurzes Endergebnis, kein Gedankengang"}
"""


def content_relation_fn(a: Proposition, b: Proposition) -> SemanticCompatibility:
    """
    Signatur bleibt kompatibel zu pipeline.process_new_proposition().

    Nutzt Anthropics Tool-Use-Mechanismus, um die Antwort zu erzwingen
    (kein Freitext möglich, keine "Wait, let me reconsider"-artigen
    Ausbrüche aus dem JSON-Format) - reine Prompt-Instruktionen dafür
    reichten nicht (siehe Chat 17.08.: mehrfach gescheitert an
    Selbstkorrekturen mitten in der Antwort, unabhängig von der
    Formulierung der Instruktion).

    temperature=0, siehe Chat 17.08.

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
                "name": "classify_content_relation",
                "description": "Gib die Klassifikation gemäß der Schritt-für-Schritt-Prozedur zurück.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "classification": {
                            "type": "string",
                            "enum": ["COMPATIBLE", "INCOMPATIBLE", "UNDETERMINED"],
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Kurzes Endergebnis (max. 15 Wörter), kein Gedankengang.",
                        },
                    },
                    "required": ["classification", "reasoning"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "classify_content_relation"},
        messages=[{"role": "user", "content": f'A: "{a.proposition_text}"\nB: "{b.proposition_text}"'}],
    )

    tool_use_block = next(block for block in message.content if block.type == "tool_use")
    return SemanticCompatibility(tool_use_block.input["classification"])