"""Controles HTTP e sessões revogáveis; não contém credenciais de produção."""
import hashlib
import hmac
import math
import os
import secrets
import sqlite3
import time
from datetime import timedelta

from flask import abort, g, jsonify, redirect, request, session, url_for
from werkzeug.security import generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask.sessions import SecureCookieSessionInterface


class EnvironmentSessionInterface(SecureCookieSessionInterface):
    def get_signing_serializer(self, app):
        serializer = super().get_signing_serializer(app)
        if serializer is not None:
            serializer.salt = ('univet-session:' + app.config['UNIVET_ENV']).encode()
        return serializer

ADMIN_WRITES = {
    'criar_produto', 'editar_produto', 'alternar_produto', 'listar_categorias_page',
    'editar_categoria', 'alternar_categoria', 'listar_fornecedores_page',
    'editar_fornecedor', 'alternar_fornecedor', 'registrar_entrada_estoque',
    'ajustar_lote', 'estornar_movimentacao', 'editar_servico', 'excluir_servico',
    'editar_veterinario', 'excluir_veterinario', 'excluir_tutor', 'excluir_pet',
    'excluir_consulta',
}


def password_hash(password):
    if not 12 <= len(password) <= 128 or len(set(password)) < 6:
        raise ValueError('Use uma senha de 12 a 128 caracteres, com pelo menos 6 caracteres distintos.')
    return generate_password_hash(password)


