#!/bin/bash

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

# Function to detect the operating system
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

# Function to get the virtual environment activation script path
get_venv_activate_path() {
    local os=$(detect_os)
    if [ "$os" = "windows" ]; then
        echo "$SCRIPT_DIR/venv/Scripts/activate"
    else
        echo "$SCRIPT_DIR/venv/bin/activate"
    fi
}

# Function to check if huggingface-cli is installed
check_huggingface_cli() {
    local venv_activate=$(get_venv_activate_path)
    
    # Activate virtual environment
    if [ -f "$venv_activate" ]; then
        source "$venv_activate"
    else
        echo "Error: Virtual environment activation script not found at $venv_activate"
        exit 1
    fi
    
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
    huggingface-cli download --resume-download --local-dir "$MODELS_DIR/stable-diffusion-v1-5" \
        runwayml/stable-diffusion-v1-5 \
        --include "*.safetensors" "*.json" "*.txt" "*.yaml" "*.ckpt" \
        --exclude "*.bin" "*.pt" "*.pth"
    
    # Ensure the model is in the correct format for Forge
    if [ ! -f "$MODELS_DIR/stable-diffusion-v1-5/v1-5-pruned.safetensors" ]; then
        echo "Converting model to Forge format..."
        huggingface-cli download --resume-download --local-dir "$MODELS_DIR/stable-diffusion-v1-5" \
            runwayml/stable-diffusion-v1-5 \
            --include "v1-5-pruned.safetensors"
    fi
}

# Function to download ControlNet model
download_controlnet_model() {
    echo "Downloading ControlNet model (Forge compatible)..."
    # Download the canny model which is most commonly used
    huggingface-cli download --resume-download --local-dir "$MODELS_DIR/controlnet" \
        lllyasviel/control_v11p_sd15_canny \
        --include "*.safetensors" "*.json" "*.txt" "*.yaml" \
        --exclude "*.bin" "*.pt" "*.pth"
    
    # Ensure the model is in the correct format for Forge
    if [ ! -f "$MODELS_DIR/controlnet/diffusion_pytorch_model.safetensors" ]; then
        echo "Converting ControlNet model to Forge format..."
        huggingface-cli download --resume-download --local-dir "$MODELS_DIR/controlnet" \
            lllyasviel/control_v11p_sd15_canny \
            --include "diffusion_pytorch_model.safetensors"
    fi
}

# Function to verify downloads
verify_downloads() {
    echo "Verifying model downloads..."
    
    # Check Stable Diffusion model
    local sd_required_files=(
        "model_index.json"
        "v1-5-pruned.safetensors"
        "v1-inference.yaml"
        "scheduler/scheduler_config.json"
    )
    
    # Check required subdirectories
    local sd_required_dirs=(
        "unet"
        "vae"
        "text_encoder"
        "tokenizer"
        "scheduler"
    )
    
    for file in "${sd_required_files[@]}"; do
        if [ ! -f "$MODELS_DIR/stable-diffusion-v1-5/$file" ]; then
            echo "Error: Stable Diffusion model download failed or is incomplete."
            echo "Missing required file: $file"
            echo "Found files:"
            ls -la "$MODELS_DIR/stable-diffusion-v1-5/"
            exit 1
        fi
    done
    
    for dir in "${sd_required_dirs[@]}"; do
        if [ ! -d "$MODELS_DIR/stable-diffusion-v1-5/$dir" ]; then
            echo "Error: Stable Diffusion model structure is incomplete."
            echo "Missing required directory: $dir"
            echo "Found directories:"
            ls -la "$MODELS_DIR/stable-diffusion-v1-5/"
            exit 1
        fi
    done
    
    # Verify model type and version
    if ! grep -q "\"_class_name\": \"StableDiffusionPipeline\"" "$MODELS_DIR/stable-diffusion-v1-5/model_index.json"; then
        echo "Error: Incorrect model type in model_index.json"
        echo "Expected: StableDiffusionPipeline"
        echo "Found:"
        grep "_class_name" "$MODELS_DIR/stable-diffusion-v1-5/model_index.json"
        exit 1
    fi
    
    # Check ControlNet model
    local cn_required_files=(
        "config.json"
        "diffusion_pytorch_model.safetensors"
        "diffusion_pytorch_model.fp16.safetensors"
    )
    
    for file in "${cn_required_files[@]}"; do
        if [ ! -f "$MODELS_DIR/controlnet/$file" ]; then
            echo "Error: ControlNet model download failed or is incomplete."
            echo "Missing required file: $file"
            echo "Found files:"
            ls -la "$MODELS_DIR/controlnet/"
            exit 1
        fi
    done
    
    # Verify ControlNet model type
    if ! grep -q "\"_class_name\": \"ControlNetModel\"" "$MODELS_DIR/controlnet/config.json"; then
        echo "Error: Incorrect ControlNet model type in config.json"
        echo "Expected: ControlNetModel"
        echo "Found:"
        grep "_class_name" "$MODELS_DIR/controlnet/config.json"
        exit 1
    fi
    
    echo "All models downloaded and verified successfully!"
    echo "Model structure matches Forge requirements."
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