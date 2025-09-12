VENV?=venv
PY=$(VENV)/bin/python
ALEMBIC=$(PY) -m alembic -c services/api/alembic.ini
DB_NAME?=diabetes_bot
DB_URL?=postgresql://postgres@localhost/$(DB_NAME)
RUN_AS_POSTGRES?=sudo -u postgres
PYTHONPATH?=PYTHONPATH=$(PWD)

# === VENV ===

venv:
	python3.12 -m venv venv && venv/bin/pip install -r requirements.txt

# === MIGRATIONS ===

migrate: venv
	$(PYTHONPATH) $(ALEMBIC) upgrade head

step-up:
	$(PYTHONPATH) $(ALEMBIC) upgrade +1

step-down:
	$(PYTHONPATH) $(ALEMBIC) downgrade -1

revision:
	$(PYTHONPATH) $(ALEMBIC) revision --autogenerate -m "change description"

current:
	$(PYTHONPATH) $(ALEMBIC) current

history:
	$(PYTHONPATH) $(ALEMBIC) history

stamp-head:
	$(PYTHONPATH) $(ALEMBIC) stamp head

show:
	$(PYTHONPATH) $(ALEMBIC) show head

# === DATA ===

load-lessons:
	$(PYTHONPATH) $(PY) -m services.api.app.diabetes.learning_fixtures --reset

seed-l1:
	$(RUN_AS_POSTGRES) psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -f scripts/seed_lesson_l1.sql

db-check:
        $(RUN_AS_POSTGRES) env DATABASE_URL="$(DB_URL)" $(PY) scripts/check_learning_db.py

# === CI ===

ci:
	pytest -q --cov
	mypy --strict .
	ruff check .
