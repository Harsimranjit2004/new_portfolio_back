install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

check:
	python3 -m compileall app

reindex:
	.venv/bin/python -m app.scripts.reindex

reindex-force:
	.venv/bin/python -m app.scripts.reindex --force
