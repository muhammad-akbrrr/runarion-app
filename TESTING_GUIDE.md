# Testing Guide - Image & PDF Generation

## Quick Fix for "Could not resolve host: python-app"

### Option 1: Set Environment Variable (Recommended)

Add to `runarion-laravel/.env`:
```env
PYTHON_SERVICE_URL=http://localhost:5000
```

### Option 2: If Running in Docker

Make sure all services are on the same network. In `docker-compose.dev.yml`, ensure:
- `laravel-app` and `python-app` are both in `runarion-network`
- Set `PYTHON_SERVICE_URL=http://python-app:5000` in Laravel `.env`

## Services That Must Be Running

### 1. Python Service (Port 5000)
```bash
# Check if running
curl http://localhost:5000/health

# If not running, start it:
cd runarion-python
python src/app.py
# OR if using Docker:
docker compose -f docker-compose.dev.yml up python-app
```

### 2. Stable Diffusion Service (Port 7860) - OPTIONAL for now
```bash
# Check if running
curl http://localhost:7860/health

# If not running and you want image generation:
# Uncomment stable-diffusion service in docker-compose.dev.yml
# Then:
docker compose -f docker-compose.dev.yml up stable-diffusion
```

### 3. Laravel Service (Port 8000)
```bash
# Should already be running if you're seeing the UI
curl http://localhost:8000/health
```

## Testing Without Stable Diffusion (PDF Only)

You can test PDF generation WITHOUT Stable Diffusion:

1. Go to Image Editor tab
2. Skip image generation (leave it empty)
3. Click "Generate PDF Preview"
4. This will create a PDF with just text (no covers)

## Testing With Stable Diffusion

1. **Start Stable Diffusion service:**
   ```bash
   # Uncomment in docker-compose.dev.yml, then:
   docker compose -f docker-compose.dev.yml up stable-diffusion -d
   ```

2. **Set environment variable in Python service:**
   Add to `runarion-python/.env`:
   ```env
   STABLE_DIFFUSION_URL=http://localhost:7860
   ```
   (Or `http://stable-diffusion:7860` if in Docker)

3. **Test the connection:**
   ```bash
   curl http://localhost:7860/health
   ```

4. **Try generating a cover:**
   - Select a chapter
   - Enter a prompt
   - Click "Generate Cover"

## Troubleshooting

### Error: "Could not resolve host: python-app"
- **Solution:** Set `PYTHON_SERVICE_URL=http://localhost:5000` in Laravel `.env`
- Or ensure you're running in Docker with proper networking

### Error: "Failed to connect to Stable Diffusion service"
- **Solution:** Make sure Stable Diffusion is running on port 7860
- Check `STABLE_DIFFUSION_URL` in Python service `.env`

### Error: "Python service error"
- **Solution:** Check Python service logs:
  ```bash
  docker compose -f docker-compose.dev.yml logs python-app
  ```

## Quick Test Commands

```bash
# Test Python service
curl http://localhost:5000/health

# Test Stable Diffusion (if running)
curl http://localhost:7860/health

# Test Laravel
curl http://localhost:8000/health
```

