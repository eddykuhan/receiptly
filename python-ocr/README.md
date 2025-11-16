# Python OCR Service

FastAPI-based microservice for receipt OCR processing using Azure Computer Vision and Tesseract.

## Overview

The Python OCR service handles receipt image processing, text extraction, and data structuring. It uses a multi-layered approach combining Azure Document Intelligence and Tesseract OCR with custom fallback strategies.

## Directory Structure

```
python-ocr/
├── app/                    # Application code
│   ├── main.py            # FastAPI application entry point
│   ├── core/              # Core functionality
│   ├── routers/           # API route handlers
│   ├── services/          # Business logic (Azure, Tesseract, extractors)
│   └── utils/             # Utility functions
├── docs/                   # Documentation
│   ├── README.md          # Documentation index
│   ├── API_REFERENCE.md   # API documentation
│   └── [feature docs]     # Feature-specific documentation
├── scripts/               # Utility scripts
│   ├── README.md          # Script documentation
│   ├── enable-tesseract-debug.sh
│   └── disable-tesseract-debug.sh
├── tests/                 # Test files
│   ├── test_azure_detection.py
│   ├── test_integration_override.py
│   └── [other tests]
├── debug_ocr/            # Debug output (gitignored)
├── output/               # Processing output (gitignored)
├── venv/                 # Virtual environment (gitignored)
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker container definition
└── docker-compose.yml   # Docker compose configuration
```

## Quick Start

### Prerequisites

- Python 3.9+
- Azure Computer Vision API key
- Virtual environment support

### Installation

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

4. **Start the service:**
   ```bash
   uvicorn app.main:app --reload
   ```

   The service will be available at:
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Features

### OCR Processing

- **Azure Document Intelligence**: Primary OCR engine using Layout and Receipt models
- **Tesseract OCR**: Fallback OCR engine for when Azure fails
- **OpenCV Preprocessing**: Image enhancement and receipt detection
- **Multi-strategy Detection**: Combines multiple detection methods with confidence scoring

### Data Extraction

- **Store Name Extraction**: 4-layer fallback system
  1. Azure Document Intelligence
  2. Tesseract OCR
  3. Custom extraction (known chains, position-based, patterns)
  4. "Unknown Store" placeholder with manual review flag

- **Item Extraction**: Line item detection with quantity and price
- **Total Extraction**: Receipt total amount detection
- **Location Extraction**: Store location and address parsing
- **Date/Time Extraction**: Transaction timestamp

### Data Quality

- **Gibberish Filtering**: Detects and filters invalid text
- **Confidence Scoring**: Validates extraction quality
- **Manual Review Flagging**: Marks low-confidence extractions
- **Validation Rules**: Ensures data integrity

## API Endpoints

### POST /ocr/analyze

Analyze a receipt image and extract structured data.

**Request:**
```bash
curl -X POST http://localhost:8000/ocr/analyze \
  -F "file=@receipt.jpg"
```

**Response:**
```json
{
  "store_name": "Walmart",
  "total": 45.67,
  "items": [
    {"name": "Milk", "price": 3.99, "quantity": 1},
    {"name": "Bread", "price": 2.50, "quantity": 2}
  ],
  "date": "2024-11-16",
  "location": "Seattle, WA"
}
```

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for complete API documentation.

## Environment Variables

Required variables in `.env`:

```bash
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_azure_key

# API Configuration
API_PREFIX=/api/v1

# CORS Settings
CORS_ORIGINS=["http://localhost:3000"]
CORS_HEADERS=["*"]
CORS_METHODS=["*"]

# Debug Configuration (optional)
DEBUG_IMAGE_PROCESSING=false  # Set to 'true' to save images at each processing stage
DEBUG_TESSERACT=false         # Set to 'true' to enable Tesseract debug output
DEBUG_OUTPUT_DIR=debug_ocr    # Directory for debug files
```

## Debugging

### Image Processing Debug Mode

Enable debug mode to save images and data at each processing stage:

```bash
# In .env
DEBUG_IMAGE_PROCESSING=true
```

This creates timestamped session folders with:
- Original downloaded image
- Cropped image (Azure Layout or OpenCV)
- Preprocessed image for Azure
- Location extraction text
- Azure analysis results
- Final merged results
- Validation output

