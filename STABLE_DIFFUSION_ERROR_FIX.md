# Stable Diffusion Service Error - Explanation & Fix

## 🔴 The Error

```
HTTPConnectionPool(host='stable-diffusion', port=7860): Max retries exceeded with url: /health 
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
```

## 📋 What's Happening

### 1. **Service is Still Initializing**
The `stable-diffusion` service is running but **still downloading models** from HuggingFace. The service hasn't finished starting up yet, so:
- The health endpoint isn't responding yet (or returning 503)
- The Python app can't connect because the service is still loading
- This is **normal** on first run - SDXL models are ~6.6GB and take 15-30 minutes to download

### 2. **Juggernaut Model Structure Issue**
You have a `juggernaut-xl-v11` folder with a single `.safetensors` file:
```
juggernaut-xl-v11/
  └── juggernautXL_v8Rundiffusion.safetensors
```

**The Problem:** Diffusers (the library we use) requires models in a **specific folder structure**:
```
juggernaut-xl-v11/
  ├── model_index.json          ← Required!
  ├── unet/
  ├── vae/
  ├── text_encoder/
  ├── text_encoder_2/
  ├── tokenizer/
  ├── tokenizer_2/
  └── scheduler/
```

A single `.safetensors` file is a **checkpoint format**, not the diffusers format. The code now detects this and falls back to downloading from HuggingFace.

## ✅ Solutions

### Option 1: Wait for Download to Complete (Easiest)
The service is currently downloading the base SDXL model. Just wait:
1. **Monitor progress:**
   ```bash
   docker compose -f docker-compose.dev.yml logs -f stable-diffusion
   ```
2. **Check when ready:**
   ```bash
   curl http://localhost:7860/health
   ```
   When it returns `"status": "healthy"`, the service is ready!

### Option 2: Use Your Juggernaut Model (Better Quality)
To use your Juggernaut XL v11 model, you need to convert it to the diffusers format:

#### Step 1: Convert the Checkpoint
You'll need to convert the `.safetensors` checkpoint to diffusers format. Use this script:

```python
# convert_juggernaut.py
from diffusers import StableDiffusionXLPipeline
import torch

# Load from checkpoint
pipe = StableDiffusionXLPipeline.from_single_file(
    "runarion-stable-diffusion/models/juggernaut-xl-v11/juggernautXL_v8Rundiffusion.safetensors",
    torch_dtype=torch.float16
)

# Save in diffusers format
pipe.save_pretrained("runarion-stable-diffusion/models/juggernaut-xl-v11")
```

Run this **outside Docker** (or in a Python container with the model file accessible).

#### Step 2: Update Environment Variable
Once converted, set in `docker-compose.dev.yml` or `.env`:
```yaml
- SD_MODEL_ID=./models/juggernaut-xl-v11  # Use local path
```

Or set `ALLOW_HF_DOWNLOAD=false` to force local-only.

### Option 3: Download Juggernaut from HuggingFace (If Available)
Some Juggernaut models are on HuggingFace. Check if `Ragnarok_AI/Juggernaut-XL-v11` exists and update:
```yaml
- SD_MODEL_ID=${SD_MODEL_ID:-Ragnarok_AI/Juggernaut-XL-v11}
```

## 🔧 What I Fixed

1. **Better Model Detection:** Now checks for `model_index.json` to verify proper model structure
2. **Improved Health Check:** Returns proper status codes and messages during initialization
3. **Better Error Messages:** Warns when model structure is incorrect

## 📊 Current Status Check

```bash
# Check service status
docker compose -f docker-compose.dev.yml ps stable-diffusion

# Check logs (see download progress)
docker compose -f docker-compose.dev.yml logs stable-diffusion --tail 50

# Test health endpoint
curl http://localhost:7860/health
```

## ⏱️ Expected Timeline

- **Model Download:** 15-30 minutes (first time only)
- **Model Loading:** 2-5 minutes after download
- **Total Startup:** ~20-35 minutes on first run

After the first run, models are cached and startup is much faster (~2-5 minutes).

## 🎯 Quick Test

Once the service is healthy:
```bash
# Should return: {"status": "healthy", ...}
curl http://localhost:7860/health

# Then try generating a cover in your app
```

## 📝 Notes

- The `hf_xet` warnings are **not critical** - just performance hints
- The PowerShell `curl` alias issue is also **not critical** - the service still works
- PDF generation works **without** Stable Diffusion - you can test that now!

