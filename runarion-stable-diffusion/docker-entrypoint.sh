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
    log "Checking for local SDXL models..."
    local sd_model_path="/app/models/juggernaut-xl-v11"
    local cn_model_path="/app/models/controlnet-sdxl"
    
    # Check SDXL model
    if [ -d "$sd_model_path" ] && [ -f "$sd_model_path/model_index.json" ]; then
        log "SDXL model found locally at $sd_model_path"
    else
        log "SDXL model not found locally. Will download from HuggingFace on first use."
        log "Note: SDXL models are large (~6.6GB). Download may take 15-30 minutes."
    fi
    
    # Check ControlNet model (optional)
    if [ "$USE_CONTROLNET" = "true" ]; then
        if [ -d "$cn_model_path" ] && [ -f "$cn_model_path/config.json" ]; then
            log "SDXL ControlNet model found locally at $cn_model_path"
        else
            log "SDXL ControlNet model not found locally. Will download from HuggingFace on first use."
        fi
    else
        log "ControlNet is disabled (USE_CONTROLNET=false)"
    fi
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

# Check for models (non-blocking, models can be downloaded on first use)
check_models || log "Model check completed with warnings, continuing..."

# Start the service
start_service
