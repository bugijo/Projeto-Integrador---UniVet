"""Migração explícita Alembic: lê configuração, nunca imprime DATABASE_URL."""
import argparse
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from config import load_settings
from database import is_postgres


def migrate(database, environment, revision='head'):
    if not is_postgres(database):
        raise RuntimeError('Alembic deste comando exige PostgreSQL; SQLite legado usa init_db.py.')
    engine = create_engine(database.replace('postgresql://','postgresql+psycopg://',1),poolclass=NullPool,hide_parameters=True)
    try:
        with engine.begin() as conn:
            conn.execute(text('SELECT pg_advisory_xact_lock(734120, 2)'))
            tables = set(conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
            if tables:
                if 'univet_environment' not in tables or 'alembic_version' not in tables:
                    raise RuntimeError('Banco legado sem controle de migração: revisão explícita necessária.')
                mode = conn.execute(text('SELECT environment FROM univet_environment WHERE id=1')).scalar()
                if mode != environment:
                    raise RuntimeError('Ambiente do banco incompatível.')
            config = Config()
            config.set_main_option('script_location', str(Path(__file__).resolve().parent/'migrations'))
            config.attributes['connection'] = conn
            command.upgrade(config, revision)
            if not tables:
                conn.execute(text('INSERT INTO univet_environment VALUES (1,:environment)'),{'environment':environment})
    finally:
        engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Schema PostgreSQL sem seeds e sem credenciais em argumentos.')
    parser.add_argument('--revision',default='head')
    args=parser.parse_args()
    try:
        settings=load_settings()
        migrate(settings.database,settings.environment,args.revision)
    except Exception:
        parser.exit(1,'Migração recusada. Confira ambiente, schema, acesso e configuração em canal privado.\n')
    print('Migração concluída; nenhum dado demo inserido.')
