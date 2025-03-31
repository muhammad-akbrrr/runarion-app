#!/bin/bash

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "Error: Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if Docker Swarm is initialized
check_swarm() {
    if ! docker info | grep -q "Swarm: active"; then
        echo "Error: Docker Swarm is not initialized. Please run 'docker swarm init' first."
        exit 1
    fi
}

# Function to check if required environment variables are set
check_env_vars() {
    local required_vars=(
        "DB_PASSWORD"
        "GEMINI_API_KEY"
        "GOOGLE_API_KEY"
        "OPENAI_API_KEY"
        "APP_URL"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: $var is not set. Please set it before deploying."
            exit 1
        fi
    done
}

# Function to create Docker secrets
create_secrets() {
    echo "Creating Docker secrets..."
    # Remove existing secrets if they exist
    docker secret rm db_password 2>/dev/null || true
    docker secret rm gemini_api_key 2>/dev/null || true
    docker secret rm google_api_key 2>/dev/null || true
    docker secret rm openai_api_key 2>/dev/null || true

    # Create new secrets
    echo "$DB_PASSWORD" | docker secret create db_password -
    echo "$GEMINI_API_KEY" | docker secret create gemini_api_key -
    echo "$GOOGLE_API_KEY" | docker secret create google_api_key -
    echo "$OPENAI_API_KEY" | docker secret create openai_api_key -
}

# Function to build and push Docker images
build_and_push_images() {
    echo "Building and pushing Docker images..."
    local tag=$(git rev-parse --short HEAD)
    local registry=${REGISTRY:-localhost}

    # Build images
    docker build -t $registry/runarion-app-postgres:$tag .
    docker build -t $registry/runarion-app-laravel:$tag ./runarion-laravel
    docker build -t $registry/runarion-app-runarion-python:$tag ./runarion-python

    # Push images
    docker push $registry/runarion-app-postgres:$tag
    docker push $registry/runarion-app-laravel:$tag
    docker push $registry/runarion-app-runarion-python:$tag
}

# Function to deploy stack
deploy_stack() {
    echo "Deploying stack to Docker Swarm..."
    docker stack deploy -c docker-compose.yml runarion-app
}

# Function to wait for services to be ready
wait_for_services() {
    echo "Waiting for services to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        local services=$(docker service ls --filter name=runarion-app --format '{{.Name}}')
        local all_ready=true

        for service in $services; do
            local replicas=$(docker service ps $service --format '{{.CurrentState}}' | grep -c "Running")
            local desired=$(docker service ls --filter name=$service --format '{{.Replicas}}' | cut -d'/' -f2)

            if [ "$replicas" -ne "$desired" ]; then
                all_ready=false
                break
            fi
        done

        if [ "$all_ready" = true ]; then
            echo "All services are ready!"
            return 0
        fi

        echo "Waiting for services... (attempt $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done

    echo "Warning: Some services did not become ready in time"
    return 1
}

# Function to check service health
check_service_health() {
    echo "Checking service health..."
    local services=$(docker service ls --filter name=runarion-app --format '{{.Name}}')
    local unhealthy_services=()

    for service in $services; do
        if ! docker service ps $service --format '{{.CurrentState}}' | grep -q "Running"; then
            unhealthy_services+=($service)
        fi
    done

    if [ ${#unhealthy_services[@]} -ne 0 ]; then
        echo "Error: The following services are unhealthy:"
        printf '%s\n' "${unhealthy_services[@]}"
        return 1
    fi

    echo "All services are healthy!"
    return 0
}

# Function to handle script interruption
handle_interrupt() {
    echo -e "\nInterrupted by user. Cleaning up..."
    docker stack rm runarion-app
    exit 1
}

# Set up trap for script interruption
trap handle_interrupt SIGINT SIGTERM

# Main execution
echo "Starting production deployment..."

# Check prerequisites
check_docker
check_swarm
check_env_vars

# Create secrets
create_secrets

# Build and push images
build_and_push_images

# Deploy stack
deploy_stack

# Wait for services and check health
wait_for_services
check_service_health

echo "Deployment complete! Checking service status..."
docker service ls --filter name=runarion-app

echo "Application is now available at: $APP_URL"