"""Configuração explícita. Nunca selecionar o banco de outro ambiente como fallback."""
from dataclasses import dataclass, field
from pathlib import Path
import os
from urllib.parse import unquote, urlsplit, parse_qs


POSTGRES_SCHEMES = frozenset({'postgres', 'postgresql'})


def is_postgres_scheme(scheme):
    return scheme in POSTGRES_SCHEMES or scheme.startswith(('postgres+', 'postgresql+'))


@dataclass(frozen=True)
class Settings:
    environment: str
    database: Path | str = field(repr=False)


def database_target(url):
    if not isinstance(url, str):
        raise RuntimeError('URL não suportada (valor ausente); use PostgreSQL ou SQLite absoluto local.')
    url = url.strip()
    for _ in range(4):
        previous = url
        if url.startswith('DATABASE_URL='):
            url = url.split('=', 1)[1].strip()
        if url.startswith('psql '):
            url = url[5:].strip()
        if len(url) >= 2 and url[0] == url[-1] and url[0] in ('"', "'"):
            url = url[1:-1].strip()
        if url == previous:
            break
    parsed = urlsplit(url)
    if is_postgres_scheme(parsed.scheme):
        if not parsed.hostname or not parsed.username or not parsed.path.strip('/'):
            raise RuntimeError('DATABASE_URL PostgreSQL incompleta.')
        query = parse_qs(parsed.query)
        allowed = {'sslmode','sslrootcert','channel_binding'}
        if set(query) - allowed or any(len(v)!=1 for v in query.values()):
            raise RuntimeError('Parâmetros PostgreSQL não permitidos.')
        if parsed.hostname not in ('127.0.0.1','localhost','::1') and query.get('sslmode') != ['verify-full']:
            raise RuntimeError('PostgreSQL remoto exige sslmode=verify-full e certificado confiável.')
        # Neon e outros provedores podem fornecer URL com o driver SQLAlchemy
        # no esquema (postgresql+psycopg://). O adaptador DB-API usa psycopg
        # diretamente, então normalizamos somente o esquema, preservando
        # host, credenciais codificadas, banco e parâmetros aprovados.
        return parsed._replace(scheme='postgresql').geturl()
    if parsed.scheme == 'sqlite':
        return sqlite_path(url)
    scheme = parsed.scheme or '<vazio>'
    raise RuntimeError(f'URL não suportada (esquema: {scheme}); use PostgreSQL ou SQLite absoluto local.')


def same_database(first, second):
    if isinstance(first, Path) and isinstance(second, Path):
        return first == second or (first.exists() and second.exists() and first.samefile(second))
    if isinstance(first,str) and isinstance(second,str):
        a,b = urlsplit(first),urlsplit(second)
        return (a.hostname.replace('-pooler',''), a.port or 5432, unquote(a.path)) == (b.hostname.replace('-pooler',''), b.port or 5432, unquote(b.path))
    return False


def sqlite_path(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'sqlite' or parsed.netloc or parsed.query or parsed.fragment:
        raise RuntimeError('URL não suportada. Use PostgreSQL ou SQLite absoluto local.')
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
        database = database_target(env[variable])
        if env.get('UNIVET_DATABASE'):
            raise RuntimeError('UNIVET_DATABASE é permitida apenas em desenvolvimento/testes.')
        if env.get('DEMO_DATABASE_URL') and env.get('DATABASE_URL'):
            demo = database_target(env['DEMO_DATABASE_URL'])
            production = database_target(env['DATABASE_URL'])
            if same_database(demo,production):
                raise RuntimeError('DEMO e produção não podem compartilhar o banco.')
        if mode == 'production' and isinstance(database,Path):
            if env.get('RENDER') or env.get('UNIVET_SQLITE_PERSISTENT') != '1':
                raise RuntimeError('SQLite de produção exige disco local persistente declarado; não é permitido no Render. Homologação ainda necessária.')
    else:
        if env.get('DATABASE_URL') and env.get('UNIVET_DATABASE'):
            raise RuntimeError('Defina somente DATABASE_URL ou UNIVET_DATABASE no ambiente local.')
        database = database_target(env['DATABASE_URL']) if env.get('DATABASE_URL') else Path(env.get('UNIVET_DATABASE', Path(__file__).resolve().parent / 'banco.db')).resolve()
    return Settings(mode, database)


def verify_database_environment(connection, mode, initialize=False):
    """Marca durável impede abrir uma cópia demo com configuração de produção."""
    if getattr(connection,'dialect',None) == 'postgresql':
        row = connection.execute('SELECT environment FROM univet_environment WHERE id=1').fetchone()
        if row is None or row[0] != mode:
            raise RuntimeError('Banco pertence a outro ambiente; acesso recusado.')
        return
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
