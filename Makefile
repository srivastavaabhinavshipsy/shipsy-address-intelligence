# Makefile for Docker operations

.PHONY: help build up down restart logs clean shell-backend shell-frontend

help:
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start containers in detached mode"
	@echo "  make down           - Stop and remove containers"
	@echo "  make restart        - Restart all containers"
	@echo "  make logs           - View container logs"
	@echo "  make logs-backend   - View backend logs"
	@echo "  make logs-frontend  - View frontend logs"
	@echo "  make clean          - Remove containers, volumes, and images"
	@echo "  make shell-backend  - Open shell in backend container"
	@echo "  make shell-frontend - Open shell in frontend container"
	@echo "  make reset-db       - Reset the database"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

clean:
	docker-compose down -v
	docker rmi address-validation-backend address-validation-frontend 2>/dev/null || true

shell-backend:
	docker exec -it address-validation-backend /bin/bash

shell-frontend:
	docker exec -it address-validation-frontend /bin/sh

reset-db:
	docker exec -it address-validation-backend python reset_database.py

# Development commands
dev-build:
	docker-compose -f docker-compose.dev.yml build

dev-up:
	docker-compose -f docker-compose.dev.yml up

dev-down:
	docker-compose -f docker-compose.dev.yml down