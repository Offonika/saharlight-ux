# === MIGRATIONS ===
ALEMBIC=alembic -c services/api/alembic.ini
PYTHONPATH=PYTHONPATH=/opt/saharlight-ux

migrate:
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
        $(PYTHONPATH) python -m services.api.app.diabetes.learning_fixtures --reset
