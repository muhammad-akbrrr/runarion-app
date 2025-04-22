#!/bin/bash

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

# Function to check if huggingface-cli is installed
check_huggingface_cli() {
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    
    if ! command -v huggingface-cli &> /dev/null; then
        echo "Error: huggingface-cli is not installed in the virtual environment."
        echo "Please install it using: pip install huggingface_hub"
        exit 1
    fi
}

# Function to create directories
create_directories() {
    echo "Creating model directories..."
    mkdir -p "$MODELS_DIR/stable-diffusion-v1-5"
    mkdir -p "$MODELS_DIR/controlnet"
}

# Function to download Stable Diffusion model
download_sd_model() {
    echo "Downloading Stable Diffusion v1.5 model (Forge compatible)..."
    huggingface-cli download --resume-download --local-dir "$MODELS_DIR/stable-diffusion-v1-5" runwayml/stable-diffusion-v1-5
}

# Function to download ControlNet model
download_controlnet_model() {
    echo "Downloading ControlNet model (Forge compatible)..."
    # Download the canny model which is most commonly used
    huggingface-cli download --resume-download --local-dir "$MODELS_DIR/controlnet" lllyasviel/control_v11p_sd15_canny --include "diffusion_pytorch_model.bin" "config.json"
}

# Function to verify downloads
verify_downloads() {
    echo "Verifying model downloads..."
    
    # Check Stable Diffusion model
    if [ ! -f "$MODELS_DIR/stable-diffusion-v1-5/model_index.json" ]; then
        echo "Error: Stable Diffusion model download failed or is incomplete."
        exit 1
    fi
    
    # Check ControlNet model
    if [ ! -f "$MODELS_DIR/controlnet/diffusion_pytorch_model.bin" ] || [ ! -f "$MODELS_DIR/controlnet/config.json" ]; then
        echo "Error: ControlNet model download failed or is incomplete."
        echo "Expected files:"
        echo "- $MODELS_DIR/controlnet/diffusion_pytorch_model.bin"
        echo "- $MODELS_DIR/controlnet/config.json"
        echo "Found files:"
        ls -la "$MODELS_DIR/controlnet/"
        exit 1
    fi
    
    echo "All models downloaded and verified successfully!"
}

# Main execution
echo "Starting model download process..."

# Check prerequisites
check_huggingface_cli

# Create directories
create_directories

# Download models
download_sd_model
download_controlnet_model

# Verify downloads
verify_downloads

echo "Models have been downloaded to:"
echo "- Stable Diffusion: $MODELS_DIR/stable-diffusion-v1-5"
echo "- ControlNet: $MODELS_DIR/controlnet" 