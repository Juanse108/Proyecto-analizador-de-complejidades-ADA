.PHONY: up down build logs fmt

up:
	docker compose up --build

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

fmt:
	black . || true
	ruff check . --fix || true
