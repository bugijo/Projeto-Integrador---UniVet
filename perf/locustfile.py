"""Somente pelo runner local; sessões reais e CSRF mantido habilitado."""
from datetime import date
from html.parser import HTMLParser
import os
from itertools import count
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from locust import HttpUser, between, events, task
from locust.exception import StopUser


_BENCH_ACCOUNT_COUNTER = count()


class CSRFParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "csrf_token":
            self.token = attrs.get("value")


def csrf_token(html):
    parser = CSRFParser()
    parser.feed(html)
    return parser.token


@events.init.add_listener
def local_only(environment, **kwargs):
    host = urlparse(environment.host or "")
    root = Path(os.environ.get("UNIVET_BENCH_ROOT", "/missing"))
    if (host.scheme != "http" or host.hostname != "127.0.0.1"
            or not (root / "isolated-benchmark").is_file()):
        raise RuntimeError("Use perf/run.py: carga permitida somente no servidor descartável local.")


class ClinicaUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def get_page(self, path, name=None):
        with self.client.get(path, name=name or path, allow_redirects=False,
                             timeout=10, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}; esperado 200 autenticado")
                return None
            return response.text

    def token_for(self, path):
        html = self.get_page(path)
        token = csrf_token(html or "")
        if not token:
            # Falha explícita: um HTML 200 sem formulário válido não é sucesso funcional.
            events.request.fire(request_type="CHECK", name=f"CSRF {path}",
                                response_time=0, response_length=0,
                                exception=ValueError("csrf_token ausente"))
        return token

    def on_start(self):
        token = self.token_for("/login")
        if not token:
            raise StopUser()
        account_index = next(_BENCH_ACCOUNT_COUNTER) % 50
        client_headers = {"X-Forwarded-For": f"198.51.100.{account_index + 1}"}
        with self.client.post("/login", data={
            "login": f"bench_qa_{account_index:02d}",
            "senha": os.environ.get("UNIVET_BENCH_PASSWORD", "QA-Benchmark-Local-2026!"),
            "csrf_token": token,
        }, headers=client_headers, allow_redirects=False, timeout=10, catch_response=True) as response:
            if (response.status_code not in (302, 303)
                    or urlparse(response.headers.get("Location", "")).path != "/pagina-inicial"):
                response.failure("Login recusado ou redirecionamento inesperado")
                raise StopUser()
        if self.get_page("/pagina-inicial") is None:
            raise StopUser()
        # Cobertura mínima inclusive no perfil curto de um usuário.
        self.navegar()
        self.pequena_escrita()

    @task(9)
    def navegar(self):
        for path in ("/pagina-inicial", "/tutores", "/pets", "/consultas",
                     "/estoque", "/estoque/produtos", "/estoque/relatorios"):
            self.get_page(path)
        self.get_page(f"/consultas/dia/{date.today().isoformat()}", "/consultas/dia/[data]")

    @task(1)
    def pequena_escrita(self):
        path = "/estoque/categorias"
        token = self.token_for(path)
        if not token:
            return
        name = f"Carga ficticia {uuid4().hex}"
        with self.client.post(path, data={"nome": name, "descricao": "Benchmark local descartavel",
                                         "csrf_token": token}, allow_redirects=False,
                              timeout=10, catch_response=True) as response:
            if (response.status_code not in (302, 303)
                    or urlparse(response.headers.get("Location", "")).path != path):
                response.failure("Escrita não redirecionou para categorias")
                return
        with self.client.get(path, params={"busca": name}, name="/estoque/categorias?busca=[criada]",
                             allow_redirects=False, timeout=10, catch_response=True) as response:
            if response.status_code != 200 or name not in response.text:
                response.failure("Categoria criada não encontrada: falha funcional")
