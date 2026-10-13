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
            kwargs['data'] = data
        return super().open(*args, **kwargs)
