import calendar
import os
from contextlib import contextmanager
from datetime import datetime

from psycopg2 import pool
from src.models.request import CallerInfo
from ulid import ULID


DEFAULT_MONTHLY_TOKEN_QUOTA = 25_000_000


class QuotaManager:
    def __init__(self):
        self.connection_pool = self._get_db_connection()

    def _get_db_connection(self):
        return pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    @contextmanager
    def get_connection(self):
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    def _require_workspace(self, caller: CallerInfo) -> str:
        workspace_id = (caller.workspace_id or "").strip()
        if not workspace_id or workspace_id == "system":
            raise ValueError("Workspace usage context is required")
        return workspace_id

    def _add_months(self, dt: datetime, months: int) -> datetime:
        month_index = (dt.month - 1) + months
        year = dt.year + month_index // 12
        month = (month_index % 12) + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    def _resolve_period_bounds(self, anchor: datetime, reference: datetime) -> tuple[datetime, datetime]:
        period_start = anchor
        period_end = self._add_months(anchor, 1)

        while reference >= period_end:
            period_start = period_end
            period_end = self._add_months(period_start, 1)

        return period_start, period_end

    def reserve_tokens(
        self,
        caller: CallerInfo,
        estimated_tokens: int,
        quota_mode: str = "strict",
        workflow_id: str | None = None,
    ) -> dict:
        workspace_id = self._require_workspace(caller)
        estimated_tokens = max(1, int(estimated_tokens))

        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, is_active, COALESCE(monthly_token_quota, %s), COALESCE(billing_cycle_anchor_at, created_at)
                        FROM workspaces
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (DEFAULT_MONTHLY_TOKEN_QUOTA, workspace_id),
                    )
                    workspace_row = cursor.fetchone()

                    if not workspace_row:
                        raise ValueError("Workspace not found")

                    _, is_active, token_quota, anchor_at = workspace_row
                    if not is_active:
                        raise ValueError("Workspace is inactive")

                    now = datetime.utcnow()
                    period_start_at, period_end_at = self._resolve_period_bounds(anchor_at, now)

                    cursor.execute(
                        """
                        INSERT INTO workspace_usage_periods (
                            id,
                            workspace_id,
                            period_start_at,
                            period_end_at,
                            token_quota,
                            tokens_reserved,
                            tokens_consumed,
                            created_at,
                            updated_at
                        ) VALUES (%s, %s, %s, %s, %s, 0, 0, NOW(), NOW())
                        ON CONFLICT (workspace_id, period_start_at) DO NOTHING
                        """,
                        (
                            str(ULID()),
                            workspace_id,
                            period_start_at,
                            period_end_at,
                            int(token_quota),
                        ),
                    )

                    cursor.execute(
                        """
                        SELECT id, token_quota, tokens_reserved, tokens_consumed
                        FROM workspace_usage_periods
                        WHERE workspace_id = %s AND period_start_at = %s
                        FOR UPDATE
                        """,
                        (workspace_id, period_start_at),
                    )
                    usage_row = cursor.fetchone()
                    if not usage_row:
                        raise ValueError("Workspace usage period could not be created")

                    usage_period_id, period_quota, tokens_reserved, tokens_consumed = usage_row
                    remaining = int(period_quota) - int(tokens_reserved) - int(tokens_consumed)
                    if quota_mode == "strict" and remaining < estimated_tokens:
                        raise ValueError("No quota remaining")

                    cursor.execute(
                        """
                        UPDATE workspace_usage_periods
                        SET tokens_reserved = tokens_reserved + %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (estimated_tokens, usage_period_id),
                    )
                    conn.commit()

                    return {
                        "workspace_usage_period_id": str(usage_period_id),
                        "workspace_id": workspace_id,
                        "reserved_tokens": estimated_tokens,
                        "quota_mode": quota_mode,
                        "workflow_id": workflow_id,
                        "token_quota": int(period_quota),
                        "period_start_at": period_start_at,
                        "period_end_at": period_end_at,
                    }
            except Exception:
                conn.rollback()
                raise

    def finalize_usage(self, reservation: dict | None, actual_total_tokens: int) -> None:
        if not reservation:
            return

        reserved_tokens = max(0, int(reservation.get("reserved_tokens", 0)))
        actual_total_tokens = max(0, int(actual_total_tokens))
        usage_period_id = reservation.get("workspace_usage_period_id")

        if not usage_period_id:
            return

        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE workspace_usage_periods
                        SET tokens_reserved = GREATEST(tokens_reserved - %s, 0),
                            tokens_consumed = tokens_consumed + %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (reserved_tokens, actual_total_tokens, usage_period_id),
                    )
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
