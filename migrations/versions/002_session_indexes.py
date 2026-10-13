"""Índices de manutenção sem modificar registros; rollback reversível."""
from alembic import op

revision='002_session_indexes'
down_revision='001_core'


def upgrade():
    op.create_index('idx_auth_user','auth_sessions',['usuario_id'])
    op.create_index('idx_auth_expiry','auth_sessions',['expires_at'])
    op.create_index('idx_rate_expiry','rate_limits',['expires_at'])


def downgrade():
    op.drop_index('idx_rate_expiry','rate_limits')
    op.drop_index('idx_auth_expiry','auth_sessions')
    op.drop_index('idx_auth_user','auth_sessions')
