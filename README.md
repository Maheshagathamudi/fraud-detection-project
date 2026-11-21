# Real-Time Fraud Detection Engine

A modular transaction risk decision service with a FastAPI backend, PostgreSQL storage, Redis-ready infrastructure, an optional Scikit-learn/XGBoost scoring path, and a React + TypeScript monitoring dashboard. The local development configuration works with SQLite and does not require Docker.

See [docs/architecture.md](docs/architecture.md) for system boundaries, the transaction flow, data protections, and scale-up path.

## What works in this starter

- Versioned FastAPI endpoints for liveness/readiness, transaction decisions, transaction history, and summary metrics.
- Idempotency key handling with request-hash conflict detection.
- Durable transaction and decision records. SQLite is the local default; Compose uses PostgreSQL.
- Transactional outbox events for review/decline decisions, published to a Redis Stream by a retrying worker in Compose.
- Explainable amount and 10-minute velocity rules with configurable thresholds.
- USD-only amounts in the initial policy; adding other currencies requires FX normalization and calibrated thresholds.
- Optional model-artifact integration; without a model, the API does not invent a prediction.
- Responsive monitoring dashboard with sample transaction controls and five-second refresh.
- Synthetic model-data generator and evaluation workflow. Synthetic performance is not evidence of real-world fraud detection quality.

## Environment

The laptop has Python 3.14.2, Node.js 24.13.0, npm 11.6.2, and Git 2.51.1. Docker is not available on PATH. Project packages support Python 3.12–3.14; the containers use Python 3.12 and Node.js 22. Node.js is only needed for the dashboard. Docker Desktop with WSL2 is needed for PostgreSQL, Redis rate counters, and the outbox worker; local SQLite works without it.

Check the installed versions in PowerShell:

```powershell
python --version
node --version
npm --version
git --version
docker --version
docker compose version
```

## Run locally

From the repository root, create the virtual environment and install the API:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .\backend
Copy-Item .env.example backend\.env
Set-Location .\backend
.\.venv\Scripts\alembic.exe upgrade head
```

In one PowerShell window, start the API:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

In another PowerShell window, start the dashboard:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again.

Open `http://localhost:5173` for the dashboard and `http://127.0.0.1:8000/docs` for the API. Use the sample controls to create synthetic transactions with opaque demo tokens only.

## Run with PostgreSQL and Redis

Start Docker Desktop, then run from the repository root:

```powershell
docker compose up --build
```

The dashboard is at `http://localhost:5173`; the API docs are at `http://localhost:8000/docs`. Compose credentials are local development values. Replace them and add reviewer identity, secret management, and deployment hardening before any shared or production environment.

## Train the illustrative model

Install the optional ML extra and follow [ml-engine/README.md](ml-engine/README.md):

```powershell
python -m pip install -e .\backend[ml]
python ml-engine/data/generate_synthetic.py --rows 20000
python ml-engine/training/train.py --model sklearn
```

The generated data is synthetic and only exercises feature and evaluation plumbing. A real deployment requires a representative, licensed dataset, leakage controls, threshold calibration, monitoring, and human review policy.
