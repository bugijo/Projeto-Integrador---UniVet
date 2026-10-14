"""Contrato do template WSGI para hospedagem acadêmica no PythonAnywhere."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PythonAnywhereWsgiTests(unittest.TestCase):
    def test_wsgi_selects_persistent_demo_sqlite_without_initializing_on_import(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="univet-pythonanywhere-") as directory:
            env = {
                key: value for key, value in os.environ.items()
                if key not in {
                    "DATABASE_URL", "DEMO_DATABASE_URL", "UNIVET_DATABASE",
                    "UNIVET_ENV", "RENDER", "UNIVET_SQLITE_PERSISTENT",
                }
            }
            env.update(
                PYTHONPATH=str(project),
                UNIVET_PROJECT_DIR=directory,
                SECRET_KEY="academic-demo-test-secret-32-characters",
            )
            script = """
import json
import os
from pathlib import Path
import runpy

module = runpy.run_path('pythonanywhere_wsgi.py')
application = module['application']
print(json.dumps({
    'environment': os.environ['UNIVET_ENV'],
    'database_url': os.environ['DEMO_DATABASE_URL'],
    'database_exists': Path(os.environ['DEMO_DATABASE_URL'].removeprefix('sqlite:///')).exists(),
    'application_name': application.name,
}))
"""
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(payload["environment"], "demo")
            self.assertEqual(
                payload["database_url"],
                f"sqlite:///{Path(directory) / 'data' / 'univet-demo.db'}",
            )
            self.assertFalse(payload["database_exists"])
            self.assertEqual(payload["application_name"], "app")


if __name__ == "__main__":
    unittest.main()
