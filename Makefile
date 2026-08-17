.PHONY: up down stop start logs ps reset build

up:
	docker compose up -d --build

build:
	docker compose build

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

stop:
	docker compose stop

start:
	docker compose start

down:
	docker compose down

reset:
	docker compose down -v
	docker compose up -d --build
