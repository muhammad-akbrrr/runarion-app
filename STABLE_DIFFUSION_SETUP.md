# Stable Diffusion XL (SDXL) Service Setup Guide

## Overview

The Stable Diffusion service now uses **SDXL (Stable Diffusion XL)** with **SD Forge** for native Layer Diffusion support. This provides:
- Higher quality image generation (1024x1024+ resolution)
- Native transparent background support via Layer Diffusion
- ControlNet support for consistent transparent images
- Better photorealism and detail

## Quick Start

### 1. Start the Service

From the project root:

```bash
docker compose -f docker-compose.dev.yml up -d stable-diffusion
```

**Important:** The Docker image needs to be rebuilt for SDXL:
```bash
docker compose -f docker-compose.dev.yml build stable-diffusion
docker compose -f docker-compose.dev.yml up -d stable-diffusion
```

### 2. Check Service Status

```bash
# Check if the service is running
docker compose -f docker-compose.dev.yml ps stable-diffusion

# Check logs
docker compose -f docker-compose.dev.yml logs -f stable-diffusion

# Check health endpoint
curl http://localhost:7860/health
```

### 3. First Run

On first run, the service will:
- Download the **Juggernaut XL v11** SDXL model from HuggingFace (if not present locally)
- This can take **15-30 minutes** depending on your internet connection (model is ~6.6GB)
- Models are cached in `./runarion-stable-diffusion/cache/`

## Configuration

### Environment Variables

The service is configured via environment variables in `docker-compose.dev.yml`. Key settings:

- `USE_CONTROLNET=true` - ControlNet enabled by default for border generation
- `USE_CUDA=true` - Use GPU if available (falls back to CPU)
- `ALLOW_HF_DOWNLOAD=true` - Allow downloading models from HuggingFace
- `SD_MODEL_ID=Ragnarok_AI/Juggernaut-XL-v11` - SDXL model to use (Juggernaut XL v11)

### GPU Requirements

**With GPU (Required for reasonable performance):**
- NVIDIA GPU with CUDA support
- **Minimum 8GB VRAM** (12GB+ recommended for SDXL)
- NVIDIA Container Toolkit installed
- SDXL is much more memory-intensive than SD 1.5

**Without GPU (CPU mode):**
- Works but will be **very slow** (15-30 minutes per image)
- **Not recommended** for production use
- May require significant RAM (16GB+)

## Model Management

### Local Models

If you want to use local models instead of downloading:

1. **Download Juggernaut XL v11 from CivitAI:**
   - Visit: https://civitai.com/models/133005?modelVersionId=288982
   - Download the model (6.62 GB SafeTensor file)
   - Extract to `./runarion-stable-diffusion/models/juggernaut-xl-v11/`

2. **Or use the download script:**
   ```bash
   cd runarion-stable-diffusion
   ./download_models.sh
   ```

3. Models will be stored in `./runarion-stable-diffusion/models/`

4. Set `ALLOW_HF_DOWNLOAD=false` in docker-compose to use only local models

### Model Cache

Models are cached in `./runarion-stable-diffusion/cache/` to speed up subsequent starts.

## SDXL Features

### Layer Diffusion (Transparent Backgrounds)

SD Forge provides **native Layer Diffusion support** for transparent backgrounds:
- Enable `transparent_background: true` in generation requests
- No post-processing needed - true native transparency
- Works with ControlNet for consistent transparent images

### Recommended Settings (Juggernaut XL v11)

Based on the model's recommended settings:

- **Resolution:** 832×1216 (portrait) or 1024×1024 (square)
- **Sampler:** DPM++ 2M SDE (default)
- **Steps:** 30-40
- **CFG Scale:** 3-6 (lower = more realistic)
- **VAE:** Baked in (no separate VAE needed)

### High-Resolution Upscaling

SDXL supports native upscaling. For high-res output:
- Generate at base resolution (1024×1024)
- Use upscaling pipeline for final output
- Or generate directly at higher resolutions (may require more VRAM)

## Testing

### Test Image Generation

```bash
# Generate a test image
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful fantasy landscape with mountains and a lake",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "transparent_background": false
  }' \
  --output test_cover.png
```

### Test Transparent Background

```bash
# Generate with transparent background (Layer Diffusion)
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a fantasy character portrait",
    "width": 832,
    "height": 1216,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "transparent_background": true
  }' \
  --output test_transparent.png
```

### Test from Frontend

1. Open your project in the editor
2. Go to the "Book Preview - Image & PDF Generator" tab
3. Select a chapter
4. Enter a prompt
5. Toggle "Transparent Background" if desired
6. Click "Generate Cover"

## Troubleshooting

### Service Won't Start

1. **Check logs:**
   ```bash
   docker compose -f docker-compose.dev.yml logs stable-diffusion
   ```

2. **Check GPU availability:**
   ```bash
   nvidia-smi
   ```

3. **Rebuild Docker image:**
   ```bash
   docker compose -f docker-compose.dev.yml build --no-cache stable-diffusion
   ```

### Out of Memory (OOM)

SDXL requires significantly more VRAM than SD 1.5:

- **Reduce image size:** Use 832×1216 instead of 1024×1024
- **Enable optimizations:** Already enabled by default (attention slicing, VAE tiling)
- **Use CPU offload:** Already enabled by default
- **Reduce batch size:** Generate one image at a time

### Models Not Downloading

1. **Check internet connection** - Models are downloaded from HuggingFace
2. **Check disk space** - SDXL models require **~10GB+** (vs ~4GB for SD 1.5)
3. **Check permissions** - Ensure cache directory is writable
4. **Manual download:** Download Juggernaut XL v11 from CivitAI if HuggingFace fails

### Slow Generation

- **GPU mode:** Check GPU utilization with `nvidia-smi`
- **CPU mode:** This is expected - CPU generation is very slow (15-30 min per image)
- **Reduce steps:** Lower `NUM_INFERENCE_STEPS` (default: 30, minimum: 20)
- **Lower resolution:** Use 832×1216 instead of 1024×1024

### Layer Diffusion Not Working

1. **Check logs** for Layer Diffusion initialization errors
2. **Verify SD Forge is installed:** Check requirements.txt includes SD Forge
3. **Check pipeline type:** Ensure using `ForgeStableDiffusionXLPipeline`
4. **Fallback:** Post-processing transparency will be used if Layer Diffusion fails

## Integration

The service is automatically integrated with:
- **Python Service:** Calls SD service at `http://stable-diffusion:7860` (Docker) or `http://localhost:7860` (local)
- **Laravel Frontend:** Uses the Python service as a proxy

## Migration from SD 1.5

If you were using SD 1.5 before:

1. **Rebuild Docker image** (required for SDXL dependencies)
2. **Download SDXL models** (larger than SD 1.5)
3. **Update API calls** - Default resolution changed to 1024×1024
4. **Update guidance scale** - SDXL uses lower CFG (3-6 vs 7.5 for SD 1.5)

## Next Steps

1. **Generate chapter covers** from the frontend with SDXL quality
2. **Use transparent backgrounds** with native Layer Diffusion support
3. **Generate borders** with ControlNet for consistent transparent designs
4. **Customize prompts** for better SDXL results
5. **Experiment with resolutions** - SDXL supports various aspect ratios

## Performance Notes

- **First generation:** May take 1-2 minutes (model loading)
- **Subsequent generations:** 30-60 seconds per image (GPU)
- **Memory usage:** ~8-12GB VRAM for 1024×1024 images
- **CPU generation:** 15-30 minutes per image (not recommended)
