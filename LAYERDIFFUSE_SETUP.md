# Layer Diffusion Setup (No SD Forge Needed!)

## ✅ What Changed

We've **removed SD Forge** (which is a UI fork) and now use the **layerdiffuse library directly**. This is perfect for your custom API!

## What You Have Now

1. **Standard SDXL Pipeline** - Uses `StableDiffusionXLPipeline` (no Forge)
2. **Layer Diffusion Library** - Direct Python library (`layerdiffuse`)
3. **ControlNet Support** - Works with SDXL ControlNet
4. **Juggernaut XL v11 Ready** - Just place the model locally

## Setup Instructions

### 1. Download Juggernaut XL v11

Since Juggernaut XL v11 isn't on HuggingFace, download it manually:

1. Go to: https://civitai.com/models/133005?modelVersionId=288982
2. Download the model file (6.62 GB SafeTensor)
3. Extract/place files in: `./runarion-stable-diffusion/models/juggernaut-xl-v11/`

The model structure should be:
```
juggernaut-xl-v11/
├── model_index.json
├── unet/
├── vae/
├── text_encoder/
├── text_encoder_2/
├── tokenizer/
├── tokenizer_2/
└── scheduler/
```

### 2. ControlNet Union SDXL (Optional)

If you want ControlNet Union SDXL instead of the default Canny:

1. Set environment variable:
   ```bash
   CONTROLNET_MODEL_ID=xinsir/controlnet-union-sdxl-1.0
   ```

2. Or update `docker-compose.dev.yml`:
   ```yaml
   - CONTROLNET_MODEL_ID=${CONTROLNET_MODEL_ID:-xinsir/controlnet-union-sdxl-1.0}
   ```

### 3. Rebuild Docker

```bash
# Stop and remove old container
docker compose -f docker-compose.dev.yml stop stable-diffusion
docker compose -f docker-compose.dev.yml rm -f stable-diffusion

# Rebuild (will install layerdiffuse library)
docker compose -f docker-compose.dev.yml build --no-cache stable-diffusion

# Start
docker compose -f docker-compose.dev.yml up -d stable-diffusion
```

## How It Works

### Layer Diffusion

The `layerdiffuse` library is installed and imported. When you request transparent backgrounds:

1. `LayerDiffusionProcessor` applies `apply_layerdiffuse()` to the pipeline
2. Pipeline generates images with native RGBA transparency
3. No post-processing needed!

### Fallback

If `layerdiffuse` isn't available or fails:
- Falls back to post-processing transparency (still works!)
- Logs a warning but continues working

## Testing

### Test Layer Diffusion

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

Check logs for:
- `"layerdiffuse library imported successfully"` ✅
- `"Layer Diffusion enabled using layerdiffuse library"` ✅
- `"Image generated with Layer Diffusion transparency"` ✅

### Test ControlNet + Layer Diffusion

```bash
curl -X POST http://localhost:7860/api/generate-border \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "ornate decorative border",
    "transparent_background": true
  }' \
  --output test_border.png
```

## Troubleshooting

### "layerdiffuse library not found"

**Check:**
1. Rebuild Docker with `--no-cache`
2. Check logs: `docker compose logs stable-diffusion | grep layerdiffuse`
3. Falls back to post-processing (still works!)

### "Failed to enable Layer Diffusion"

**Check:**
1. Verify `layerdiffuse` installed: Check requirements.txt
2. Check import errors in logs
3. Post-processing fallback will still work

### Model Not Found

**For Juggernaut XL v11:**
- Ensure model is in `./runarion-stable-diffusion/models/juggernaut-xl-v11/`
- Check `model_index.json` exists
- Set `SD_MODEL_ID` to use local path or keep default (base SDXL)

## What's Different from Before

| Before (SD Forge) | Now (layerdiffuse) |
|-------------------|-------------------|
| Full UI fork | Just the library |
| `sgm_forge` imports | `layerdiffuse` imports |
| Forge pipelines | Standard SDXL pipelines |
| Complex setup | Simple library install |

## Benefits

✅ **Simpler** - No UI fork, just a library  
✅ **Lighter** - Smaller dependency footprint  
✅ **More Compatible** - Works with standard diffusers  
✅ **Easier to Debug** - Standard pipeline, easier to troubleshoot  
✅ **Same Functionality** - Layer Diffusion still works!

## Next Steps

1. ✅ Rebuild Docker
2. ✅ Download Juggernaut XL v11 (if you want it)
3. ✅ Test Layer Diffusion
4. ✅ Test ControlNet + Layer Diffusion
5. ✅ Enjoy native transparency! 🎉

