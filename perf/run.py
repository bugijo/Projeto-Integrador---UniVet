#!/usr/bin/env python3
"""Benchmark local opt-in; dependências instaladas somente no cache isolado uv."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
PERF = REPO / "perf"
PROFILES = (1, 5, 10, 20, 30, 50)


def source_files():
    files = list(REPO.glob("*.py")) + [REPO / "requirements.txt"]
    for folder in ("estoque", "templates", "static", "perf"):
        files.extend(p for p in (REPO / folder).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and "results" not in p.parts)
    return sorted(files)


def fingerprint():
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files()}


def stop(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def spawn(command, env, root, log):
    return subprocess.Popen(command, cwd=root / "source", env=env,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


def tree_usage(pid, previous, now):
    import psutil
    cpu = rss = 0
    current = {}
    try:
        parent = psutil.Process(pid)
        processes = [parent] + parent.children(recursive=True)
    except psutil.NoSuchProcess:
        return 0, 0, current
    for process in processes:
        try:
            stamp = (process.pid, process.create_time())
            times = process.cpu_times()
            total = times.user + times.system
            rss += process.memory_info().rss
            if stamp in previous:
                old, then = previous[stamp]
                cpu += max(0, total - old) / (now - then) * 100
            current[stamp] = (total, now)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return cpu, rss / 1024**2, current


def counts(database):
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        return {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("usuarios", "tutores", "pets", "consultas", "produtos", "categorias")}


def write_summary(output, results, soak_status):
    lines = ["# Resultado local", "", f"Soak: {soak_status}.", "",
             "| Perfil | Req/s | Média ms | Mediana ms | p95 ms | p99 ms | Erros/req | CPU média % | RSS pico MiB |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for result in results:
        stats = result["locust"]
        values = [result["profile"], stats.get("Requests/s"), stats.get("Average Response Time"),
                  stats.get("Median Response Time"), stats.get("95%"), stats.get("99%"),
                  f'{stats.get("Failure Count", "?")}/{stats.get("Request Count", "?")}',
                  result["server_cpu_mean_pct"], result["server_rss_peak_mib"]]
        lines.append("| " + " | ".join(str(v) if v is not None else "N/D" for v in values) + " |")
        if result["interrupted"]:
            lines.append(f'\nInterrupção {result["profile"]}: {result["interrupted"]}.\n')
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def profile(users, seconds, label, root, output, base_env, hashes, workers):
    import psutil
    # Executa sempre a cópia imutável desta rodada, identificada em metadata.json.
    database = root / f"{label}.db"
    env = dict(base_env, UNIVET_DATABASE=str(database))
    with (output / f"{label}-seed.log").open("w") as log:
        subprocess.run([sys.executable, str(root / "source/perf/bench_app.py")],
                       cwd=root / "source", env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=120)
    initial = counts(database)
    # Escolha efêmera; a checagem de processo abaixo detecta eventual disputa pela porta.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    host = f"http://127.0.0.1:{port}"
    server = load = None
    samples = []
    reason = None
    with (output / f"{label}-gunicorn.log").open("w") as server_log, \
            (output / f"{label}-locust.log").open("w") as load_log:
        try:
            server = spawn([sys.executable, "-m", "gunicorn", "--bind", f"127.0.0.1:{port}",
                            "--workers", str(workers), "--worker-class", "sync", "--timeout", "30",
                            "--chdir", str(root / "source/perf"), "bench_app:app"], env, root, server_log)
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Gunicorn encerrou; consulte log")
                try:
                    with urlopen(host + "/login", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Gunicorn não ficou pronto")
            load = spawn([sys.executable, "-m", "locust", "-f", "perf/locustfile.py",
                          "--headless", "--host", host, "--users", str(users),
                          "--spawn-rate", str(min(users, 5)), "--run-time", f"{seconds}s",
                          "--stop-timeout", "10", "--only-summary", "--exit-code-on-error", "1",
                          "--csv", str(output / label), "--csv-full-history",
                          "--html", str(output / f"{label}.html")], env, root, load_log)
            start = time.monotonic()
            server_prev = load_prev = {}
            saturated = 0
            while load.poll() is None:
                now = time.monotonic()
                cpu, ram, server_prev = tree_usage(server.pid, server_prev, now)
                load_cpu, load_ram, load_prev = tree_usage(load.pid, load_prev, now)
                available = psutil.virtual_memory().available / 1024**2
                host_cpu = psutil.cpu_percent()
                samples.append({"elapsed_s": round(now - start, 2), "server_cpu_pct": cpu,
                                "server_rss_mib": ram, "locust_cpu_pct": load_cpu,
                                "locust_rss_mib": load_ram, "host_cpu_pct": host_cpu,
                                "host_available_mib": available})
                saturated = saturated + 1 if host_cpu > 98 else 0
                if available < 256 or saturated >= 15:
                    reason = "interrompido por recursos: RAM disponível <256 MiB ou CPU host >98% por 15 amostras"
                elif server.poll() is not None:
                    reason = "Gunicorn encerrou durante carga"
                elif now - start > seconds + 45:
                    reason = "timeout externo do perfil"
                if reason:
                    stop(load)
                    break
                time.sleep(1)
            code = load.wait()
        finally:
            stop(load)
            stop(server)
    with (output / f"{label}-resources.csv").open("w", newline="") as stream:
        if samples:
            writer = csv.DictWriter(stream, fieldnames=samples[0])
            writer.writeheader()
            writer.writerows(samples)
    statfile = output / f"{label}_stats.csv"
    aggregate = {}
    if statfile.exists():
        with statfile.open(newline="") as stream:
            aggregate = next((r for r in csv.DictReader(stream) if r["Name"] == "Aggregated"), {})
    final = counts(database)
    result = {"profile": label, "users": users, "duration_s": seconds, "exit_code": code,
              "interrupted": reason, "locust": aggregate, "rows_before": initial, "rows_after": final,
              "server_cpu_mean_pct": statistics.mean(s["server_cpu_pct"] for s in samples[1:]) if len(samples) > 1 else None,
              "server_rss_peak_mib": max((s["server_rss_mib"] for s in samples), default=None)}
    # Evidência adicional de persistência/integridade, fora da janela medida.
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        result["integrity_check"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
        result["foreign_key_errors"] = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if not aggregate or float(aggregate.get("Request Count", 0)) == 0:
        result["interrupted"] = reason or "nenhuma requisição medida"
    (output / f"{label}-summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", help="usar somente após liberação explícita do agente principal")
    parser.add_argument("--soak", action="store_true", help="após os seis perfis, tentar 10 usuários por 600s")
    parser.add_argument("--disable-rate-limit", action="store_true", help="UNIVET_RATE_LIMIT_ENABLED=0 apenas nos filhos isolados")
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()
    if not args.authorized:
        parser.error("Aguardando agente principal: auth pronta e código estável; não execute sem autorização")
    if os.environ.get("UNIVET_BENCH_UV") != "1":
        uv = shutil.which("uvx")
        if not uv:
            parser.error("uvx não encontrado; instalar uv antes de executar")
        env = dict(os.environ, UNIVET_BENCH_UV="1")
        os.execvpe(uv, [uv, "--isolated", "--no-env-file", "--from", "locust>=2.32,<3", "--with", "psutil>=6,<8",
                       "--with-requirements", str(REPO / "requirements.txt"),
                       "python", str(Path(__file__).resolve()), *sys.argv[1:]], env)
    import psutil
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = PERF / "results" / stamp
    output.mkdir(parents=True)
    hashes = fingerprint()
    metadata = {"utc": stamp, "platform": platform.platform(), "python": platform.python_version(),
                "cpu_logical": psutil.cpu_count(), "ram_mib": psutil.virtual_memory().total / 1024**2,
                "workers": args.workers, "rate_limit_disabled": args.disable_rate_limit,
                "source_sha256": hashes,
                "versions": {name: importlib.metadata.version(name) for name in ("locust", "gunicorn", "Flask", "Werkzeug", "psutil")}}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Evidências: {output}", flush=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="univet-bench-") as temporary:
        root = Path(temporary)
        (root / "isolated-benchmark").touch()
        for path in source_files():
            target = root / "source" / path.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if fingerprint() != hashes:
            raise RuntimeError("Código mudou durante cópia; aguarde nova autorização")
        # Não herdar configurações de produção, proxy, .env, hooks ou opções Locust/Gunicorn.
        env = {k: v for k, v in os.environ.items() if k in
               ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "VIRTUAL_ENV", "UNIVET_BENCH_LOGIN", "UNIVET_BENCH_PASSWORD")}
        env.update(UNIVET_BENCH_ROOT=str(root), UNIVET_ENV="development",
                   SECRET_KEY=secrets.token_hex(32), UNIVET_SECRET_KEY=secrets.token_hex(32),
                   PYTHONDONTWRITEBYTECODE="1", NO_PROXY="127.0.0.1,localhost")
        if args.disable_rate_limit:
            env["UNIVET_RATE_LIMIT_ENABLED"] = "0"
        for users in PROFILES:
            result = profile(users, 30, f"users-{users:02d}", root, output, env, hashes, args.workers)
            results.append(result)
            if result["exit_code"] or result["interrupted"] or result["integrity_check"] != "ok" or result["foreign_key_errors"]:
                break
        soak_status = "não solicitado"
        if args.soak:
            if len(results) == 6 and all(not r["exit_code"] and not r["interrupted"] for r in results) \
                    and psutil.virtual_memory().available >= 1024**3 and psutil.cpu_percent(interval=1) < 85:
                results.append(profile(10, 600, "soak-10", root, output, env, hashes, args.workers))
                soak_status = "executado; consultar resultado"
            else:
                soak_status = "não executado: perfil anterior falhou ou recursos insuficientes (1 GiB livre, CPU <85%)"
        (output / "summary.json").write_text(json.dumps({"profiles": results, "soak": soak_status}, indent=2), encoding="utf-8")
        write_summary(output, results, soak_status)
    if len(results) < 6 or any(r["exit_code"] or r["interrupted"] or r["integrity_check"] != "ok" or r["foreign_key_errors"] for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
