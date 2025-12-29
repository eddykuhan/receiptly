# LLM Service

FastAPI service for LLM-powered receipt processing features including item canonicalization, merchant normalization, category classification, and location selection.

## Features

- **Item Canonicalization**: Normalize messy OCR item names into clean, canonical product names
- **Merchant Normalization**: Standardize merchant/store names
- **Category Classification**: Classify items into product categories
- **Receipt Cleaning**: Clean and structure OCR output
- **Location Selection**: Select the best location from multiple candidates

## Setup

### Option 1: Docker (Recommended)

#### Using Docker Compose (with full stack)
```bash
# From project root
docker-compose up llm-service

# Or run the entire stack
docker-compose up
```

#### Using standalone Docker
```bash
cd llm_service

# Build the image
docker build -t receiptly-llm-service .

# Run the container
docker run -p 8500:8500 \
  -e OPENAI_API_KEY=your-key \
  -e USE_GROQ=false \
  --name receiptly-llm-service \
  receiptly-llm-service
#
sudo docker run -d  -p 8500:8500 --env-file .env llm-service
# Or use docker-compose in llm_service directory
docker-compose up
```

The service will be available at:
- API: http://localhost:8500
- Documentation: http://localhost:8500/docs

### Option 2: Local Development

#### 1. Install Dependencies

```bash
cd llm_service
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` and set your API keys:

```env
# Choose your LLM provider
USE_GROQ=false  # Set to true to use Groq, false for OpenAI

# OpenAI Configuration (when USE_GROQ=false)
OPENAI_API_KEY=sk-your-actual-openai-key
MODEL_NAME=gpt-4o-mini

# Groq Configuration (when USE_GROQ=true)
GROQ_API_KEY=your-actual-groq-key
```

#### 3. Run the Service

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the service
uvicorn main:app --host 0.0.0.0 --port 8500 --reload
```

The service will be available at:
- API: http://localhost:8500
- Documentation: http://localhost:8500/docs

## Docker Configuration

The service includes:
- **Multi-stage build** for optimized image size
- **Health checks** for container monitoring
- **Environment variable configuration** for flexible deployment
- **Network isolation** when using docker-compose

### Docker Environment Variables

When running with Docker, you can pass environment variables via:
1. `.env` file (recommended for local development)
2. `-e` flags in `docker run` command
3. `environment` section in docker-compose.yml

### Integration with OCR Service

When running the full stack with docker-compose, the Python OCR service will automatically connect to the LLM service using the internal Docker network:

```yaml
# In docker-compose.yml
environment:
  - LLM_SERVICE_URL=http://llm-service:8500
```

For local development (services running outside Docker), configure the OCR service to use:
```
LLM_SERVICE_URL=http://localhost:8500
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_GROQ` | No | `false` | Set to `true` to use Groq, `false` for OpenAI |
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key (required when USE_GROQ=false) |
| `MODEL_NAME` | No | `gpt-4o-mini` | OpenAI model to use |
| `GROQ_API_KEY` | Yes* | - | Groq API key (required when USE_GROQ=true) |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8500` | Server port |

*One of `OPENAI_API_KEY` or `GROQ_API_KEY` is required depending on which provider you choose.

## API Endpoints

### POST /canonicalize_item
Canonicalize a single item name.

**Request:**
```json
{
  "raw_item": "Farm Fresh Pure Fresh 1L"
}
```

**Response:**
```json
{
  "canonical_name": "Farm Fresh Fresh Milk 1L"
}
```

### POST /canonicalize_batch
Canonicalize multiple items at once.

**Request:**
```json
{
  "items": ["Farm Fresh Pure Fresh 1L", "MILO 1KG"]
}
```

**Response:**
```json
{
  "canonical_names": ["Farm Fresh Fresh Milk 1L", "Milo 1kg"]
}
```

### POST /normalize_merchant
Normalize merchant name.

**Request:**
```json
{
  "merchant_text": "AEON BIG SUBANG JAYA"
}
```

**Response:**
```json
{
  "merchant": "Aeon Big"
}
```

### POST /classify_category
Classify item into a category.

**Request:**
```json
{
  "name": "Farm Fresh Fresh Milk 1L"
}
```

**Response:**
```json
{
  "category": "Dairy"
}
```

### POST /clean_receipt
Clean OCR receipt data.

**Request:**
```json
{
  "ocr_json": { ... }
}
```

**Response:**
```json
{
  "cleaned": { ... }
}
```

### POST /select_best_location
Select the best location from candidates.

**Request:**
```json
{
  "candidates": [
    {
      "name": "Aeon Big Subang Jaya",
      "address": "123 Main St",
      "distance": 1.5
    }
  ]
}
```

**Response:**
```json
{
  "selected_location": { ... }
}
```

## LLM Provider Options

### OpenAI (Default)
- **Pros**: High quality, reliable
- **Cons**: Costs money per API call
- **Setup**: Get API key from https://platform.openai.com/api-keys

### Groq
- **Pros**: Very fast, free tier available
- **Cons**: Rate limits on free tier
- **Setup**: Get API key from https://console.groq.com/keys

## Development

The service uses an in-memory cache to avoid redundant LLM calls for the same inputs. The cache is stored in `cache/memory_cache.py`.

## Troubleshooting

### Service won't start
- Check that your `.env` file exists and has valid API keys
- Ensure you've activated the virtual environment
- Check that port 8500 is not already in use

### API key errors
- Verify your API key is correct in `.env`
- Make sure `USE_GROQ` is set correctly for your chosen provider
- Check that you have credits/quota remaining with your provider

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Ensure you're in the correct directory and virtual environment is activated
