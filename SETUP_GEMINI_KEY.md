# 🔑 Quick Setup: Add Gemini API Key

## The Problem
Generation isn't working because the Gemini API key isn't configured in Docker.

## The Solution

You need to create a `.env` file in the **root directory** with your API keys.

### Step 1: Create `.env` file

In the root directory (`C:\Users\Yousuf Zakhel\OneDrive\Documents\GitHub\runarion-app`), create a file named `.env`

### Step 2: Add your Gemini API Key

Add this line to the `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3: Restart Docker containers

After adding the key, restart the Python container:

```bash
docker restart runarion-app-python-app-1
```

Or restart all services:
```bash
docker compose restart
```

## Complete `.env` File Template

If you don't have a `.env` file yet, here's a minimal template with your Gemini key:

```env
# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Database (if not set, Docker will use defaults)
DB_HOST=postgres-db
DB_PORT=5432
DB_DATABASE=runarion
DB_USER=postgres
DB_PASSWORD=your_db_password_here

# Other API Keys (optional, but recommended)
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Model Names
GEMINI_MODEL_NAME=gemini-2.0-flash
OPENAI_MODEL_NAME=gpt-4
DEEPSEEK_MODEL_NAME=deepseek-chat

# Python Service
PYTHON_SERVICE_URL=http://python-app:5000
```

## Quick Test After Setup

1. **Check if key is loaded:**
   ```bash
   docker exec runarion-app-python-app-1 env | findstr GEMINI
   ```
   Should show: `GEMINI_API_KEY=AIzaSy...`

2. **Try generating again in Laravel UI**

3. **Check Python logs:**
   ```bash
   docker logs runarion-app-python-app-1 --tail 20
   ```
   Should NOT show API key errors

## Troubleshooting

### Issue: "API key not found"
- Make sure `.env` file is in root directory
- Check file is named exactly `.env` (not `.env.txt`)
- Restart Python container after creating file

### Issue: Still not working
- Check Laravel also needs the key (if passing through):
  ```env
  # In .env file, Laravel might need:
  GEMINI_API_KEY=your_gemini_api_key_here
  ```

- Check Python container environment:
  ```bash
  docker exec runarion-app-python-app-1 printenv | findstr API
  ```

## Important Notes

1. **Don't commit `.env` to git** - It should be in `.gitignore`
2. **Restart containers** after changing `.env` file
3. **Use docker-compose.dev.yml** if you're in development mode