def security_schema(conn):
    columns = {r[1] for r in conn.execute('PRAGMA table_info(usuarios)')}
    for name, definition in [('session_version', 'INTEGER NOT NULL DEFAULT 0'),
                             ('must_change_password', 'INTEGER NOT NULL DEFAULT 0'),
                             ('ultimo_acesso', 'TEXT')]:
        if name not in columns:
            conn.execute(f'ALTER TABLE usuarios ADD COLUMN {name} {definition}')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL,
            version INTEGER NOT NULL, expires_at REAL NOT NULL, last_seen REAL NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS rate_limits (
            key TEXT PRIMARY KEY, expires_at REAL NOT NULL, hits INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY, usuario_id INTEGER, evento TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT OR IGNORE INTO schema_migrations(version) VALUES ('20260919_security_v1');
    ''')


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def start_session(conn, user):
    session.clear()
    token = secrets.token_urlsafe(32)
    now = time.time()
    conn.execute('DELETE FROM auth_sessions WHERE expires_at < ?', (now,))
    conn.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,?)',
                 (_digest(token), user['id'], user['session_version'], now + 8 * 3600, now))
    conn.execute("UPDATE usuarios SET ultimo_acesso=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))
    conn.execute("INSERT INTO security_events(usuario_id,evento) VALUES (?, 'login')", (user['id'],))
    conn.commit()
    session.update(sid=token, usuario_id=user['id'], usuario_login=user['login'],
                   usuario_nome=user['nome'], usuario_perfil=user['perfil'])
    session.permanent = True


def end_session(conn):
    if session.get('sid'):
        conn.execute('DELETE FROM auth_sessions WHERE token_hash=?', (_digest(session['sid']),))
        conn.execute("INSERT INTO security_events(usuario_id,evento) VALUES (?, 'logout')", (session.get('usuario_id'),))
        conn.commit()
    session.clear()


def register_security(app, get_connection):
    mode = os.environ.get('UNIVET_ENV', 'development')
    if mode not in ('development', 'demo', 'production', 'test'):
        raise RuntimeError('UNIVET_ENV inválido.')
    production = mode == 'production'
    key = os.environ.get('SECRET_KEY')
    if production and (not key or len(key) < 32 or key == 'univet-chave-inicial-dev'):
        raise RuntimeError('Produção exige SECRET_KEY privada de pelo menos 32 caracteres.')
    app.config.update(SECRET_KEY=key or secrets.token_hex(32), DEBUG=False,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=production,
                      SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
                      MAX_CONTENT_LENGTH=256 * 1024, MAX_FORM_MEMORY_SIZE=256 * 1024,
                      RATE_LIMIT_ENABLED=production or os.environ.get('UNIVET_RATE_LIMIT_ENABLED', '1') != '0',
                      PRODUCTION=production)
    app.config.update(UNIVET_ENV=mode, SESSION_COOKIE_NAME='session' if mode in ('development', 'test') else 'univet_' + mode)
    app.session_interface = EnvironmentSessionInterface()
    if os.environ.get('UNIVET_TRUST_PROXY') == '1':
        # Somente atrás de UM proxy confiável, sem acesso direto ao backend.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    app.jinja_env.globals['csrf_token'] = csrf_token

    def limit(conn, category, identity, maximum, window):
        if not app.config['RATE_LIMIT_ENABLED']:
            return
        now = time.time()
        key = hmac.new(app.secret_key.encode(), f'{category}:{identity}:{int(now // window)}'.encode(), hashlib.sha256).hexdigest()
        conn.execute('DELETE FROM rate_limits WHERE expires_at < ?', (now,))
        row = conn.execute('''INSERT INTO rate_limits VALUES (?,?,1)
            ON CONFLICT(key) DO UPDATE SET hits=hits+1 RETURNING hits''', (key, now + window)).fetchone()
        conn.commit()
        if row[0] > maximum:
            abort(429)

    @app.before_request
    def protect():
        g.csp_nonce = secrets.token_urlsafe(24)
        g.current_user = None
        if production and not request.is_secure:
            # Do not echo untrusted Host in a redirect.
            abort(400, description='Utilize HTTPS.')
        if request.endpoint == 'static':
            return
        if request.endpoint is None:
            abort(404)
        if any(len(request.args.getlist(name)) != 1 or len(request.args[name]) > 512 for name in request.args):
            abort(400)
        conn = get_connection()
        try:
            if session.get('sid'):
                user = conn.execute('''SELECT u.*, s.last_seen, s.expires_at FROM usuarios u
                    JOIN auth_sessions s ON s.usuario_id=u.id AND s.version=u.session_version
                    WHERE s.token_hash=? AND u.ativo=1''', (_digest(session['sid']),)).fetchone()
                now = time.time()
                if user and user['perfil'] in ('admin', 'veterinaria') and user['expires_at'] > now and now-user['last_seen'] < 1800:
                    g.current_user = user
                    session.update(usuario_id=user['id'], usuario_perfil=user['perfil'], usuario_nome=user['nome'], usuario_login=user['login'])
                    if now-user['last_seen'] > 60:
                        conn.execute('UPDATE auth_sessions SET last_seen=? WHERE token_hash=?', (now, _digest(session['sid'])))
                        conn.commit()
                else:
                    session.clear()
            elif session.get('usuario_id'):
                session.clear()
            public = request.endpoint in ('login', 'health')
            if not public and g.current_user is None:
                if request.path.startswith('/api/'):
                    abort(401)
                return redirect(url_for('login'))
            if g.current_user is not None:
                if g.current_user['must_change_password'] and request.endpoint not in ('alterar_senha', 'logout'):
                    if request.path.startswith('/api/'):
                        abort(403)
                    return redirect(url_for('alterar_senha'))
                admin_action = request.endpoint in ADMIN_WRITES or request.path == '/estoque/lotes/entrada'
                if request.method != 'GET' and admin_action and g.current_user['perfil'] != 'admin':
                    abort(403)
                if request.path.startswith('/estoque/exportar/') and g.current_user['perfil'] != 'admin':
                    abort(403)
                if request.path.startswith('/api/'):
                    limit(conn, 'api', str(g.current_user['id']), 180, 60)
                if request.path.startswith('/estoque/exportar/'):
                    limit(conn, 'csv', str(g.current_user['id']), 10, 60)
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                values = request.form.getlist('csrf_token')
                supplied = values[0] if len(values) == 1 else request.headers.get('X-CSRFToken', '')
                expected = session.get('csrf_token', '')
                if not supplied or not expected or not hmac.compare_digest(supplied, expected):
                    abort(400, description='Formulário expirado ou inválido. Recarregue a página.')
                for name in request.form:
                    if len(request.form.getlist(name)) != 1 or len(request.form[name]) > (10000 if name in ('historico', 'diagnostico', 'tratamento', 'observacoes', 'descricao') else 512):
                        abort(400)
                numeric = ('quantidade','nova_quantidade','estoque_minimo','margem_lucro_percentual','valor_compra_unitario','valor','valor_unitario_praticado')
                for name in numeric:
                    value = request.form.get(name, '')
                    if value:
                        try:
                            number = float(value.replace(',', '.'))
                        except ValueError:
                            abort(400)
                        if not math.isfinite(number) or not 0 <= number <= 1e9:
                            abort(400)
                if request.endpoint == 'login':
                    limit(conn, 'login-ip', request.remote_addr or 'unknown', 20, 900)
                    limit(conn, 'login-account', request.form.get('login', '').strip().casefold(), 10, 900)
                if request.endpoint == 'alterar_senha':
                    limit(conn, 'password', str(g.current_user['id']), 5, 900)
        finally:
            conn.close()

    @app.after_request
    def headers(response):
        nonce = getattr(g, 'csp_nonce', '')
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' 'nonce-" + nonce + "'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        if production and request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        if response.status_code == 429:
            response.headers['Retry-After'] = '60'
        return response

    def error_response(error):
        code = getattr(error, 'code', None) or (400 if isinstance(error, sqlite3.IntegrityError) else 503 if isinstance(error, sqlite3.OperationalError) else 500)
        messages = {400:'Dados inválidos.',401:'Autenticação necessária.',403:'Acesso não permitido.',404:'Página não encontrada.',405:'Método não permitido.',413:'Formulário muito grande.',429:'Limite de tentativas. Aguarde.',500:'Não foi possível concluir a operação.',503:'Serviço temporariamente indisponível.'}
        return jsonify(error=messages.get(code, 'Não foi possível concluir a operação.')), code
    for code in (400,401,403,405,413,429,500):
        app.register_error_handler(code, error_response)
    app.register_error_handler(sqlite3.IntegrityError, error_response)
    app.register_error_handler(sqlite3.OperationalError, error_response)
