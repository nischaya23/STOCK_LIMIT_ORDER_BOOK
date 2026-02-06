up:
	docker compose up -d

deps:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

migrate:
	. .venv/bin/activate && python manage.py migrate

run:
	. .venv/bin/activate && python manage.py runserver

