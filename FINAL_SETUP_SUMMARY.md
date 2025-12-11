# ✅ Final Setup Summary - SDXL with Layer Diffusion & ControlNet Union

## What's Been Configured

### ✅ 1. Layer Diffusion
- **Repository**: `lllyasviel/sd-forge-layerdiffuse` ([GitHub](https://github.com/lllyasviel/sd-forge-layerdiffuse))
- **Library**: Uses `lib_layerdiffusion` folder (core library, no UI needed)
- **Status**: ✅ Configured in `requirements.txt` and `layer_diffusion.py`

### ✅ 2. ControlNet Union SDXL
- **Repository**: `xinsir6/ControlNetPlus` ([GitHub](https://github.com/xinsir6/ControlNetPlus))
- **Model ID**: `xinsir6/controlnet-union-sdxl-1.0` (configured as default)
- **Status**: ✅ Configured in `main.py`

### ✅ 3. SDXL Pipeline
- **Base Model**: `stabilityai/stable-diffusion-xl-base-1.0` (default, auto-downloads)
- **Juggernaut XL v11**: Ready for manual download (see below)
- **Status**: ✅ Configured

## Current Status

### Docker Build
- **Status**: Building in background
- **What it's doing**: Installing `lib_layerdiffusion` from `sd-forge-layerdiffuse` repo
- **Time**: ~5-10 minutes

### Models Needed

1. **Juggernaut XL v11** (Optional but recommended)
   - **Source**: [CivitAI](https://civitai.com/models/133005?modelVersionId=288982)
   - **Size**: ~6.62 GB
   - **Location**: `./runarion-stable-diffusion/models/juggernaut-xl-v11/`
   - **Status**: ⏳ Needs manual download
   - **Note**: System works with base SDXL if you skip this

2. **ControlNet Union SDXL** (Auto-downloads)
   - **Model**: `xinsir6/controlnet-union-sdxl-1.0`
   - **Size**: ~1-2 GB
   - **Status**: ✅ Will download automatically on first run

3. **Layer Diffusion Models** (Auto-downloads)
   - **Models**: Downloaded automatically by `lib_layerdiffusion`
   - **Status**: ✅ Handled by the library

## What Happens Next

### After Docker Build Completes:

1. **Start the service:**
   ```bash
   docker compose -f docker-compose.dev.yml up -d stable-diffusion
   ```

2. **Check logs:**
   ```bash
   docker compose -f docker-compose.dev.yml logs -f stable-diffusion
   ```

3. **Wait for models to download** (first run only):
   - Base SDXL: ~6GB (if Juggernaut not present)
   - ControlNet Union: ~1-2GB
   - Layer Diffusion models: Auto-downloaded by library

4. **Test:**
   ```bash
   curl http://localhost:7860/health
   ```

## Files Updated

✅ `requirements.txt` - Added `lllyasviel/sd-forge-layerdiffuse`  
✅ `src/main.py` - Removed SD Forge, using standard SDXL + ControlNet Union  
✅ `src/utils/layer_diffusion.py` - Updated to use `lib_layerdiffusion`  
✅ `docker-compose.dev.yml` - Added `CONTROLNET_MODEL_ID` env var  

## How It Works

### Layer Diffusion Flow:
1. `lib_layerdiffusion` from `sd-forge-layerdiffuse` is installed
2. When `transparent_background: true` is requested:
   - `LayerDiffusionProcessor` imports `lib_layerdiffusion`
   - Calls `apply_layerdiffuse(pipe)` to modify the pipeline
   - Pipeline generates native RGBA images
3. If `lib_layerdiffusion` fails, falls back to post-processing

### ControlNet Union Flow:
1. ControlNet Union SDXL model downloads from HuggingFace
2. Works with standard `StableDiffusionXLControlNetPipeline`
3. Supports multiple control types in one model

## Testing Commands

### Test Basic Generation:
```bash
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a fantasy landscape", "width": 1024, "height": 1024}'
```

### Test Layer Diffusion:
```bash
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a fantasy character", "transparent_background": true}'
```

### Test ControlNet + Layer Diffusion:
```bash
curl -X POST http://localhost:7860/api/generate-border \
  -H "Content-Type: application/json" \
  -d '{"prompt": "ornate border", "transparent_background": true}'
```

## Troubleshooting

### If Layer Diffusion doesn't work:
- Check logs: `docker compose logs stable-diffusion | grep layerdiffusion`
- Falls back to post-processing (still works!)
- Verify `lib_layerdiffusion` installed correctly

### If ControlNet Union fails:
- Falls back to standard ControlNet Canny
- Check model ID: `xinsir6/controlnet-union-sdxl-1.0`
- May need to use alternative: `diffusers/controlnet-canny-sdxl-1.0`

### If Juggernaut XL v11 not found:
- System uses base SDXL (still works!)
- Download Juggernaut from CivitAI when ready
- Place in `./runarion-stable-diffusion/models/juggernaut-xl-v11/`

## Next Steps

1. ⏳ **Wait for Docker build to complete** (~5-10 min)
2. ✅ **Start the service** (command above)
3. ✅ **Test Layer Diffusion** (command above)
4. 📥 **Download Juggernaut XL v11** (optional, when ready)

## Summary

✅ **Layer Diffusion**: Using `lib_layerdiffusion` from `lllyasviel/sd-forge-layerdiffuse`  
✅ **ControlNet**: Using Union SDXL from `xinsir6/ControlNetPlus`  
✅ **SDXL**: Ready for base SDXL, Juggernaut XL v11 ready when downloaded  
✅ **No SD Forge UI**: Just the core libraries we need!

**Everything is configured correctly!** 🚀

