#!/bin/bash

# Production deployment
echo "Starting production deployment..."

# Set environment variables
export REGISTRY=your-registry.com
export TAG=$(git rev-parse --short HEAD)
export DB_USER=postgres
export DB_PASSWORD=your-secure-password
export GEMINI_API_KEY=your-llm-api-key
export GOOGLE_API_KEY=your-llm-api-key
export OPENAI_API_KEY=your-llm-api-key
export APP_URL=https://your-domain.com

# Create Docker secrets for sensitive data
echo "Creating Docker secrets..."
echo "$DB_PASSWORD" | docker secret create db_password -
echo "$GEMINI_API_KEY" | docker secret create gemini_api_key -
echo "$GOOGLE_API_KEY" | docker secret create google_api_key -
echo "$OPENAI_API_KEY" | docker secret create openai_api_key -

# Build and push Docker images
echo "Building and pushing Docker images..."
docker build -t $REGISTRY/runarion-app-postgres:$TAG .
docker build -t $REGISTRY/runarion-app-laravel:$TAG ./runarion-laravel
docker build -t $REGISTRY/runarion-app-runarion-python:$TAG ./runarion-python

docker push $REGISTRY/runarion-app-postgres:$TAG
docker push $REGISTRY/runarion-app-laravel:$TAG
docker push $REGISTRY/runarion-app-runarion-python:$TAG

# Deploy stack to Docker Swarm
echo "Deploying stack to Docker Swarm..."
docker stack deploy -c docker-compose.yml runarion-app

echo "Deployment complete! Checking service status..."
docker service ls --filter name=runarion-app