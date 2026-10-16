API := apps/api
UV  := uv

.DEFAULT_GOAL := help
.PHONY: help doctor api-install api-test api-lint api-fmt api-typecheck check

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

doctor: ## Verifica las herramientas del entorno
	@./scripts/doctor.sh

api-install: ## Instala dependencias de la API
	cd $(API) && $(UV) sync

api-test: ## Ejecuta las pruebas de la API
	cd $(API) && $(UV) run pytest

api-lint: ## Lint y formato (verificación) de la API
	cd $(API) && $(UV) run ruff check . && $(UV) run ruff format --check .

api-fmt: ## Formatea y corrige la API
	cd $(API) && $(UV) run ruff format . && $(UV) run ruff check --fix .

api-typecheck: ## Revisión de tipos de la API
	cd $(API) && $(UV) run mypy app tests

check: api-lint api-typecheck api-test ## Todo lo que corre en CI
