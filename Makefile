.PHONY: compile lint format-check diff-check test validate validate-json validate-generated pipeline dashboard api-smoke smoke ci web-install web-dev web-typecheck web-build web-clean web-ci docker-build helm-lint helm-template terraform-fmt terraform-validate deploy-check uv-sync uv-lock pre-commit-install pre-commit-run pip-audit npm-audit security

test:
	PYTHONPATH=src python -m pytest -q

compile:
	PYTHONPATH=src python -m compileall -q src tests tools

lint:
	PYTHONPATH=src python -m ruff check src tests tools

format-check:
	PYTHONPATH=src python -m ruff format --check src tests tools

diff-check:
	git diff --check

validate:
	PYTHONPATH=src python -m security_lakehouse.cli validate --raw data/raw/security_events.jsonl
	PYTHONPATH=src python -m security_lakehouse.cli connectors validate
	PYTHONPATH=src python -c "from security_lakehouse.catalog import validate_catalog; from security_lakehouse.programs import validate_program_catalog; errors = validate_catalog() + validate_program_catalog(); assert not errors, errors"
	PYTHONPATH=src python -m security_lakehouse.cli catalog verify

validate-json:
	PYTHONPATH=src python tools/validate_ci_artifacts.py

validate-generated:
	PYTHONPATH=src python tools/validate_ci_artifacts.py --generated

validate-doc-images:
	PYTHONPATH=src python tools/validate_doc_images.py

pipeline:
	PYTHONPATH=src python -m security_lakehouse.cli pipeline run --raw data/raw/security_events.jsonl --out build/lakehouse

dashboard:
	PYTHONPATH=src python -m security_lakehouse.cli dashboard --lake build/lakehouse --out build/dashboard/index.html

api-smoke:
	PYTHONPATH=src python tools/api_smoke.py

smoke: validate validate-json validate-doc-images pipeline validate-generated dashboard api-smoke test

ci: diff-check compile lint format-check web-ci smoke

# --- React (Next.js) workbench targets -------------------------------------
# Lives in app/web/, builds to src/security_lakehouse/web/dist/ so the Python
# wheel ships the bundle. Dev mode proxies /api to a running `security-lakehouse serve`.

web-install:
	npm --prefix app/web ci

web-dev:
	npm --prefix app/web run dev

web-typecheck:
	npm --prefix app/web run typecheck

web-build:
	npm --prefix app/web run build

demo-screenshots:
	npm --prefix app/web run demo-screenshots

web-ci: web-install web-typecheck web-build

web-clean:
	rm -rf src/security_lakehouse/web/dist/* src/security_lakehouse/web/dist/.* 2>/dev/null || true
	mkdir -p src/security_lakehouse/web/dist
	touch src/security_lakehouse/web/dist/.gitkeep

# --- Deploy targets -------------------------------------------------------
# Container image, Helm chart, EKS Terraform reference IaC.

docker-build:
	docker build -t trustops:dev .

helm-lint:
	helm lint deploy/helm/trustops

helm-template:
	helm template trustops deploy/helm/trustops > /tmp/trustops-helm-render.yaml
	@echo "wrote /tmp/trustops-helm-render.yaml ($$(wc -l < /tmp/trustops-helm-render.yaml) lines)"

terraform-fmt:
	terraform -chdir=deploy/eks-terraform fmt -check

terraform-validate:
	terraform -chdir=deploy/eks-terraform init -backend=false -input=false
	terraform -chdir=deploy/eks-terraform validate

deploy-check: helm-lint helm-template terraform-fmt terraform-validate

# --- Supply-chain + commit hooks -------------------------------------------
# uv is the recommended package manager (deterministic + locked install).
# pip still works as a fallback when uv isn't installed.

uv-sync:
	uv sync --frozen --all-extras

uv-lock:
	uv lock

framework-packs:
	PYTHONPATH=src python -m security_lakehouse.cli frameworks sync-packs

pre-commit-install:
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

pre-commit-run:
	uv run pre-commit run --all-files

pip-audit:
	uv export --no-emit-project --format requirements-txt --no-hashes > /tmp/trustops-reqs.txt
	uv run pip-audit --strict -r /tmp/trustops-reqs.txt

npm-audit:
	cd app/web && npm audit --omit=dev --audit-level=high

security: pip-audit npm-audit pre-commit-run
