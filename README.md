# Runarion - AI-Powered Novel Generation Pipeline

A revolutionary AI-powered novel generation and enhancement pipeline that transforms basic story concepts into professionally formatted, illustrated books.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Initial Setup](#initial-setup)
  - [Laravel Setup](#laravel-setup)
  - [Python Setup](#python-setup)
  - [Stable Diffusion Setup](#stable-diffusion-setup)
- [Development](#development)
  - [Docker Development](#docker-development)
  - [Port Management](#port-management)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Directory-specific Documentation

1. [Laravel Documentation](./runarion-laravel/README.md)
2. [Python Documentation](./runarion-python/README.md)
3. [Stable Diffusion Documentation](./runarion-stable-diffusion/README.md)

## Overview

Runarion is a comprehensive five-phase pipeline that revolutionizes the book creation process:

1. Initial Story Generation
2. Style Building
3. Novel Writing
4. Relationship Analysis
5. PDF Enhancement

## Features

- AI-powered story generation
- Style customization and building
- Automated novel writing pipeline
- Character relationship analysis
- Professional PDF formatting and enhancement
- Integrated illustration generation with Stable Diffusion
- ControlNet-based image generation for consistent style

## Cross-Platform Compatibility

This project is designed to work on both Linux and Windows. For Windows users:

1. Use Git Bash, WSL with Docker Desktop
2. Ensure line endings are properly handled:
   - Git will handle this automatically thanks to .gitattributes
   - If issues occur, run `dos2unix .env` and other script files (already done for the dev scripts)
3. Environment variables are loaded from .env file:
   - Copy .env.example to .env
   - Update values as needed (namely db password)
   - The dev.sh script will handle loading them properly

## Prerequisites

- Docker Engine
- Node.js (v20 or higher)
- PHP 8.4
- Composer
- Python 3.12
- PostgreSQL 17
- Git
- Git Bash
- NVIDIA GPU with CUDA support (required for Stable Diffusion)
- NVIDIA Container Toolkit (nvidia-docker2)
- 8GB GPU VRAM (recommended for Stable Diffusion)

### Windows-Specific Requirements

This project supports development on both Linux and Windows. The development scripts automatically convert entry scripts to Unix format using `dos2unix`.

Before building the application container on Windows:

1. Install `dos2unix` globally by running the following command in an administrator terminal (CMD or PowerShell):

```bash
choco install dos2unix
```

2. Once installed, you'll be able to run the Docker container on both Linux and Windows operating systems.

### NVIDIA GPU Requirements

The Stable Diffusion container requires NVIDIA GPU support. Before proceeding:

1. Ensure you have an NVIDIA GPU with CUDA support
2. Install the latest NVIDIA drivers
3. Install NVIDIA Container Toolkit:

**Linux:**

```bash
# Add NVIDIA package repositories
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**Windows:**

1. Install Docker Desktop
2. Enable WSL 2
3. Install a Linux distro in your WSL environment
4. Enable the distro in the "Resources" tab under WSL Integration in your Docker Desktop
5. Access your Linux Distro of choice
6. Install NVIDIA CUDA Toolkit
7. Install NVIDIA Container Toolkit for WSL 2

## Installation

### Initial Setup

1. Clone the repository:

```bash
git clone https://github.com/muhammad-akbrrr/runarion-app.git
cd runarion-app
```

2. Create necessary .env files:
   - Copy `.env.example` to `.env` in the root directory `cp ./.env.example .env` (make sure you run this in the current directory you wanna copy the env files to).
   - Copy `.env.example` to `.env` in `runarion-laravel`, `runarion-python`, and `runarion-stable-diffusion` directories

### Laravel Setup

```bash
# Navigate to Laravel project
cd runarion-laravel

# Install PHP dependencies
composer install

# Install Node.js dependencies
npm install

# Generate application key
php artisan key:generate

# Return to root directory
cd ..
```

### Python Setup

```bash
# Navigate to Python project
cd runarion-python

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

# Deactivate virtual environment when done
deactivate

# Return to root directory
cd ..
```

### Stable Diffusion Setup

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

## Development

### Docker Development

The project uses Docker for development to ensure consistency across environments.

Before we proceed with running any entry scripts, we must make sure we have nvidia runtime configured in our docker engine:

**Linux:**

```bash
# Verify NVIDIA Container Toolkit installation
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

**Windows:**

1. Access your preferred Linux distro through WSL:
   ```bash
   wsl -d <your-distro-name>
   ```
2. Verify NVIDIA Container Toolkit installation:
   ```bash
   nvidia-smi
   ```
3. Test Docker GPU access:
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
   ```

Then start the development environment:

```bash
# Start development environment
./dev.sh

# Rebuild containers (when needed)
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build -d

# Quick restart
docker compose -f docker-compose.dev.yml restart

# Cleanup and restart
./dev.sh cleanup
./dev.sh
```

### Port Management

The application uses the following ports:

- Laravel: 8000
- Python: 5000
- PostgreSQL: 5432
- Vite: 5173
- Stable Diffusion: 7860

To manage port conflicts:

**Windows:**

```bash
# Check port usage
netstat -ano | findstr :<PORT_NUMBER>

# Kill process using port
taskkill /PID <PID> /F
```

**Linux:**

```bash
# Check port usage
sudo lsof -i :<PORT_NUMBER>

# Kill process using port
sudo kill <PID>
```

## Architecture

The application is split into four main components:

- Laravel Application (`runarion-laravel`): Handles web interface, authentication, and database operations
- Python Service (`runarion-python`): Manages AI processing and novel generation pipeline
- Stable Diffusion Service (`runarion-stable-diffusion`): Locally hosted AI model for image generation
- Database Service (PostgreSQL): A commonly shared database between the python service and the laravel service

## Configuration

- Database configuration is managed through Laravel's `.env` file
- AI settings can be adjusted in the Python service's configuration
- Docker settings are defined in `docker-compose.dev.yml`
- Environment-specific settings should be configured in respective `.env` files
- Stable Diffusion settings can be configured in `runarion-stable-diffusion/.env`

Key configuration files:

- `.env` files (root, Laravel, Python, and Stable-Diffusion directories)
- `config/app.php` (Laravel configuration)
- `docker-compose.dev.yml` (Docker configuration)
- `runarion-stable-diffusion/src/main.py` (Stable Diffusion API configuration)

## Troubleshooting

Common issues and solutions:

1. **Port Conflicts**

   - Use the port management commands above to identify and resolve conflicts
   - Check if other applications are using required ports

2. **Docker Issues**

   - Ensure Docker Engine is running
   - Try rebuilding containers using `./dev.sh cleanup && ./dev.sh`
   - Check Docker logs for specific error messages

3. **Permission Issues**

   - Ensure proper file permissions in mounted volumes
   - Check user permissions in Docker containers

4. **Database Connection Issues**

   - Verify PostgreSQL password in `.env` files
   - Ensure database service is running
   - Check network connectivity between containers

5. **Stable Diffusion Issues**

   - Verify NVIDIA GPU is properly detected: `nvidia-smi`
   - Check NVIDIA Container Toolkit installation
   - Ensure sufficient GPU memory (8GB recommended)
   - Verify model files are properly downloaded
   - Check container logs for specific error messages
   - Ensure proper CUDA version compatibility

6. **Model Download Issues**
   - Check internet connectivity
   - Verify Hugging Face credentials if using private models
   - Ensure sufficient disk space for model files
   - Try running `./download_models.sh` multiple times if download fails
