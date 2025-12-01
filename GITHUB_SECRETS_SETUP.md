# GitHub Secrets Configuration

Add these secrets to your GitHub repository for the LLM service deployment:

## Required Secrets

### Option 1: Using OpenAI (Default)

1. **OPENAI_API_KEY** (Required)
   - Description: OpenAI API key for GPT models
   - How to get: https://platform.openai.com/api-keys
   - Example: `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

2. **MODEL_NAME** (Optional)
   - Description: OpenAI model to use
   - Default: `gpt-4o-mini`
   - Options: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`

### Option 2: Using Groq (Fast & Free Tier)

1. **USE_GROQ** (Required)
   - Description: Switch to use Groq instead of OpenAI
   - Value: `true`

2. **GROQ_API_KEY** (Required)
   - Description: Groq API key for Llama models
   - How to get: https://console.groq.com/keys
   - Example: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## How to Add Secrets

### Via GitHub UI

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   - Name: `OPENAI_API_KEY` (or other secret name)
   - Value: (paste your API key)
   - Click **Add secret**

### Via GitHub CLI

```bash
# For OpenAI
gh secret set OPENAI_API_KEY --body "sk-proj-your-key-here"
gh secret set MODEL_NAME --body "gpt-4o-mini"

# For Groq
gh secret set USE_GROQ --body "true"
gh secret set GROQ_API_KEY --body "gsk_your-key-here"
```

## Verify Secrets

```bash
# List all secrets (values are hidden)
gh secret list
```

## Secret Usage in Deployment

These secrets are injected into the LLM service container via the `.env` file created during deployment:

```bash
# Created by GitHub Actions in llm.env
USE_GROQ=${USE_GROQ:-false}
OPENAI_API_KEY=${OPENAI_API_KEY}
MODEL_NAME=${MODEL_NAME:-gpt-4o-mini}
GROQ_API_KEY=${GROQ_API_KEY}
HOST=0.0.0.0
PORT=8500
```

## Testing API Keys Locally

Before adding to GitHub, test your keys:

### OpenAI
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Groq
```bash
curl https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Cost Considerations

### OpenAI (gpt-4o-mini)
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens
- Recommended for production

### Groq (Free Tier)
- Free tier: 14,400 requests/day
- Very fast inference
- Good for development/testing
- Rate limits apply

## Security Best Practices

✅ **DO:**
- Use separate API keys for staging and production
- Rotate keys regularly
- Monitor API usage in provider dashboard
- Set spending limits in provider settings

❌ **DON'T:**
- Commit API keys to git
- Share API keys in chat/email
- Use production keys for development
- Leave unused keys active

## Troubleshooting

### "Invalid API key" error
- Verify key is copied correctly (no extra spaces)
- Check key hasn't expired
- Ensure billing is set up (for OpenAI)

### LLM service not starting
- Check CloudWatch logs: `/receiptly/staging/llm`
- SSH to EC2: `journalctl -u receiptly-llm -f`
- Verify .env file: `cat /opt/receiptly/llm/.env`

### Rate limit errors
- Switch to OpenAI if using Groq free tier
- Implement caching (already done in code)
- Reduce concurrent requests
