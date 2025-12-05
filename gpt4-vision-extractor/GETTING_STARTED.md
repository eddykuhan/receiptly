# Getting Started with Receipt Extractor

Welcome! This guide will help you get started with the Receipt Merchant Extractor using GPT-4 Vision.

## Prerequisites

Before you begin, make sure you have:

1. **Python 3.8+** installed on your system
2. **OpenAI API Key** with GPT-4 Vision access
   - Sign up at: https://platform.openai.com
   - Get your API key: https://platform.openai.com/api-keys
   - Note: You'll need to add payment method and have credits

## Step-by-Step Setup

### Step 1: Navigate to Project Directory

```bash
cd /Users/kuhan/Projects/receiptly/gpt4-vision-extractor
```

### Step 2: Run Quick Start (Recommended)

```bash
chmod +x quickstart.sh
./quickstart.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up directories
- Create .env file template

### Step 3: Add Your API Key

Edit the `.env` file:

```bash
nano .env
```

Replace `your_openai_api_key_here` with your actual API key:

```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

Save and exit (Ctrl+X, then Y, then Enter)

### Step 4: Verify Setup

```bash
source venv/bin/activate  # Activate virtual environment
python test_setup.py      # Run verification
```

### Step 5: Add Receipt Images

Place your receipt images in the `receipts/` directory:

```bash
# Example: Copy a receipt image
cp ~/Downloads/my_receipt.jpg receipts/
```

Or use existing receipts from the parent project:

```bash
# Link to parent receipts directory
ln -s ../receipts receipts_parent
```

### Step 6: Process Your First Receipt

```bash
python receipt_extractor.py receipts/my_receipt.jpg
```

## Alternative: Manual Setup

If you prefer manual setup:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env

# 5. Edit .env and add your API key
nano .env

# 6. Create directories
mkdir -p receipts output

# 7. Verify setup
python test_setup.py
```

## Usage Examples

### Process a Single Receipt

```bash
# Basic usage
python receipt_extractor.py receipts/receipt1.jpg

# Save to specific output file
python receipt_extractor.py receipts/receipt1.jpg output/result.json
```

### Process Multiple Receipts

```bash
# Process all receipts in receipts/ directory
python batch_processor.py receipts/

# Specify custom output directory
python batch_processor.py receipts/ output/batch_results/
```

### Run Examples

```bash
python example_usage.py
```

## Understanding the Output

The extractor returns JSON with:

```json
{
  "merchant_name": "ABC Store",
  "merchant_address": "123 Main Street, City, State 12345",
  "raw_response": "..."
}
```

- **merchant_name**: The business/store name
- **merchant_address**: Complete address
- **raw_response**: Full GPT-4 Vision response

## Tips for Best Results

1. **Image Quality**
   - Use clear, well-lit photos
   - Ensure text is readable
   - Avoid heavy shadows or glare

2. **Image Format**
   - Supported: JPG, PNG, BMP, TIFF, WebP
   - Higher resolution generally works better

3. **Receipt Position**
   - Merchant info is usually at the top
   - Ensure the top portion is visible

4. **Cost Management**
   - Test with 1-2 images first
   - Monitor usage at: https://platform.openai.com/usage
   - Set spending limits in OpenAI dashboard

## Troubleshooting

### "OpenAI API key not found"

**Solution**: Make sure you've created `.env` file and added your API key:

```bash
cp .env.example .env
nano .env  # Add your key
```

### "Image file not found"

**Solution**: Check the file path is correct:

```bash
ls receipts/  # List files in receipts directory
```

### "Module not found" errors

**Solution**: Install dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Permission denied on quickstart.sh

**Solution**: Make it executable:

```bash
chmod +x quickstart.sh
```

## Cost Estimates

GPT-4 Vision API costs approximately:
- **$0.01 - $0.03 per image** (varies by size)
- 100 receipts ≈ $1-3
- 1000 receipts ≈ $10-30

Always check current pricing: https://openai.com/pricing

## Integration with Receiptly

This GPT-4 Vision extractor can be integrated into the main Receiptly project:

### Option 1: As a Fallback Service

Add to the OCR pipeline when Azure fails:

```python
# In python-ocr/ocr_router.py
from gpt4_vision_extractor.receipt_extractor import ReceiptExtractor

def extract_with_fallback(image_path):
    try:
        # Try Azure first
        result = azure_ocr(image_path)
        if not result.get('merchant_name'):
            # Fallback to GPT-4 Vision
            gpt4_extractor = ReceiptExtractor()
            result = gpt4_extractor.extract_merchant_info(image_path)
        return result
    except Exception as e:
        # Final fallback
        return fallback_extraction(image_path)
```

### Option 2: As a Validation Layer

Compare results for accuracy:

```python
def validate_merchant_info(image_path):
    azure_result = azure_ocr(image_path)
    gpt4_result = ReceiptExtractor().extract_merchant_info(image_path)
    
    # Compare and choose best result
    if azure_result['merchant_name'] == gpt4_result['merchant_name']:
        return azure_result  # High confidence
    else:
        return choose_best_result(azure_result, gpt4_result)
```

## Next Steps

1. ✅ Complete setup above
2. ✅ Process a test receipt
3. ✅ Review the output
4. ✅ Integrate into your workflow

## Need Help?

- Check `README.md` for detailed documentation
- See `QUICKREF.md` for quick command reference
- Review `example_usage.py` for code examples
- Run `python test_setup.py` to diagnose issues

Happy extracting! 🎉
