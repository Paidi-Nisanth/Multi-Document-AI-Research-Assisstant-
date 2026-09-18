"""Enable Row Level Security (RLS) on multi-tenant tables.

Revision ID: 002_enable_rls
Revises: 001_initial_schema
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '002_enable_rls'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    'documents',
    'chunks',
    'embeddings',
    'conversations',
    'messages',
    'flashcards',
    'query_cache'
]

def upgrade() -> None:
    for tbl in TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies WHERE tablename = '{tbl}' AND policyname = 'workspace_isolation_policy'
                ) THEN
                    CREATE POLICY workspace_isolation_policy ON {tbl}
                    USING (
                        NULLIF(current_setting('app.current_workspace_id', true), '') IS NULL
                        OR workspace_id::text = current_setting('app.current_workspace_id', true)
                    );
                END IF;
            END $$;
        """)

def downgrade() -> None:
    for tbl in TABLES:
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation_policy ON {tbl};")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")
