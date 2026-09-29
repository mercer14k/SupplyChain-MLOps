# Native development

Requirements: CPython 3.12+, Node.js 24 and pnpm 11.25.0. The checked dependency versions are in `requirements.lock`, `requirements-dev.lock` and `apps/web/pnpm-lock.yaml`. No GPU or LLM is required. Run all backend commands from the repository root.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
scml init
scml keys
```

In terminal one:

```bash
source .venv/bin/activate
uvicorn apps.api.main:app --host 127.0.0.1 --port 8018
```

In terminal two:

```bash
source .venv/bin/activate
scml worker
```

In terminal three:

```bash
corepack enable
corepack prepare pnpm@11.25.0 --activate
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://127.0.0.1:5188`. The Vite proxy preserves the origin/host so browser writes pass the same-origin policy. Do not run Compose on the same ports simultaneously. Stop each process with Ctrl+C. `scml drain` synchronously completes currently queued jobs for scripts and tests.

## Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\scml.exe init
.\.venv\Scripts\scml.exe keys
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8018
```

Open another PowerShell terminal for `.\.venv\Scripts\scml.exe worker`. In a third, run `corepack enable`, `corepack prepare pnpm@11.25.0 --activate`, `cd apps/web`, `pnpm install --frozen-lockfile`, and `pnpm dev`. These commands avoid requiring a PowerShell activation-policy change. Set environment variables as `$env:SCML_LLM_ENABLED="true"` if opting into local AI. Copy the sample environment file with `Copy-Item .env.example .env` for Compose.

Native mode reads process environment variables, not `.env` automatically. Use `.runtime` for generated state; never commit it. For a fresh isolated experiment, set `SCML_STATE_DIR` to another private directory instead of deleting your history.

## Checks

```bash
ruff format --check packages apps/api tests scripts
ruff check packages apps/api tests scripts
pytest --cov=scml --cov=apps.api --cov-report=term-missing
python -m scml.evaluation.benchmark
cd apps/web
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

Browser tests start isolated servers on 8019/5189 and use `.runtime/e2e`. Override `SCML_PYTHON` with an absolute Python path when your virtual environment is elsewhere. Chromium may need OS libraries on Linux; `pnpm exec playwright install --with-deps chromium` installs them on a disposable CI machine.

## Dependency updates

Update `pyproject.toml`, install into a clean virtual environment, then run `python scripts/lock_dependencies.py` to pin runtime/test dependencies and regenerate the Python license inventory. Update frontend packages with pnpm, regenerate its lockfile, and run the audit/tests. Regenerate the frontend license inventory with `node scripts/frontend_licenses.mjs` from the repository root. Do not add local absolute paths to lockfiles.

Development tools may emit platform-specific warnings. The tested Starlette release currently warns that its `httpx` TestClient integration is deprecated; the tests still exercise it successfully. It is a developer-tool migration item, not an application network dependency.
