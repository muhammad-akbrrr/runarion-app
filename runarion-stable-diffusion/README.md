# Runarion Stable Diffusion Service

## Overview

The Stable Diffusion service component of Runarion provides AI-powered image generation capabilities for the novel generation pipeline. This service integrates Stable Diffusion v1.5 with ControlNet for consistent style generation and high-quality illustrations.

## Features

- Stable Diffusion v1.5 model integration
- ControlNet support for style consistency
- GPU-accelerated inference
- Model caching for improved performance
- Health monitoring and automatic recovery
- Docker containerization with NVIDIA support
- FastAPI-based REST API

## Directory Structure

```
runarion-stable-diffusion/
├── src/
│   ├── main.py           # FastAPI application and model initialization
│   └── utils/            # Utility functions and helpers
├── models/               # Model storage directory
│   ├── stable-diffusion-v1-5/
│   └── controlnet/
├── outputs/             # Generated image storage
├── inputs/              # Input image storage
├── cache/               # Model cache directory
├── venv/                # Python virtual environment
├── dockerfile           # Docker container definition
├── docker-entrypoint.sh # Container entrypoint script
├── download_models.sh   # Model download script
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration
```

## Prerequisites

- NVIDIA GPU with CUDA support
- Minimum 8GB GPU VRAM (recommended)
- Docker with NVIDIA Container Toolkit
- Python 3.12
- Virtual environment management tool (venv)

## Setup and Installation

### Local Development Setup

```bash
# Navigate to Stable Diffusion project
cd runarion-stable-diffusion

# For Windows:
python -m venv venv --clear
venv\Scripts\activate  # For CMD
# OR
source venv/Scripts/activate  # For Git Bash

# For Linux/macOS:
python3 -m venv venv --clear
source venv/bin/activate

# Install dependencies
python -m pip install --no-cache-dir -r requirements.txt

# Download models locally (might take multiple runs)
./download_models.sh

# Deactivate virtual environment when done
deactivate

# Return to root directory
cd ..
```

### Docker Setup

The service is designed to run in a Docker container with NVIDIA GPU support. The container is managed through the main project's Docker Compose configuration.

To build and run the container:

```bash
# From the root directory
docker compose -f docker-compose.dev.yml up -d stable-diffusion
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```
# Model Configuration
MODELS_DIR=/app/models
CONTROLNET_MODEL_PATH=controlnet
STABLE_DIFFUSION_MODEL_PATH=stable-diffusion-v1-5
USE_SAFETENSORS=true
ENABLE_MODEL_CACHING=true
CACHE_DIR=/app/cache

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5000

# Generation Parameters
NUM_INFERENCE_STEPS=20
GUIDANCE_SCALE=7.5

# GPU Configuration
USE_CUDA=true
ENABLE_XFORMERS=true
ENABLE_SEQUENTIAL_CPU_OFFLOAD=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_TILING=true
ENABLE_GRADIENT_CHECKPOINTING=true
```

## API Endpoints

### Image Generation

- `GET /generate` - Generate an image from a text prompt
  - Query Parameters:
    - `prompt` (string): Text description of the image to generate
  - Returns: PNG image

### Health Check

- `GET /health` - Check service health status
  - Returns: JSON with service status

## Model Management

### Downloading Models

The `download_models.sh` script handles model downloads:

```bash
./download_models.sh
```

This script:

1. Downloads Stable Diffusion v1.5 model
2. Downloads ControlNet model
3. Verifies model integrity
4. Sets up required model structure

### Model Caching

The service supports model caching to improve performance:

- Models are cached in the `cache/` directory
- Caching can be enabled/disabled via `ENABLE_MODEL_CACHING`
- Cache directory is configurable via `CACHE_DIR`

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 guidelines. Run linting with:

```bash
flake8 .
```

### Adding New Models

1. Add model files to appropriate directory in `models/`
2. Update model paths in `.env`
3. Restart the service

## Troubleshooting

### Common Issues

1. **GPU Detection Issues**

   - Verify NVIDIA drivers are installed
   - Check `nvidia-smi` output
   - Ensure NVIDIA Container Toolkit is properly configured

2. **Model Loading Errors**

   - Verify model files are present
   - Check model directory permissions
   - Ensure sufficient GPU memory

3. **Generation Quality Issues**

   - Adjust `NUM_INFERENCE_STEPS` and `GUIDANCE_SCALE`
   - Check prompt quality
   - Verify model version compatibility

4. **Performance Issues**

   - Enable/disable GPU optimizations in `.env`
   - Monitor GPU memory usage
   - Check for system resource constraints

5. **Docker Issues**
   - Verify NVIDIA runtime is available
   - Check container logs
   - Ensure proper volume mounts

## Security

- CORS protection is enabled
- Input validation for prompts
- Resource limits on generation
- Container security best practices

## License

This project is licensed under the MIT License. See `LICENSE` for details.
