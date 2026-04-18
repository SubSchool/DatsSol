BACKEND_DIR=backend
FRONTEND_DIR=frontend

.PHONY: install-backend install-frontend dev-backend live-backend dev-frontend up down

install-backend:
	cd $(BACKEND_DIR) && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

install-frontend:
	cd $(FRONTEND_DIR) && npm install

dev-backend:
	cd $(BACKEND_DIR) && . .venv/bin/activate && RUNTIME_AUTOSTART=false uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

live-backend:
	cd $(BACKEND_DIR) && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev -- --host 0.0.0.0 --port 5173

up:
	docker compose up --build

down:
	docker compose down
