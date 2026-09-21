"""Configuração explícita. Nunca selecionar o banco de outro ambiente como fallback."""
from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Settings:
    environment: str
    database: Path


def sqlite_path(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'sqlite' or parsed.netloc or parsed.query or parsed.fragment:
        raise RuntimeError('URL não suportada: use sqlite:////caminho/absoluto. PostgreSQL ainda requer migração da aplicação.')
    path = unquote(parsed.path)
    if not path.startswith('//') or path in ('//', '//:memory:'):
        raise RuntimeError('O banco configurado deve ter caminho absoluto e persistente.')
    return Path(path[1:]).resolve()


def load_settings(environ=None):
    env = os.environ if environ is None else environ
    mode = env.get('UNIVET_ENV', 'development')
    if mode not in ('development', 'demo', 'production', 'test'):
        raise RuntimeError('UNIVET_ENV inválido.')
    if mode in ('demo', 'production'):
        variable = 'DEMO_DATABASE_URL' if mode == 'demo' else 'DATABASE_URL'
        if not env.get(variable):
            raise RuntimeError(f'{variable} é obrigatória; não existe fallback entre ambientes.')
        database = sqlite_path(env[variable])
        if env.get('UNIVET_DATABASE'):
            raise RuntimeError('UNIVET_DATABASE é permitida apenas em desenvolvimento/testes.')
        if env.get('DEMO_DATABASE_URL') and env.get('DATABASE_URL'):
            demo = sqlite_path(env['DEMO_DATABASE_URL'])
            production = sqlite_path(env['DATABASE_URL'])
            if demo == production or (demo.exists() and production.exists() and demo.samefile(production)):
                raise RuntimeError('DEMO e produção não podem compartilhar o banco.')
        if mode == 'production':
            if env.get('RENDER') or env.get('UNIVET_SQLITE_PERSISTENT') != '1':
                raise RuntimeError('SQLite de produção exige disco local persistente declarado; não é permitido no Render. Homologação ainda necessária.')
    else:
        database = Path(env.get('UNIVET_DATABASE', Path(__file__).resolve().parent / 'banco.db')).resolve()
    return Settings(mode, database)


def verify_database_environment(connection, mode, initialize=False):
    """Marca durável impede abrir uma cópia demo com configuração de produção."""
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='univet_environment'").fetchone()
    if exists:
        row = connection.execute('SELECT environment FROM univet_environment WHERE id=1').fetchone()
        if row is None or row[0] != mode:
            raise RuntimeError('Banco pertence a outro ambiente; acesso recusado.')
        return
    if mode in ('development', 'test'):
        return  # Compatibilidade com bancos locais antigos; não homologados.
    if not initialize:
        raise RuntimeError('Banco sem identificação de ambiente. Inicialize explicitamente um banco vazio.')
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone():
        raise RuntimeError('Banco existente sem identificação; exige migração revisada, nunca adoção automática.')
    connection.execute("CREATE TABLE univet_environment (id INTEGER PRIMARY KEY CHECK(id=1), environment TEXT NOT NULL CHECK(environment IN ('demo','production')))")
    connection.execute('INSERT INTO univet_environment VALUES (1,?)', (mode,))
    connection.commit()
