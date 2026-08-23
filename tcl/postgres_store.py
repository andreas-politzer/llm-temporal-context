"""
PostgresStore — erfüllt StoreProtocol, echte persistente Implementierung
gegen PostgreSQL, siehe schema.sql und Decision 2026-08-18.
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

_PROPOSITION_SELECT = """
    SELECT p.*, t.assertion_time
    FROM propositions p
    JOIN turns t ON p.turn_id = t.id
"""


class PostgresStore:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or os.environ.get("DATABASE_URL", DEFAULT_DSN)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def add_conversation(self, workspace_id: Optional[str] = None) -> str:
        with self._connect() as conn:
            if workspace_id is None:
                row = conn.execute("SELECT id FROM workspaces ORDER BY created_at LIMIT 1").fetchone()
                if row is None:
                    row = conn.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()
                workspace_id = str(row["id"])
            row = conn.execute(
                "INSERT INTO conversations (workspace_id) VALUES (%s) RETURNING id",
                (workspace_id,),
            ).fetchone()
            return str(row["id"])

    def add_turn(self, conversation_id: str, text: str, assertion_time: Optional[datetime] = None) -> str:
        if assertion_time is None:
            assertion_time = datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO turns (conversation_id, text, assertion_time) VALUES (%s, %s, %s) RETURNING id",
                (conversation_id, text, assertion_time),
            ).fetchone()
            return str(row["id"])

    def get_turn_assertion_time(self, turn_id: str) -> datetime:
        with self._connect() as conn:
            row = conn.execute("SELECT assertion_time FROM turns WHERE id = %s", (turn_id,)).fetchone()
            if row is None:
                raise ValueError(f"turn_id {turn_id!r} existiert nicht in der Datenbank")
            return row["assertion_time"]

    def ingest_propositions(
        self, turn_id: str, propositions: list[Proposition], relations: list[PairwiseRelation]
    ) -> None:
        with self._connect() as conn:
            with conn.transaction():
                turn_row = conn.execute("SELECT conversation_id FROM turns WHERE id = %s", (turn_id,)).fetchone()
                if turn_row is None:
                    raise ValueError(
                        f"turn_id {turn_id!r} existiert nicht in der Datenbank — "
                        f"möglicherweise eine veraltete ID aus einer früheren Session "
                        f"oder einem gelöschten/zurückgesetzten Datenbankstand."
                    )
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
                            p.proposition_id, turn_id, conversation_id, p.decomposition_group_id,
                            p.proposition_text, p.assertion_status.value, p.transition_type.value,
                            p.raw_temporal_expression,
                            p.normalized_temporal_reference.start if p.normalized_temporal_reference else None,
                            p.normalized_temporal_reference.end if p.normalized_temporal_reference else None,
                        ),
                    )
                for r in relations:
                    conn.execute(
                        """
                        INSERT INTO pairwise_relations
                            (proposition_a_id, proposition_b_id, temporal_relation, content_relation, state_relation)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (r.proposition_a_id, r.proposition_b_id, r.temporal_relation.value,
                         r.content_relation.value, r.state_relation.value),
                    )

    def get_candidates(self, conversation_id: str, new_proposition: Proposition) -> list[Proposition]:
        with self._connect() as conn:
            rows = conn.execute(
                _PROPOSITION_SELECT + " WHERE p.conversation_id = %s AND p.assertion_status = 'ASSERTED'",
                (conversation_id,),
            ).fetchall()
            return [self._row_to_proposition(row) for row in rows]

    def get_all_propositions(self, conversation_id: str) -> list[Proposition]:
        with self._connect() as conn:
            rows = conn.execute(
                _PROPOSITION_SELECT + " WHERE p.conversation_id = %s", (conversation_id,)
            ).fetchall()
            return [self._row_to_proposition(row) for row in rows]

    def get_by_id(self, proposition_id: str) -> Optional[Proposition]:
        with self._connect() as conn:
            row = conn.execute(_PROPOSITION_SELECT + " WHERE p.id = %s", (proposition_id,)).fetchone()
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
            assertion_time=row["assertion_time"],
            transition_type=TransitionType(row["transition_type"]),
            raw_temporal_expression=row["raw_temporal_expression"],
            normalized_temporal_reference=normalized,
            decomposition_group_id=str(row["decomposition_group_id"]) if row["decomposition_group_id"] else None,
            turn_id=str(row["turn_id"]) if row.get("turn_id") else None,
            proposition_id=str(row["id"]),
        )

    def search_turns(self, conversation_id: str, search_term: str) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT text, assertion_time FROM turns
                WHERE conversation_id = %s
                AND to_tsvector('simple', text) @@ to_tsquery('simple', %s)
                ORDER BY assertion_time
                """,
                (conversation_id, search_term),
            ).fetchall()
            return [{"turn_text": row["text"], "assertion_time": row["assertion_time"]} for row in rows]

    def get_propositions_for_turn(self, turn_id: str) -> list:
        with self._connect() as conn:
            rows = conn.execute(_PROPOSITION_SELECT + " WHERE p.turn_id = %s", (turn_id,)).fetchall()
            return [self._row_to_proposition(row) for row in rows]

    def search_temporal_memory(self, search_term: str, workspace_id: Optional[str] = None) -> list:
        with self._connect() as conn:
            if workspace_id is None:
                row = conn.execute("SELECT id FROM workspaces ORDER BY created_at LIMIT 1").fetchone()
                if row is None:
                    return []
                workspace_id = str(row["id"])

            rows = conn.execute(
                """
                SELECT p.proposition_text AS text, p.normalized_start AS time,
                       'EVENT' AS time_source, t.conversation_id AS conversation_id
                FROM propositions p
                JOIN turns t ON p.turn_id = t.id
                JOIN conversations c ON t.conversation_id = c.id
                WHERE c.workspace_id = %s AND p.normalized_start IS NOT NULL
                  AND to_tsvector('simple', p.proposition_text) @@ to_tsquery('simple', %s)

                UNION ALL

                SELECT t.text AS text, t.assertion_time AS time,
                       'MENTION' AS time_source, t.conversation_id AS conversation_id
                FROM turns t
                JOIN conversations c ON t.conversation_id = c.id
                WHERE c.workspace_id = %s
                  AND to_tsvector('simple', t.text) @@ to_tsquery('simple', %s)
                  AND t.id NOT IN (
                      SELECT p2.turn_id FROM propositions p2 WHERE p2.normalized_start IS NOT NULL
                  )
                ORDER BY time
                """,
                (workspace_id, search_term, workspace_id, search_term),
            ).fetchall()
            return [
                {
                    "text": r["text"],
                    "time": r["time"],
                    "time_source": r["time_source"] if r["time"] is not None else "UNKNOWN",
                    "conversation_id": str(r["conversation_id"]),
                }
                for r in rows
            ]

    def get_recent_events(self, limit: int = 5, workspace_id: Optional[str] = None) -> list:
        with self._connect() as conn:
            if workspace_id is None:
                row = conn.execute("SELECT id FROM workspaces ORDER BY created_at LIMIT 1").fetchone()
                if row is None:
                    return []
                workspace_id = str(row["id"])

            rows = conn.execute(
                """
                SELECT p.proposition_text AS text, p.normalized_start AS time,
                       'EVENT' AS time_source
                FROM propositions p
                JOIN turns t ON p.turn_id = t.id
                JOIN conversations c ON t.conversation_id = c.id
                WHERE c.workspace_id = %s AND p.normalized_start IS NOT NULL

                UNION ALL

                SELECT t.text AS text, t.assertion_time AS time,
                       'MENTION' AS time_source
                FROM turns t
                JOIN conversations c ON t.conversation_id = c.id
                WHERE c.workspace_id = %s
                  AND t.id NOT IN (
                      SELECT p2.turn_id FROM propositions p2 WHERE p2.normalized_start IS NOT NULL
                  )

                ORDER BY time DESC
                LIMIT %s
                """,
                (workspace_id, workspace_id, limit),
            ).fetchall()
            return [
                {"text": r["text"], "time": r["time"], "time_source": r["time_source"]}
                for r in rows
            ]

    def __len__(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM propositions").fetchone()["n"]