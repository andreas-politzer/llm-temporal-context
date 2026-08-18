"""
Proposition — die atomare Einheit des Temporal Context Layer.

Empirische Grundlage (Labortest 16.08.2026): ein Satz ist nicht die
richtige Einheit; eine einzelne behauptete Proposition ist es.
assertion_status kennt bewusst nur ASSERTED/NOT_ASSERTED — IMPLIED wurde
in keinem Test je gebraucht und deshalb nicht aufgenommen.

Update 17.08.2026 (Architecture Contract v0, Schritt 1/2; siehe
Decisions/2026-08-17 State-Relation - Storage-Query-Trennung und
Transition-Dominanz): zwei neue Felder.

- transition_type: ob die Proposition selbst einen Zustandsbruch
  gegenüber einem Vorzustand markiert (TRANSITION), Kontinuität betont
  (CONTINUATION) oder schlicht einen Zustand behauptet, ohne sich zu
  einem Vorzustand zu äußern (BARE, Default). Wird in Schritt 2
  (Assertion Check) gesetzt, gilt für die einzelne Proposition — die
  Bindung an eine konkrete andere Proposition (state_relation) entsteht
  erst in Schritt 7, siehe relation.py.

- decomposition_group_id: reine Provenienz. Entstehen zwei Propositionen
  durch Splitten EINER Assertion (z.B. "war lange zuverlässig, ist es
  aber nicht mehr" -> zwei Propositionen), tragen beide dieselbe ID.
  Das ist KEINE Relationsbehauptung — nur ein Hinweis für Schritt 5
  (Candidate Retrieval), diese Propositionen garantiert als Kandidaten
  füreinander zu berücksichtigen. Ob zwischen ihnen tatsächlich eine
  state_relation besteht, entscheidet weiterhin ausschließlich Schritt 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class AssertionStatus(str, Enum):
    ASSERTED = "ASSERTED"
    NOT_ASSERTED = "NOT_ASSERTED"


class TransitionType(str, Enum):
    """
    Architecture Contract v0, Schritt 1/2. Eigenschaft EINER Proposition,
    keine Paar-Relation (die entsteht erst in Schritt 7 als state_relation,
    siehe relation.py). BARE ist der Default für eine schlichte
    Zustandsbehauptung ohne Bezug auf einen Vorzustand.

    CONTINUATION ist bislang totes Feld — wie DISJOINT vor dem 17.08.
    definiert, aber in keiner Regel (resolve_state_relation) und keinem
    Test tatsächlich verwendet oder gebraucht. Nicht entfernt, weil noch
    nicht geprüft, ob es strukturell unerreichbar ist (wie DISJOINT) oder
    schlicht noch nie gebraucht wurde, weil kein Testfall es ausgelöst
    hat. Offener Punkt, keine Lösung hier vorweggenommen.
    """

    BARE = "BARE"
    CONTINUATION = "CONTINUATION"
    TRANSITION = "TRANSITION"


@dataclass(frozen=True)
class SemanticSignature:
    """
    Flache, bewusst nicht-finale semantische Verankerung (Architecture
    Contract v0 §2). Dient als Anker für Retrieval, keine Ontologie.
    """

    domain: Optional[str] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    role: Optional[str] = None
    value: Optional[str] = None


@dataclass(frozen=True)
class TemporalInterval:
    """
    Normalisiertes Zeitintervall. start/end None = offenes Ende
    ("andauernd" bzw. "kein bekannter Beginn"). start == end = Zeitpunkt.
    """

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def is_point(self) -> bool:
        return self.start is not None and self.start == self.end

    def is_fully_bounded(self) -> bool:
        return self.start is not None and self.end is not None


@dataclass
class Proposition:
    proposition_text: str
    assertion_status: AssertionStatus
    assertion_time: Optional[datetime] = None
    raw_temporal_expression: Optional[str] = None
    normalized_temporal_reference: Optional[TemporalInterval] = None
    semantic_signature: Optional[SemanticSignature] = None
    transition_type: TransitionType = TransitionType.BARE
    decomposition_group_id: Optional[str] = None
    turn_id: Optional[str] = None
    proposition_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __repr__(self) -> str:  # pragma: no cover - Lesbarkeit im Test-Log
        return (
            f"Proposition(id={self.proposition_id[:8]}, "
            f"text={self.proposition_text!r}, "
            f"status={self.assertion_status.value}, "
            f"transition={self.transition_type.value}, "
            f"group={self.decomposition_group_id}, "
            f"ref={self.normalized_temporal_reference})"
        )

@dataclass(frozen=True)
class ExtractedProposition:
    """
    Schritt-1-Output (Proposition Extraction) — bewusst schlanker als
    Proposition. Enthält NUR, was Schritt 1 laut Contract entscheiden
    darf: den Text und die Turn-Provenienz (decomposition_group_id).
    assertion_status, transition_type, raw_temporal_expression sind
    Aufgabe von Schritt 2/3 und werden hier NICHT geraten oder
    vorweggenommen — dafür gibt es bewusst kein Feld. Wird erst in
    Schritt 2 zu einer vollständigen Proposition angereichert.

    Siehe Temporal Continuity/Proposition-Extraction Contract v0.
    """

    proposition_text: str
    decomposition_group_id: str

@dataclass(frozen=True)
class Conversation:
    """Scope-Grenze für Retrieval, siehe Decision 2026-08-18."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class Turn:
    """
    Wird IMMER persistiert, unabhängig davon, ob daraus ASSERTED-
    Propositionen entstehen (Audit-Trail-Prinzip, Decision 2026-08-18).
    assertion_time ist hier verortet, nicht mehr primär auf Proposition -
    alle Propositionen eines Turns teilen denselben Wert.
    """

    conversation_id: str
    text: str
    assertion_time: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inserted_at: datetime = field(default_factory=datetime.now)