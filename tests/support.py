"""Cliente de formulários: envia CSRF real, sem desabilitar controles."""
from flask.testing import FlaskClient


class FormClient(FlaskClient):
    def open(self, *args, **kwargs):
        if kwargs.get('method', 'GET').upper() == 'POST':
            with self.session_transaction() as state:
                token = state.get('csrf_token')
            if not token:
                super().open('/login', follow_redirects=True)
                with self.session_transaction() as state:
                    token = state.get('csrf_token')
            data = dict(kwargs.get('data') or {})
            data.setdefault('csrf_token', token)
            path = str(args[0]) if args else str(kwargs.get('path', ''))
            scope = 'saida' if path.split('?')[0] == '/estoque/saidas' else None
            if path.startswith('/consultas/') and path.endswith('/produtos'):
                scope = 'consulta:' + path.split('/')[2]
            if scope and 'operacao_token' not in data:
                from app import stock_operation_token
                with self.session_transaction() as state:
                    user = state.get('usuario_id')
                from flask import session
                with self.application.test_request_context():
                    session['usuario_id'] = user
                    data['operacao_token'] = stock_operation_token(scope)
            kwargs['data'] = data
        return super().open(*args, **kwargs)
