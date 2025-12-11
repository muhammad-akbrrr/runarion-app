# 🧪 SDXL Testing Guide

## ✅ READY TO TEST!

All code has been migrated to SDXL. Follow these steps to test:

---

## Step 1: Rebuild Docker Image (REQUIRED)

**This is critical - the old image won't work with SDXL!**

```bash
# Stop and remove old container
docker compose -f docker-compose.dev.yml stop stable-diffusion
docker compose -f docker-compose.dev.yml rm -f stable-diffusion

# Rebuild with no cache (ensures fresh SD Forge installation)
docker compose -f docker-compose.dev.yml build --no-cache stable-diffusion

# This will take 5-10 minutes - grab a coffee ☕
```

---

## Step 2: Start the Service

```bash
# Start the new SDXL container
docker compose -f docker-compose.dev.yml up -d stable-diffusion

# Watch the logs (models will download on first run)
docker compose -f docker-compose.dev.yml logs -f stable-diffusion
```

**First run will:**
- Download Juggernaut XL v11 (~6.6GB) - takes 15-30 minutes
- Download SDXL ControlNet (~1-2GB) if enabled
- Initialize SD Forge with Layer Diffusion support

**Wait for:** `"SDXL startup complete"` in the logs

---

## Step 3: Verify Health Check

```bash
# Check if service is healthy
curl http://localhost:7860/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "cuda_available": true,
  "model_loaded": true,
  "model_ready": true,
  "use_controlnet": true,
  "model_type": "SDXL"
}
```

✅ If you see `"model_type": "SDXL"` - you're good!

---

## Step 4: Test Basic Generation

### Test 1: Standard Image (No Transparency)

```bash
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful fantasy landscape with mountains and a lake at sunset",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "transparent_background": false
  }' \
  --output test_sdxl_standard.png
```

**Expected:**
- ✅ Image generated (1024×1024 PNG)
- ✅ Takes 30-60 seconds (GPU) or 15-30 minutes (CPU)
- ✅ High quality SDXL output

---

## Step 5: Test Layer Diffusion (Transparent Background)

### Test 2: Transparent Background (Layer Diffusion)

```bash
curl -X POST http://localhost:7860/api/generate-cover \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a fantasy character portrait, detailed face, magical aura",
    "width": 832,
    "height": 1216,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "transparent_background": true
  }' \
  --output test_sdxl_transparent.png
```

**Expected:**
- ✅ Image generated with transparent background
- ✅ Check logs for: `"Image generated with Layer Diffusion transparency"`
- ✅ Open in image viewer - should have transparent background (checkerboard pattern)

**If Layer Diffusion fails:**
- Check logs for errors
- Falls back to post-processing (still works, but not native)

---

## Step 6: Test ControlNet Border Generation

### Test 3: Border with ControlNet

```bash
curl -X POST http://localhost:7860/api/generate-border \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "ornate decorative border frame, intricate patterns, elegant design",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "border_style": "ornate"
  }' \
  --output test_sdxl_border.png
```

**Expected:**
- ✅ Border generated with ControlNet
- ✅ Transparent center (border frame only)
- ✅ SDXL quality detail

---

## Step 7: Test from Frontend

1. **Open your app** in the browser
2. **Navigate to:** "Book Preview - Image & PDF Generator"
3. **Select a chapter**
4. **Enter a prompt:** e.g., "a fantasy book cover with dragons"
5. **Settings:**
   - Width: 1024
   - Height: 1024
   - Steps: 30
   - CFG Scale: 5.0
   - **Toggle "Transparent Background" ON**
6. **Click "Generate Cover"**

**Expected:**
- ✅ Image generates (30-60 seconds)
- ✅ Shows in the preview
- ✅ If transparent: background should be transparent

---

## 🐛 Troubleshooting

### Issue: "SD Forge not found" or Import Error

**Solution:**
```bash
# Rebuild with no cache
docker compose -f docker-compose.dev.yml build --no-cache stable-diffusion
```

### Issue: Out of Memory (OOM)

**Solution:**
- Reduce resolution to 832×1216 or 768×1024
- Check GPU VRAM: `nvidia-smi`
- Need 8GB+ VRAM for 1024×1024

### Issue: Models Not Downloading

**Solution:**
- Check internet connection
- Check disk space (need ~10GB+)
- Check logs: `docker compose logs stable-diffusion`
- Manual download: See `SDXL_MIGRATION.md`

### Issue: Layer Diffusion Not Working

**Check logs:**
```bash
docker compose logs stable-diffusion | grep -i "layer"
```

**Expected:** `"Layer Diffusion processor initialized (SD Forge native support)"`

**If fails:**
- Falls back to post-processing (still works)
- Check SD Forge installation in logs

### Issue: Slow Generation

**Normal:**
- GPU: 30-60 seconds per image (first one may take 1-2 min)
- CPU: 15-30 minutes per image (not recommended)

**If too slow:**
- Check GPU utilization: `nvidia-smi`
- Reduce steps to 20-25
- Reduce resolution

---

## ✅ Success Criteria

You'll know it's working when:

1. ✅ Health check returns `"model_type": "SDXL"`
2. ✅ Standard images generate at 1024×1024
3. ✅ Transparent images have native transparency (not post-processed)
4. ✅ Logs show "Layer Diffusion" messages
5. ✅ Image quality is noticeably better than SD 1.5
6. ✅ Frontend can generate covers successfully

---

## 📊 Performance Benchmarks

**Expected times (with GPU):**
- First generation: 1-2 minutes (model loading)
- Subsequent generations: 30-60 seconds
- With Layer Diffusion: Same speed (native)
- With ControlNet: 40-70 seconds

**VRAM Usage:**
- 1024×1024: ~8-12GB VRAM
- 832×1216: ~7-10GB VRAM
- 768×1024: ~6-9GB VRAM

---

## 🎉 You're Ready!

Once all tests pass, you're good to go! SDXL is now fully integrated with:
- ✅ Native Layer Diffusion
- ✅ ControlNet support
- ✅ High-quality 1024×1024+ generation

**Let me know how the tests go!** 🚀

