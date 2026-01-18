# Project Structure

```
gpt4-vision-extractor/
├── receipt_extractor.py      # Main extraction module
├── batch_processor.py         # Batch processing utility
├── example_usage.py          # Usage examples
├── test_setup.py             # Setup verification script
├── quickstart.sh             # Quick setup script
├── requirements.txt          # Python dependencies
├── config.json              # Configuration settings
├── .env.example             # Environment template
├── .env                     # Your API key (create this)
├── .gitignore              # Git ignore rules
├── README.md               # Main documentation
├── GETTING_STARTED.md      # Setup guide
├── QUICKREF.md             # This file
├── receipts/               # Place receipt images here
└── output/                 # Extraction results saved here
```

# Quick Reference

## Setup (First Time)

```bash
# Option 1: Automated setup
./quickstart.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Verify Setup

```bash
python test_setup.py
```

## Usage

### Single Receipt
```bash
python receipt_extractor.py receipts/receipt.jpg
python receipt_extractor.py receipts/receipt.jpg output/result.json
```

### Batch Processing
```bash
python batch_processor.py receipts/
python batch_processor.py receipts/ output/
```

### Examples
```bash
python example_usage.py
```

## API Key

Get your OpenAI API key from:
https://platform.openai.com/api-keys

Add it to `.env`:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## Supported Image Formats

- JPG/JPEG
- PNG
- BMP
- TIFF
- WebP

## Output Format

```json
{
  "merchant_name": "Store Name",
  "merchant_address": "123 Main St, City, State 12345",
  "raw_response": "..."
}
```

## Cost Estimate

GPT-4 Vision pricing (as of 2024):
- ~$0.01 - $0.03 per image (varies by image size and resolution)
- Check current pricing: https://openai.com/pricing

## Tips

1. Use clear, well-lit images
2. Ensure merchant info is visible
3. Test with 1-2 images first
4. Monitor API usage in OpenAI dashboard
5. Set spending limits in OpenAI account

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not found" | Add OPENAI_API_KEY to .env file |
| "Image file not found" | Check file path, use absolute paths |
| "Module not found" | Run: pip install -r requirements.txt |
| "Permission denied" | Run: chmod +x quickstart.sh |

## Integration with Receiptly

```python
# Import in your Python code
from receipt_extractor import ReceiptExtractor

# Use as fallback
extractor = ReceiptExtractor()
result = extractor.extract_merchant_info("path/to/receipt.jpg")
```

## Next Steps

1. ✅ Set up environment
2. ✅ Add API key to .env
3. ✅ Add receipt images to receipts/
4. ✅ Run test_setup.py to verify
5. ✅ Process your first receipt!
