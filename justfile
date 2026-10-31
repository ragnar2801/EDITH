# Friday command runner. Run `just` to list the commands.
# On Windows each line runs in PowerShell; elsewhere in sh.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# npm.ps1 is blocked by Windows' default script policy, so call npm.cmd there.
npm := if os_family() == "windows" { "npm.cmd" } else { "npm" }

# List the commands
default:
    @just --list

# Install everything, set up the database and build the UI
setup:
    uv sync --project backend
    {{ npm }} --prefix frontend ci
    uv run --project backend friday migrate
    {{ npm }} --prefix frontend run build

# Run Friday for daily use at http://localhost:8000
run:
    uv run --project backend friday serve

# Develop with hot reload: UI at http://localhost:5173, API on :8000
dev:
    uv run --project backend python scripts/dev.py

# Build the UI that `just run` serves
build:
    {{ npm }} --prefix frontend run build

# Upgrade the database to the latest schema
migrate:
    uv run --project backend friday migrate

# Create a migration from model changes, e.g. `just revision "add holdings"`
revision message:
    uv run --directory backend alembic revision --autogenerate -m "{{ message }}"

# Download the NSE, AMFI and US lists and update instruments, e.g. `just instruments --source amfi`
instruments *args:
    uv run --project backend friday instruments refresh {{ args }}

# Download missing NAVs for every tracked fund, e.g. `just navs` or `just navs --fund 122639`
navs *args:
    uv run --project backend friday navs sync {{ args }}

# Regenerate the TypeScript API types from the backend schema
api:
    uv run --project backend friday openapi --out frontend/src/api/openapi.json
    {{ npm }} --prefix frontend run gen:api

# Fail if the generated API types are out of date
api-check: api
    git diff --exit-code -- frontend/src/api

# Run all tests
test:
    uv run --project backend pytest backend
    {{ npm }} --prefix frontend test

# Check lint, formatting and types
lint:
    uv run --project backend ruff check backend scripts
    uv run --project backend ruff format --check backend scripts
    {{ npm }} --prefix frontend run lint

# Fix formatting and auto-fixable lint
fmt:
    uv run --project backend ruff format backend scripts
    uv run --project backend ruff check --fix backend scripts
    {{ npm }} --prefix frontend run format

# Start the real server with a throwaway database and check it answers
smoke:
    uv run --project backend python scripts/smoke.py
