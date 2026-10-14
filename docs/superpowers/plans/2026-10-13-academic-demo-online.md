# UniVet Academic Demo Online Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** deixar o UniVet pronto para avaliação acadêmica como uma demonstração online gratuita, usando somente dados fictícios, `UNIVET_ENV=demo`, PostgreSQL/Neon separado e sem apresentar o sistema como pronto para uma clínica real.

**Architecture:** preservar a aplicação Flask e os módulos existentes; validar o fluxo completo em banco descartável, tornar explícita a configuração demo e documentar o provisionamento idempotente. A publicação só avançará se houver um serviço gratuito realmente utilizável e sem cobrança, caso contrário o resultado será um bloqueio documentado, sem criar compromissos financeiros.

**Tech Stack:** Python/Flask, Gunicorn, PostgreSQL via psycopg/libpq, Neon Free para demo, Render Free quando o workspace puder ser reativado sem cobrança, e Koyeb somente se sua modalidade gratuita atual puder ser usada sem cartão/risco de cobrança.

**Spec:** `/home/giovanni/.codex/attachments/49c0dd8e-6e8b-4878-91e7-bd7a68f1ede8/Texto colado.txt`

## Global constraints

- Trabalhar somente em `/media/giovanni/HD/Projetos/PI/UniVet 2/UniVet`.
- Não tocar em `/media/giovanni/HD/Projetos/PI/Sistema Clinica Vet`.
- Não usar reset, rebase, force-push, apagar arquivos ou sobrescrever alterações locais.
- Não expor valores de `DATABASE_URL`, `SECRET_KEY` ou qualquer outro segredo.
- Não usar dados reais, não criar `DrFernanda` e não alterar planos pagos.
- Manter a branch Security preservada e integrar apenas com merge explícito quando os gates forem aprovados.
- Toda validação PostgreSQL deverá usar banco descartável ou o banco demo explicitamente autorizado; nunca um banco de clínica real.

## Task 1: Establish a reproducible baseline

**Files:** `README.md`, `docs/current-state.md`, `docs/prontidao-clinica.md`, `docs/checklist-producao-clinica.md`

- [ ] Confirm `main`, HEAD, origin, clean status, target commits and branch divergence.
- [ ] Run the existing full suite, PostgreSQL opt-in suite, compilation and `git diff --check`.
- [ ] Record the baseline commit and any pre-existing failures without changing behavior.
- [ ] Preserve the current Render suspension as an infrastructure fact, not as a code workaround.

## Task 2: Validate the demo configuration and fictional seed

**Files:** `config.py`, `init_db.py`, relevant tests under `tests/`

- [ ] Confirm `UNIVET_ENV=demo` requires an isolated `DEMO_DATABASE_URL` and cannot silently use production storage.
- [ ] Exercise the existing fictional demo seed against a disposable PostgreSQL database.
- [ ] Verify the seed is repeatable, does not reset existing demo data unexpectedly, and never creates `DrFernanda` or real-person data.
- [ ] Verify the academic demo account is fictional and document its safe creation path without committing credentials.
- [ ] Add or adjust only focused tests for any proven gap; preserve existing APIs and business rules.

## Task 3: Execute the academic functional and security gates

**Files:** existing application and test suite; add focused coverage only where absent

- [ ] Validate login, dashboard, tutors, animals, veterinarians, services, scheduling, consultations and history.
- [ ] Validate stock, products, categories, suppliers, lots, entries, exits, FEFO, automatic reduction, alerts, reports, API, CSV and logout.
- [ ] Validate adjustments, reversals, authorization, CSRF, sessions, migrations, rate limiting and security headers.
- [ ] Validate the PostgreSQL path with `SELECT 1`, migrations at head, TLS requirements (`verify-full`, trusted root, `channel_binding=require`) and persistence.
- [ ] If a test fails, diagnose the exact failure, apply the smallest safe fix, and repeat the failed gate plus the regression suite.

## Task 4: Update the academic README and evaluation guidance

**Files:** `README.md`, optionally `docs/current-state.md`

- [ ] Reframe the project as PI II / academic evaluation software and explicitly state that it is not ready for real-clinic data.
- [ ] Document the demo environment, fictional data policy, main modules, stock/FEFO functionality, Flask/PostgreSQL/Neon stack and local evaluation commands.
- [ ] Document the academic demo account provisioning without exposing a secret.
- [ ] Add the final online URL only after it is verified; do not publish a guessed or suspended URL as available.

## Task 5: Evaluate and provision one free online demo path

**Files:** Render/Koyeb configuration only if required and safe; no secret values committed

- [ ] Inspect the existing Render Demo service and the suspended workspace without paying, adding a card, upgrading, or changing paid settings.
- [ ] Check the current official Koyeb Free terms and whether deployment is possible without card or pay-per-use exposure.
- [ ] Select Render only if the free service can be reactivated without payment; otherwise select Koyeb only if it satisfies the same no-cost/no-card constraints.
- [ ] Configure the chosen service with the consolidated `main`, the existing build/start commands, `UNIVET_ENV=demo`, and masked environment variable names only.
- [ ] Keep `DATABASE_URL`/`DEMO_DATABASE_URL` isolated from any production or clinical database and never print their values.

## Task 6: Deploy and perform online smoke/persistence/isolation checks

- [ ] Confirm the deployed commit and branch.
- [ ] Check HTTPS, `/health`, `/login`, `/`, no 503, no traceback, database reachability and migration state.
- [ ] Create only fictional academic test data, verify it survives restart and redeploy, then remove temporary records when appropriate.
- [ ] Verify Demo and Clínica use different databases and that users/data cannot cross environments.
- [ ] Do not create `DrFernanda` while any blocker remains.

## Task 7: Consolidate only after all gates pass

- [ ] Update local `main` from the remote without discarding work.
- [ ] Merge `security/demo-producao-isolados` into `main` with an explicit non-rewriting merge if it is not already integrated.
- [ ] Resolve conflicts in favor of the newest safe behavior and rerun the essential tests.
- [ ] Create a clear merge commit and push `main`; do not delete the Security branch.
- [ ] Update `docs/current-state.md`, `docs/auditoria-seguranca.md`, `docs/prontidao-clinica.md` and `docs/checklist-producao-clinica.md` with commit, URL, deploy, test results and blockers.

## Review focus

- Demo isolation must be enforced by configuration, not only by documentation.
- No credentials, real people, real clinical records or secrets may appear in code, tests, logs or README.
- A suspended provider or unavailable free tier is a blocker; it must not be bypassed with a paid plan.
- “Apto para piloto controlado” is allowed only when all blockers are zero; otherwise status remains academic demo / not ready for real data.
- The final report must distinguish code readiness, database readiness and hosting availability.
