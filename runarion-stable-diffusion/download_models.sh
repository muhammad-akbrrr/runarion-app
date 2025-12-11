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
    mkdir -p "$MODELS_DIR/juggernaut-xl-v11"
    mkdir -p "$MODELS_DIR/controlnet-sdxl"
}

# Function to download SDXL model (Juggernaut XL v11)
download_sdxl_model() {
    echo "Downloading Juggernaut XL v11 (SDXL) model..."
    echo "Note: This model is large (~6.6GB). Download may take 10-30 minutes depending on connection."
    
    # Try to download from HuggingFace if available
    # If not, user will need to download from CivitAI manually
    if huggingface-cli repo exists Ragnarok_AI/Juggernaut-XL-v11 2>/dev/null; then
        huggingface-cli download --resume-download --local-dir "$MODELS_DIR/juggernaut-xl-v11" \
            Ragnarok_AI/Juggernaut-XL-v11 \
            --include "*.safetensors" "*.json" "*.txt" "*.yaml" \
            --exclude "*.bin" "*.pt" "*.pth"
    else
        echo "Warning: Juggernaut XL v11 not found on HuggingFace."
        echo "Please download manually from: https://civitai.com/models/133005?modelVersionId=288982"
        echo "Place the model files in: $MODELS_DIR/juggernaut-xl-v11"
        echo ""
        echo "Alternatively, using base SDXL model..."
        huggingface-cli download --resume-download --local-dir "$MODELS_DIR/juggernaut-xl-v11" \
            stabilityai/stable-diffusion-xl-base-1.0 \
            --include "*.safetensors" "*.json" "*.txt" "*.yaml" \
            --exclude "*.bin" "*.pt" "*.pth"
    fi
}

# Function to download SDXL ControlNet model
download_controlnet_model() {
    echo "Downloading SDXL ControlNet model (Canny)..."
    huggingface-cli download --resume-download --local-dir "$MODELS_DIR/controlnet-sdxl" \
        diffusers/controlnet-canny-sdxl-1.0 \
        --include "*.safetensors" "*.json" "*.txt" "*.yaml" \
        --exclude "*.bin" "*.pt" "*.pth"
}

# Function to verify downloads
verify_downloads() {
    echo "Verifying model downloads..."
    
    # Check SDXL model
    local sdxl_required_files=(
        "model_index.json"
    )
    
    # Check required subdirectories for SDXL
    local sdxl_required_dirs=(
        "unet"
        "vae"
        "text_encoder"
        "text_encoder_2"
        "tokenizer"
        "tokenizer_2"
        "scheduler"
    )
    
    for file in "${sdxl_required_files[@]}"; do
        if [ ! -f "$MODELS_DIR/juggernaut-xl-v11/$file" ]; then
            echo "Warning: SDXL model download may be incomplete."
            echo "Missing file: $file"
            echo "This is OK if you're using a manually downloaded model."
        fi
    done
    
    # Verify model type (SDXL)
    if [ -f "$MODELS_DIR/juggernaut-xl-v11/model_index.json" ]; then
        if ! grep -q "StableDiffusionXLPipeline" "$MODELS_DIR/juggernaut-xl-v11/model_index.json"; then
            echo "Warning: Model type may not be SDXL"
            echo "Found:"
            grep "_class_name" "$MODELS_DIR/juggernaut-xl-v11/model_index.json" || echo "No _class_name found"
        fi
    fi
    
    # Check ControlNet model
    if [ -f "$MODELS_DIR/controlnet-sdxl/config.json" ]; then
        if ! grep -q "ControlNetModel" "$MODELS_DIR/controlnet-sdxl/config.json"; then
            echo "Warning: ControlNet model type may be incorrect"
        fi
    fi
    
    echo "Model verification complete!"
    echo "Note: SDXL models are large. Ensure you have sufficient disk space (~10GB+)."
}

# Main execution
echo "Starting SDXL model download process..."
echo "This will download Juggernaut XL v11 (SDXL) and SDXL ControlNet models."
echo ""

# Check prerequisites
check_huggingface_cli

# Create directories
create_directories

# Download models
download_sdxl_model
download_controlnet_model

# Verify downloads
verify_downloads

echo ""
echo "Models have been downloaded to:"
echo "- SDXL Model: $MODELS_DIR/juggernaut-xl-v11"
echo "- SDXL ControlNet: $MODELS_DIR/controlnet-sdxl"
echo ""
echo "Note: If Juggernaut XL v11 wasn't found on HuggingFace, you may need to:"
echo "1. Download from CivitAI: https://civitai.com/models/133005?modelVersionId=288982"
echo "2. Extract and place files in: $MODELS_DIR/juggernaut-xl-v11"
