API := apps/api
UV  := uv
SB  := pnpm exec supabase

# Node (fnm) y uv viven en el espacio de usuario; así make los encuentra sin shell interactivo.
export PATH := $(HOME)/.local/share/fnm/aliases/default/bin:$(HOME)/.local/bin:$(PATH)

.DEFAULT_GOAL := help
.PHONY: help doctor api api-install api-test api-lint api-fmt api-typecheck check db-start db-stop db-reset db-test db-check

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

doctor: ## Verifica las herramientas del entorno
	@./scripts/doctor.sh

api: ## Levanta la API en el puerto 8000 (necesita apps/api/.env y make db-start)
	cd $(API) && $(UV) run uvicorn app.main:app --reload --port 8000

api-install: ## Instala dependencias de la API
	cd $(API) && $(UV) sync

api-test: ## Ejecuta las pruebas de la API (las de integración se omiten sin make db-start)
	cd $(API) && $(UV) run pytest

api-lint: ## Lint y formato (verificación) de la API
	cd $(API) && $(UV) run ruff check . && $(UV) run ruff format --check .

api-fmt: ## Formatea y corrige la API
	cd $(API) && $(UV) run ruff format . && $(UV) run ruff check --fix .

api-typecheck: ## Revisión de tipos de la API
	cd $(API) && $(UV) run mypy app tests

db-start: ## Levanta Supabase local (Postgres, Auth y Storage en Docker)
	$(SB) start

db-stop: ## Detiene Supabase local
	$(SB) stop

db-reset: ## Recrea la base local con las migraciones y el seed
	$(SB) db reset

db-test: ## Pruebas pgTAP de la base (requiere Supabase local levantado)
	$(SB) test db

db-check: db-reset db-test ## Migraciones desde cero y pruebas pgTAP (lo que corre CI)

check: api-lint api-typecheck api-test ## Python: lo que corre en CI para apps/api
