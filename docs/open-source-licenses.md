# Open-source licenses

The project code and original synthetic fixtures use Apache-2.0. No model weights, proprietary datasets or paid API SDKs are required. Package/container licenses apply independently; installation does not transfer their copyright to this project.

## Material dependencies

| Component | Use | License / notes |
|---|---|---|
| CPython | Backend runtime | Python Software Foundation License; included third-party notices apply |
| NumPy | Numerical fitting and monitoring | BSD-3-Clause; binary wheels may include OpenBLAS/LAPACK and compiler-runtime notices under their own licenses |
| FastAPI / Pydantic / pydantic-core | Typed API and validation | MIT |
| Starlette / Uvicorn | ASGI stack | BSD-3-Clause |
| HTTPX / HTTPCore | Optional local runtime transport and tests | BSD-3-Clause |
| SQLite | Local transactional registry | Public domain |
| React / React DOM | Dashboard | MIT |
| Vite | Local development and build | MIT |
| TypeScript | Static typechecking | Apache-2.0 |
| Lucide React | UI icons | ISC |
| Node.js / pnpm | Frontend build runtime/package manager | MIT; Node includes additional third-party notices |
| pytest | Backend tests | MIT |
| pytest-cov | Coverage integration | MIT |
| coverage.py | Coverage measurement | Apache-2.0 |
| Ruff | Python lint/format | MIT |
| Vitest / Testing Library / ESLint / Prettier | Frontend tests and lint | MIT |
| Playwright | Browser lifecycle tests | Apache-2.0; downloaded Chromium has its own third-party licenses |
| pip-audit | Dependency advisory check | Apache-2.0 |
| PyYAML | Local/CI configuration checks | MIT |
| Nginx | Static web server and API proxy | BSD-2-Clause |
| Docker Engine / Compose | Local container execution | Apache-2.0; Docker Desktop is not required |
| Colima | Optional open-source macOS container runtime | MIT |
| Trivy / trivy-action | CI container dependency scan | Apache-2.0 |
| GitHub checkout/setup/upload actions | CI orchestration | MIT; the GitHub service itself is optional infrastructure, not required for the application |
| Ollama | Optional local model runtime | MIT runtime; chosen weights have separate licenses |
| llama.cpp | Optional local model runtime | MIT; chosen weights have separate licenses |
| vLLM | Optional local model runtime | Apache-2.0; chosen weights have separate licenses |
| ConsignAI synthetic sample | Included source fixture | Apache-2.0; original LICENSE and NOTICE in `data/upstream` |

The `python:3.12-slim`, `node:24-alpine`, and `nginxinc/nginx-unprivileged:1.28-alpine` images aggregate OS packages with individual licenses. Alpine contains MIT-licensed musl and GPL-licensed utilities such as BusyBox; Debian images also include packages with varied licenses. Refer to the image/package notices when redistributing images. No image is represented as having one blanket project license.

## Inventories and locks

- [Python inventory](python-dependency-licenses.md): installed runtime and development packages, exact versions and declared metadata.
- [Frontend inventory](frontend-dependency-licenses.md): installed direct/transitive frontend packages and declared licenses, including development tools.
- `requirements.lock`, `requirements-dev.lock`, `apps/web/pnpm-lock.yaml`: exact resolved versions.
- Inventory commands: `python scripts/lock_dependencies.py` and `node scripts/frontend_licenses.mjs`.

Inventories are metadata-based aids. License files in each distribution remain authoritative. Long license notices are summarized in the inventory, not relicensed. Optional platform binaries can differ across operating systems; review the packages actually shipped for your platform.

## Model weights

There is no default or bundled model. Users select an installed local model and are responsible for reviewing its license, acceptable-use terms and redistribution permissions. Runtime licensing does not imply permissive licensing for every compatible weight file. Do not use a cloud-proxy model in the local-only demo path. No model license is silently accepted or download initiated by this application.

## Upstream source links

[NumPy](https://github.com/numpy/numpy/blob/main/LICENSE.txt), [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE), [Pydantic](https://github.com/pydantic/pydantic/blob/main/LICENSE), [React](https://github.com/facebook/react/blob/main/LICENSE), [Lucide](https://github.com/lucide-icons/lucide/blob/main/LICENSE), [SQLite](https://www.sqlite.org/copyright.html), [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE), [vLLM](https://github.com/vllm-project/vllm/blob/main/LICENSE), [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE).
