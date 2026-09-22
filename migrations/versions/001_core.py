"""Schema PostgreSQL explícito, sem dados fictícios."""
from pathlib import Path
from alembic import op

revision='001_core'
down_revision=None


def upgrade():
    sql = Path(__file__).with_suffix('.sql').read_text(encoding='utf-8')
    bind = op.get_bind()
    raw = getattr(bind.connection, 'driver_connection', bind.connection)
    raw.execute(sql, prepare=False)


def downgrade():
    raise RuntimeError('Baseline não pode ser apagada por downgrade. Preserve dados e restaure em outro banco.')
