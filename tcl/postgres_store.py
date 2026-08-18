"""
PostgresStore — erfüllt StoreProtocol (siehe tcl/store_protocol.py),
echte persistente Implementierung gegen PostgreSQL, siehe schema.sql
und Decision 2026-08-18 (Persistenz-Architektur).

Verbindungsdaten kommen aus der Umgebungsvariable DATABASE_URL, Default
passt zum lokalen Docker-Container aus dem Setup-Befehl im Chat.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from .proposition import AssertionStatus, Proposition, TransitionType
from .relation import PairwiseRelation, SemanticCompatibility, StateRelation, TemporalRelation
from .temporal_engine import TemporalInterval

DEFAULT_DSN = "postgresql://postgres:devpassword@localhost:5432/temporal_context_layer"


class PostgresStore:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or os.environ.get("DATABASE_URL", DEFAULT_DSN)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def add_conversation(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO conversations DEFAULT VALUES RETURNING id"
            ).fetchone()
            return str(row["id"])

    def add_turn(self, conversation_id: str, text: str, assertion_time: datetime) -> str:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO turns (conversation_id, text, assertion_time)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (conversation_id, text, assertion_time),
            ).fetchone()
            return str(row["id"])

    def ingest_propositions(
        self,
        turn_id: str,
        propositions: list[Proposition],
        relations: list[PairwiseRelation],
    ) -> None:
        with self._connect() as conn:
            # ATOMAR: eine einzige Transaktion für alle Propositionen + Relationen
            with conn.transaction():
                # conversation_id über turn_id nachschlagen (Propositionen kennen
                # es nicht direkt, siehe Proposition-Dataclass)
                turn_row = conn.execute(
                    "SELECT conversation_id FROM turns WHERE id = %s", (turn_id,)
                ).fetchone()
                conversation_id = turn_row["conversation_id"]

                for p in propositions:
                    conn.execute(
                        """
                        INSERT INTO propositions (
                            id, turn_id, conversation_id, decomposition_group_id,
                            proposition_text, assertion_status, transition_type,
                            raw_temporal_expression, normalized_start, normalized_end
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            p.proposition_id,
                            turn_id,
                            conversation_id,
                            p.decomposition_group_id,
                            p.proposition_text,
                            p.assertion_status.value,
                            p.transition_type.value,
                            p.raw_temporal_expression,
                            p.normalized_temporal_reference.start if p.normalized_temporal_reference else None,
                            p.normalized_temporal_reference.end if p.normalized_temporal_reference else None,
                        ),
                    )

                for r in relations:
                    conn.execute(
                        """
                        INSERT INTO pairwise_relations (
                            proposition_a_id, proposition_b_id,
                            temporal_relation, content_relation, state_relation
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            r.proposition_a_id,
                            r.proposition_b_id,
                            r.temporal_relation.value,
                            r.content_relation.value,
                            r.state_relation.value,
                        ),
                    )

    def get_candidates(self, conversation_id: str, new_proposition: Proposition) -> list[Proposition]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM propositions
                WHERE conversation_id = %s AND assertion_status = 'ASSERTED'
                """,
                (conversation_id,),
            ).fetchall()
            return [self._row_to_proposition(row) for row in rows]

    def get_by_id(self, proposition_id: str) -> Optional[Proposition]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM propositions WHERE id = %s", (proposition_id,)
            ).fetchone()
            return self._row_to_proposition(row) if row else None

    def get_relation_between(self, id_a: str, id_b: str) -> Optional[PairwiseRelation]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM pairwise_relations
                WHERE (proposition_a_id = %s AND proposition_b_id = %s)
                   OR (proposition_a_id = %s AND proposition_b_id = %s)
                """,
                (id_a, id_b, id_b, id_a),
            ).fetchone()
            if row is None:
                return None
            return PairwiseRelation(
                proposition_a_id=str(row["proposition_a_id"]),
                proposition_b_id=str(row["proposition_b_id"]),
                temporal_relation=TemporalRelation(row["temporal_relation"]),
                content_relation=SemanticCompatibility(row["content_relation"]),
                state_relation=StateRelation(row["state_relation"]),
            )

    @staticmethod
    def _row_to_proposition(row: dict) -> Proposition:
        normalized = None
        if row["normalized_start"] is not None or row["normalized_end"] is not None:
            normalized = TemporalInterval(start=row["normalized_start"], end=row["normalized_end"])
        return Proposition(
            proposition_text=row["proposition_text"],
            assertion_status=AssertionStatus(row["assertion_status"]),
            transition_type=TransitionType(row["transition_type"]),
            raw_temporal_expression=row["raw_temporal_expression"],
            normalized_temporal_reference=normalized,
            decomposition_group_id=str(row["decomposition_group_id"]) if row["decomposition_group_id"] else None,
            proposition_id=str(row["id"]),
        )

    def __len__(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM propositions").fetchone()
            return row["n"]