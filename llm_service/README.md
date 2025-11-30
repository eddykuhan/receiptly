# LLM Service

FastAPI service for LLM-powered receipt processing features including item canonicalization, merchant normalization, category classification, and location selection.

## Features

- **Item Canonicalization**: Normalize messy OCR item names into clean, canonical product names
- **Merchant Normalization**: Standardize merchant/store names
- **Category Classification**: Classify items into product categories
- **Receipt Cleaning**: Clean and structure OCR output
- **Location Selection**: Select the best location from multiple candidates

## Setup

### 1. Install Dependencies

```bash
cd llm_service
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

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

### 3. Run the Service

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the service
uvicorn main:app --host 0.0.0.0 --port 8500 --reload
```

The service will be available at:
- API: http://localhost:8500
- Documentation: http://localhost:8500/docs

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
