#!/bin/bash

# Check if we're in development mode
if [ "$1" = "dev" ]; then
    echo "Starting in development mode..."
    # Set local development environment variables
    export REGISTRY=localhost
    export TAG=latest
    export DB_USER=postgres
    export DB_PASSWORD=@kb4r123
    export GEMINI_API_KEY=your-llm-api-key
    export GOOGLE_API_KEY=your-llm-api-key
    export OPENAI_API_KEY=your-llm-api-key
    export APP_URL=http://localhost:8000
    
    # Build and start containers
    echo "Building and starting containers..."
    docker-compose -f docker-compose.dev.yml up -d --build
    
    # Wait for the database to be ready
    echo "Waiting for database to be ready..."
    sleep 10
    
    # Generate Laravel application key
    echo "Generating Laravel application key..."
    docker-compose -f docker-compose.dev.yml exec laravel-app php artisan key:generate
    
    # Run Laravel migrations
    echo "Running Laravel migrations..."
    docker-compose -f docker-compose.dev.yml exec laravel-app php artisan migrate --force
    
    # Install Laravel frontend dependencies and build assets
    echo "Installing Laravel frontend dependencies..."
    docker-compose -f docker-compose.dev.yml exec laravel-app npm install
    docker-compose -f docker-compose.dev.yml exec laravel-app npm run build
    
    # Set proper permissions
    echo "Setting proper permissions..."
    docker-compose -f docker-compose.dev.yml exec laravel-app chown -R www-data:www-data storage bootstrap/cache
    
    echo "Development environment is ready!"
    echo "Laravel frontend: http://localhost:8000"
    echo "Python service: http://localhost:5000"
else
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
fi