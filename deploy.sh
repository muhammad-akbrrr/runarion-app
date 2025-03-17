#!/bin/bash

# Set environment variables
export REGISTRY=your-registry.com
export TAG=$(git rev-parse --short HEAD)
export DB_USER=postgres
export DB_PASSWORD=your-secure-password
export LLM_API_KEY=your-llm-api-key
export APP_URL=https://your-domain.com

# Build and push Docker images
echo "Building and pushing Docker images..."
docker build -t $REGISTRY/runarion-app-runarion-laravel:$TAG ./runarion-laravel
docker build -t $REGISTRY/runarion-app-runarion-python:$TAG ./runarion-python

docker push $REGISTRY/runarion-app-runarion-laravel:$TAG
docker push $REGISTRY/runarion-app-runarion-python:$TAG

# Deploy stack to Docker Swarm
echo "Deploying stack to Docker Swarm..."
docker stack deploy -c docker-compose.yml runarion-app

echo "Deployment complete! Checking service status..."
docker service ls --filter name=runarion-app