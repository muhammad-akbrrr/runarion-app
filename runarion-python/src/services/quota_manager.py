import os
from psycopg2 import pool
from models.request import CallerInfo

class QuotaManager:
    def __init__(self):
        self.connection_pool = self._get_db_connection()

    def _get_db_connection(self):
        return pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )

    def check_quota(self, caller: CallerInfo) -> int:
        """
        Fetch current quota for a workspace.
        """
        try:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT is_active, quota FROM workspaces WHERE id = %s",
                        (caller.workspace_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise ValueError("Workspace not found")

                    is_active, quota = row
                    if not is_active:
                        raise ValueError("Workspace is inactive")
                    if quota is None or quota <= 0:
                        raise ValueError("No quota remaining")

                    return quota
            finally:
                self.connection_pool.putconn(conn)
        except Exception as e:
            raise ValueError(f"Quota fetch failed: {str(e)}")

    def update_quota(self, caller: CallerInfo, expected_quota: int, quota_generation_count: int = 1) -> None:
        """
        Atomically decrements the quota using optimistic locking.
        Fails if the current quota is not equal to expected_quota.
        """
        try:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    new_quota = expected_quota - quota_generation_count
                    if new_quota < 0:
                        raise ValueError("Insufficient quota")

                    # Optimistic update using WHERE quota = expected_quota
                    cursor.execute(
                        """
                        UPDATE workspaces
                        SET quota = %s, updated_at = NOW()
                        WHERE id = %s AND quota = %s
                        """,
                        (new_quota, caller.workspace_id, expected_quota)
                    )

                    if cursor.rowcount == 0:
                        raise ValueError("Quota update failed due to concurrent modification")

                    conn.commit()
            finally:
                self.connection_pool.putconn(conn)
        except Exception as e:
            raise RuntimeError(f"Failed to update quota: {str(e)}")
