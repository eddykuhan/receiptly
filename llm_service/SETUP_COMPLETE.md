# LLM Service Environment Configuration - Setup Complete ✅

## What Was Done

1. **Created `.env.example`** - Template file with all environment variables documented
2. **Created `.env`** - Active configuration file (gitignored)
3. **Created `config.py`** - Module to load environment variables before other imports
4. **Updated `main.py`** - Import config module first to ensure env vars are loaded
5. **Created `.gitignore`** - Ensures `.env` is not committed to git
6. **Created `README.md`** - Comprehensive documentation for the service

## Files Created/Modified

### New Files:
- `/llm_service/.env` - Environment configuration (gitignored)
- `/llm_service/.env.example` - Template for environment variables
- `/llm_service/config.py` - Environment loader module
- `/llm_service/.gitignore` - Git ignore rules
- `/llm_service/README.md` - Service documentation

### Modified Files:
- `/llm_service/main.py` - Now imports config first to load env vars

## Next Steps

### 1. Configure Your API Key

Edit `/llm_service/.env` and replace the placeholder with your actual API key:

**For OpenAI (default):**
```env
USE_GROQ=false
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
MODEL_NAME=gpt-4o-mini
```

**For Groq (faster, free tier):**
```env
USE_GROQ=true
GROQ_API_KEY=your-actual-groq-api-key-here
```

### 2. Test the Service

```bash
cd llm_service
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8500 --reload
```

Visit http://localhost:8500/docs to see the API documentation.

### 3. Or Use the Startup Script

The main startup script should now work:
```bash
./start-services.sh
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_GROQ` | No | `false` | Set to `true` to use Groq, `false` for OpenAI |
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key (required when USE_GROQ=false) |
| `MODEL_NAME` | No | `gpt-4o-mini` | OpenAI model to use |
| `GROQ_API_KEY` | Yes* | - | Groq API key (required when USE_GROQ=true) |

*One of `OPENAI_API_KEY` or `GROQ_API_KEY` is required depending on which provider you choose.

## How It Works

1. **`config.py`** is imported first in `main.py`
2. This calls `load_dotenv()` which reads the `.env` file
3. Environment variables are now available to all modules via `os.getenv()`
4. The `LLMClient` in `models/llm_client.py` can now read the API keys

## Troubleshooting

### Error: "The api_key client option must be set"
- Make sure you've edited `.env` with your actual API key
- Verify the API key doesn't have extra spaces or quotes
- Check that `USE_GROQ` matches your chosen provider

### Service won't start
- Ensure virtual environment is activated: `source venv/bin/activate`
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify port 8500 is not in use: `lsof -i :8500`

## Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key and paste it in `.env`

### Groq (Free Alternative)
1. Go to https://console.groq.com/keys
2. Sign in or create an account
3. Create a new API key
4. Copy the key and paste it in `.env`
5. Set `USE_GROQ=true` in `.env`
