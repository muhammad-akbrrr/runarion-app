#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if CUDA is available
check_cuda() {
    log "Checking CUDA availability..."
    
    # Check if nvidia-smi is available and working
    if ! command -v nvidia-smi &> /dev/null; then
        log "Warning: nvidia-smi not found, but continuing anyway..."
        return 0
    fi
    
    # Try to get CUDA version from nvidia-smi
    if ! nvidia-smi --query-gpu=driver_version --format=csv,noheader &> /dev/null; then
        log "Warning: Could not get CUDA version from nvidia-smi, but continuing anyway..."
        return 0
    fi
    
    log "NVIDIA GPU detected"
    nvidia-smi || true
    return 0
}

# Function to check if required models are present
check_models() {
    log "Checking required models..."
    local required_models=(
        "models/stable-diffusion-v1-5/model_index.json"
        "models/stable-diffusion-v1-5/v1-5-pruned.safetensors"
        "models/stable-diffusion-v1-5/scheduler/scheduler_config.json"
        "models/controlnet/diffusion_pytorch_model.safetensors"
        "models/controlnet/config.json"
    )
    
    for model in "${required_models[@]}"; do
        if [ ! -f "/app/$model" ]; then
            log "Warning: Required model file $model not found. Please ensure models are properly mounted."
            return 1
        else
            log "Model file $model found"
        fi
    done
}

# Function to check cache directory
check_cache() {
    log "Checking cache directory..."
    if [ ! -d "/app/cache" ]; then
        log "Creating cache directory..."
        mkdir -p /app/cache
        chown sduser:sduser /app/cache
    fi
    
    if [ ! -w "/app/cache" ]; then
        log "Warning: Cache directory is not writable. Model caching may not work properly."
        return 1
    fi
}

# Function to start the Stable Diffusion service
start_service() {
    log "Starting Stable Diffusion service..."
    
    # Activate virtual environment
    source /app/venv/bin/activate
    
    # Set Python path
    export PYTHONPATH="/app/src"
    
    # Start the FastAPI server
    exec python -m uvicorn src.main:app --host 0.0.0.0 --port 7860 --workers 1
}

# Main execution
log "Starting Stable Diffusion container initialization..."

# Check CUDA availability
check_cuda

# Check cache directory
check_cache

# Check required models
check_models

# Start the service
start_service
