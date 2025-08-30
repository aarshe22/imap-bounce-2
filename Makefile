IMAGE_NAME=ghcr.io/aarshe22/imap-bounce-app
TAG=latest

.PHONY: help build push up down logs

help:
	@echo "Available commands:"
	@echo "  make build   - Build the Docker image"
	@echo "  make push    - Push the image to GHCR"
	@echo "  make up      - Run docker-compose up"
	@echo "  make down    - Stop the containers"
	@echo "  make logs    - Tail logs"

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

push:
	docker push $(IMAGE_NAME):$(TAG)

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f
