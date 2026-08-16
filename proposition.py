"""
Proposition — die atomare Einheit des Temporal Context Layer.

Empirische Grundlage (Labortest 16.08.2026): ein Satz ist nicht die
richtige Einheit; eine einzelne behauptete Proposition ist es.
assertion_status kennt bewusst nur ASSERTED/NOT_ASSERTED — IMPLIED wurde
in keinem Test je gebraucht und deshalb nicht aufgenommen.
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
    proposition_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __repr__(self) -> str:  # pragma: no cover - Lesbarkeit im Test-Log
        return (
            f"Proposition(id={self.proposition_id[:8]}, "
            f"text={self.proposition_text!r}, "
            f"status={self.assertion_status.value}, "
            f"ref={self.normalized_temporal_reference})"
        )
