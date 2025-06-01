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

    def fetch(self, caller: CallerInfo) -> int:
        """
        Checks if the workspace exists, is active, and has quota left.
        Returns the remaining quota if valid, otherwise raises ValueError.
        """
        try:
            with self.connection_pool.getconn() as conn:
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
        except Exception as e:
            raise ValueError(f"Quota fetch failed: {str(e)}")

    def update(self, caller: CallerInfo, quota_generation_count: int = 1) -> None:
        """
        Deducts quota_generation_count from the workspace's quota after validation.
        """
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT quota FROM workspaces WHERE id = %s FOR UPDATE",
                        (caller.workspace_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise ValueError("Workspace not found")

                    current_quota = row[0]
                    if current_quota is None or current_quota < quota_generation_count:
                        raise ValueError("Insufficient quota")

                    new_quota = current_quota - quota_generation_count
                    cursor.execute(
                        "UPDATE workspaces SET quota = %s, updated_at = NOW() WHERE id = %s",
                        (new_quota, caller.workspace_id)
                    )
                    conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to update quota: {str(e)}")