See [docs/DEBUG_MODE.md](docs/DEBUG_MODE.md) for complete debugging guide.

### Tesseract Debug Mode

Enable Tesseract debugging:

```bash
./scripts/enable-tesseract-debug.sh
# or manually: DEBUG_TESSERACT=true in .env
```

Disable when done:

```bash
./scripts/disable-tesseract-debug.sh
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_azure_detection.py

# Run with coverage
pytest --cov=app tests/

# Run with debug output
pytest -v -s
```

## Debugging

### Enable Tesseract Debug Mode

```bash
./scripts/enable-tesseract-debug.sh
```

This creates detailed debug output in `debug_ocr/` including:
- Original and preprocessed images
- Tesseract raw output
- Confidence scores
- Detected regions

### Disable Debug Mode

```bash
./scripts/disable-tesseract-debug.sh
```

See [scripts/README.md](scripts/README.md) for more debugging tools.

## Docker

### Build and Run

```bash
# Build image
docker build -t receiptly-ocr .

# Run container
docker run -p 8000:8000 \
  -e AZURE_VISION_KEY=your_key \
  -e AZURE_VISION_ENDPOINT=your_endpoint \
  receiptly-ocr
```

### Docker Compose

```bash
# Start service
docker-compose up

# Start in background
docker-compose up -d

# Stop service
docker-compose down
```

## Documentation

### Main Documentation
- [docs/README.md](docs/README.md) - Complete documentation index

### Feature Documentation
- [docs/AZURE_RECEIPT_DETECTION.md](docs/AZURE_RECEIPT_DETECTION.md) - Azure integration
- [docs/STORE_NAME_FALLBACK.md](docs/STORE_NAME_FALLBACK.md) - Store name extraction
- [docs/OPENCV_IMPROVEMENTS.md](docs/OPENCV_IMPROVEMENTS.md) - Image preprocessing
- [docs/GIBBERISH_FILTERING.md](docs/GIBBERISH_FILTERING.md) - Text validation
- [docs/OCR_IMPROVEMENTS.md](docs/OCR_IMPROVEMENTS.md) - OCR enhancements

### API Documentation
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) - Complete API reference
- Interactive docs: http://localhost:8000/docs (when running)

## Performance

### Optimization Tips

1. **Use Azure caching**: Enable caching for repeated receipts
2. **Optimize image size**: Resize large images before processing
3. **Batch processing**: Process multiple receipts in parallel
4. **Disable debug mode**: Ensure debug mode is off in production

See [docs/WORKFLOW_OPTIMIZATION.md](docs/WORKFLOW_OPTIMIZATION.md) for details.

### Benchmarks

Typical processing times:
- Small receipt (< 1MB): 2-4 seconds
- Medium receipt (1-3MB): 4-8 seconds
- Large receipt (3-10MB): 8-15 seconds

Times include:
- Image download/upload
- OpenCV preprocessing
- Azure OCR processing
- Tesseract fallback (if needed)
- Data extraction and validation

## Troubleshooting

### Common Issues

**Azure authentication fails:**
```bash
# Check credentials
echo $AZURE_VISION_KEY
echo $AZURE_VISION_ENDPOINT

# Test connection
curl -X POST "$AZURE_VISION_ENDPOINT/vision/v3.2/analyze?visualFeatures=Categories" \
  -H "Ocp-Apim-Subscription-Key: $AZURE_VISION_KEY"
```

**Tesseract not found:**
```bash
# Install Tesseract
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Check installation
tesseract --version
```

**Import errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Poor OCR accuracy:**
1. Check image quality (minimum 300 DPI recommended)
2. Ensure receipt is well-lit and in focus
3. Enable debug mode to analyze issues
4. Review confidence scores
5. Check if fallback strategies are working

## Contributing

1. Create feature branch from `develop`
2. Make changes
3. Add tests for new features
4. Update documentation
5. Run tests: `pytest`
6. Submit pull request

## Related Services

- **.NET API Gateway**: http://localhost:5188 (main application)
- **Angular PWA**: http://localhost:4200 (frontend)

See [../README.md](../README.md) for overall project documentation.

## License

[License information will be added]
