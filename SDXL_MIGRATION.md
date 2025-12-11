# SDXL Migration Summary

## What Changed

### ✅ Completed Migration from SD 1.5 to SDXL

All code has been migrated from Stable Diffusion 1.5 to **SDXL (Stable Diffusion XL)** with **SD Forge** for native Layer Diffusion support.

### Files Updated

1. **`requirements.txt`**
   - Added SD Forge: `git+https://github.com/layerdiffusion/sd-forge-layerdiffuse.git`
   - Updated diffusers to `>=0.30.0` (SDXL compatible)

2. **`src/main.py`**
   - Changed from `StableDiffusionPipeline` → `StableDiffusionXLPipeline`
   - Integrated SD Forge pipelines (`ForgeStableDiffusionXLPipeline`)
   - Updated to SDXL ControlNet models
   - Updated default model: `Ragnarok_AI/Juggernaut-XL-v11`
   - Updated default guidance scale: `5.0` (SDXL uses 3-6)
   - Updated default steps: `30` (SDXL recommended)

3. **`src/utils/layer_diffusion.py`**
   - Complete rewrite to use SD Forge's native Layer Diffusion
   - Simplified API - SD Forge handles Layer Diffusion internally
   - Removed VAE loading logic (not needed with SD Forge)

4. **`src/api/cover_generation.py`**
   - Updated for SDXL pipeline
   - Updated default resolution: `1024x1024` (SDXL standard)
   - Updated default guidance scale: `5.0`
   - Simplified Layer Diffusion integration

5. **`src/api/border_generation.py`**
   - Updated for SDXL ControlNet
   - Updated default resolution: `1024x1024`
   - Updated default guidance scale: `5.0`

6. **`docker-compose.dev.yml`**
   - Updated `SD_MODEL_ID`: `Ragnarok_AI/Juggernaut-XL-v11`
   - Removed `TRANSPARENT_VAE_ID` (not needed with SD Forge)

7. **`download_models.sh`**
   - Updated to download SDXL models
   - Changed to Juggernaut XL v11
   - Updated ControlNet to SDXL version

8. **`STABLE_DIFFUSION_SETUP.md`**
   - Complete rewrite for SDXL
   - Updated requirements, settings, and troubleshooting

## What You Need to Do

### 🔴 CRITICAL: Rebuild Docker Image

The Docker image **MUST be rebuilt** because:
- New dependencies (SD Forge)
- Different model requirements
- Updated Python packages

```bash
# Stop the current container
docker compose -f docker-compose.dev.yml stop stable-diffusion

# Remove the old container and image
docker compose -f docker-compose.dev.yml rm -f stable-diffusion
docker rmi runarion-app-stable-diffusion  # Or whatever the image name is

# Rebuild with no cache (to ensure fresh dependencies)
docker compose -f docker-compose.dev.yml build --no-cache stable-diffusion

# Start the new container
docker compose -f docker-compose.dev.yml up -d stable-diffusion
```

### 📥 Download SDXL Models

SDXL models are **much larger** than SD 1.5:
- **SD 1.5:** ~4GB
- **SDXL (Juggernaut XL v11):** ~6.6GB
- **SDXL ControlNet:** ~1-2GB
- **Total:** ~10GB+ disk space needed

**Option 1: Automatic Download (Recommended)**
- Models will download automatically on first run
- Takes 15-30 minutes depending on connection
- Cached in `./runarion-stable-diffusion/cache/`

**Option 2: Manual Download**
1. Download Juggernaut XL v11 from CivitAI:
   - https://civitai.com/models/133005?modelVersionId=288982
   - Download the SafeTensor file (6.62 GB)
   - Extract to `./runarion-stable-diffusion/models/juggernaut-xl-v11/`

2. Download SDXL ControlNet (if using ControlNet):
   - Will download automatically from HuggingFace: `diffusers/controlnet-canny-sdxl-1.0`

### ⚙️ Update Environment Variables (Optional)

If you have a `.env` file or environment variables, update:
- `SD_MODEL_ID=Ragnarok_AI/Juggernaut-XL-v11` (or local path)
- Remove `TRANSPARENT_VAE_ID` (not needed)

### 🧪 Test the Migration

1. **Check health:**
   ```bash
   curl http://localhost:7860/health
   ```
   Should return `"model_type": "SDXL"`

2. **Test generation:**
   ```bash
   curl -X POST http://localhost:7860/api/generate-cover \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "a beautiful fantasy landscape",
       "width": 1024,
       "height": 1024,
       "num_inference_steps": 30,
       "guidance_scale": 5.0
     }' \
     --output test_sdxl.png
   ```

3. **Test Layer Diffusion:**
   ```bash
   curl -X POST http://localhost:7860/api/generate-cover \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "a fantasy character portrait",
       "width": 832,
       "height": 1216,
       "transparent_background": true
     }' \
     --output test_transparent.png
   ```

## Key Differences from SD 1.5

### Performance
- **Slower:** SDXL takes 30-60 seconds per image (vs 10-20s for SD 1.5)
- **More VRAM:** Requires 8-12GB VRAM (vs 4-6GB for SD 1.5)
- **Better Quality:** Significantly higher quality output

### Settings
- **Resolution:** Default 1024×1024 (vs 512×512 for SD 1.5)
- **CFG Scale:** 3-6 (vs 7.5 for SD 1.5)
- **Steps:** 30-40 recommended (vs 20 for SD 1.5)

### Layer Diffusion
- **Native Support:** SD Forge provides native Layer Diffusion (no VAE swapping)
- **Better Quality:** True native transparency (vs post-processing)
- **ControlNet Compatible:** Works with ControlNet for consistent transparent images

## Troubleshooting

### "SD Forge not found" Error
- Ensure `requirements.txt` includes SD Forge
- Rebuild Docker image with `--no-cache`
- Check logs: `docker compose logs stable-diffusion`

### Out of Memory
- Reduce resolution to 832×1216 or lower
- Ensure you have 8GB+ VRAM
- Enable all optimizations (already enabled by default)

### Models Not Loading
- Check disk space (need ~10GB+)
- Check internet connection (for HuggingFace downloads)
- Check logs for specific errors

### Layer Diffusion Not Working
- Check logs for SD Forge initialization
- Falls back to post-processing if Layer Diffusion fails
- Verify SD Forge is installed correctly

## Next Steps

1. ✅ **Rebuild Docker image** (REQUIRED)
2. ✅ **Download/verify SDXL models**
3. ✅ **Test basic generation**
4. ✅ **Test Layer Diffusion**
5. ✅ **Test ControlNet borders**
6. ✅ **Update frontend if needed** (default resolution changed)

## Rollback (If Needed)

If you need to rollback to SD 1.5:
1. Revert git changes
2. Rebuild Docker image
3. Download SD 1.5 models again

But SDXL is much better, so you probably won't want to! 🚀

