# Receipt Merchant Extractor using GPT-4 Vision

A Python project that uses GPT-4 Vision (GPT-4.1) to automatically extract merchant name and address from receipt images.

## Features

- 🔍 **Accurate Extraction**: Uses GPT-4 Vision to intelligently extract merchant information
- 📸 **Image Support**: Works with various image formats (JPG, PNG, BMP, TIFF, WebP)
- 📦 **Batch Processing**: Process multiple receipts at once
- 💾 **JSON Output**: Structured JSON output for easy integration
- 🎯 **Focused Extraction**: Extracts only merchant name and address from receipt headers

## Prerequisites

- Python 3.8 or higher
- OpenAI API key with GPT-4 Vision access

## Installation

1. **Navigate to the project directory**:
   ```bash
   cd /Users/kuhan/Projects/receiptly/gpt4-vision-extractor
   ```

2. **Run the quick start script**:
   ```bash
   ./quickstart.sh
   ```

   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up your OpenAI API key**:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

## Usage

### Single Receipt Processing

Process a single receipt image:

```bash
python receipt_extractor.py path/to/receipt.jpg
```

Save results to a specific JSON file:

```bash
python receipt_extractor.py path/to/receipt.jpg output/result.json
```

### Batch Processing

Process all receipts in a directory:

```bash
python batch_processor.py receipts/
```

Specify a custom output directory:

```bash
python batch_processor.py receipts/ output/
```

### Programmatic Usage

```python
from receipt_extractor import ReceiptExtractor

# Initialize the extractor
extractor = ReceiptExtractor()

# Extract merchant information
result = extractor.extract_merchant_info("receipt.jpg")

print(f"Merchant: {result['merchant_name']}")
print(f"Address: {result['merchant_address']}")
```

## Output Format

The extraction returns a JSON object with the following structure:

```json
{
  "merchant_name": "ABC Supermarket",
  "merchant_address": "123 Main Street, City, State 12345",
  "raw_response": "..."
}
```

## Project Structure

```
gpt4-vision-extractor/
├── receipt_extractor.py    # Main extraction module
├── batch_processor.py      # Batch processing utility
├── example_usage.py        # Usage examples
├── test_setup.py          # Setup verification script
├── quickstart.sh          # Quick setup script
├── requirements.txt       # Python dependencies
├── config.json           # Configuration settings
├── .env.example          # Environment variable template
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── receipts/            # Place receipt images here
└── output/              # Extraction results saved here
```

## How It Works

1. **Image Encoding**: The receipt image is encoded to base64 format
2. **API Call**: The encoded image is sent to GPT-4 Vision with a specialized prompt
3. **Extraction**: GPT-4 Vision analyzes the receipt and extracts merchant information
4. **Parsing**: The response is parsed and structured into JSON format
5. **Output**: Results are displayed and optionally saved to a file

## Tips for Best Results

- 📷 Use clear, well-lit images
- 🔍 Ensure the merchant name and address are visible
- 📐 Avoid heavily skewed or rotated images
- 🎨 Higher resolution images generally work better

## Error Handling

The extractor includes comprehensive error handling:
- Missing API key detection
- File not found errors
- JSON parsing errors
- API call failures

All errors are logged with descriptive messages.

## Cost Considerations

GPT-4 Vision API calls are charged per request. Consider:
- Testing with a small batch first
- Monitoring your OpenAI API usage
- Setting up usage limits in your OpenAI account

Approximate costs:
- $0.01 - $0.03 per image
- 100 receipts ≈ $1-3
- Check current pricing: https://openai.com/pricing

## Troubleshooting

### "OpenAI API key not found"
- Ensure `.env` file exists and contains `OPENAI_API_KEY`
- Check that the API key is valid

### "Image file not found"
- Verify the image path is correct
- Use absolute paths if relative paths don't work

### "Error parsing JSON response"
- This may indicate an API issue or unexpected response format
- Check the `raw_response` field in the output for details

## Integration with Receiptly

This module can be integrated into the main Receiptly project:

1. **As a fallback**: Use when Azure OCR fails to extract merchant info
2. **For validation**: Compare results with existing OCR methods
3. **Enhanced accuracy**: Use GPT-4 Vision for critical merchant data

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions:
- Check the OpenAI API documentation
- Review `GETTING_STARTED.md` for setup help
- Run `python test_setup.py` to diagnose issues
