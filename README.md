# Receipt Merchant & Location Extraction Model

A machine learning model to automatically extract merchant names and locations from OCR-extracted receipt text.

## Features

- **Multi-output Classification**: Simultaneously predicts both merchant name and location
- **TF-IDF Vectorization**: Converts text into numerical features using n-grams (1-3)
- **Random Forest Classifier**: Robust ensemble method for accurate predictions
- **Confidence Scores**: Returns confidence levels for predictions
- **Easy to Use**: Simple API for training and prediction

## Project Structure

```
.
├── sample_data.csv          # Sample training data
├── train_model.py           # Main training script
├── predict.py               # Interactive prediction script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Prepare Your Data

Create a CSV file with three columns:
- `header_text`: The receipt header text (from OCR)
- `merchant_label`: The merchant name label
- `location_label`: The location label

Example:
```csv
header_text,merchant_label,location_label
"MYDIN WHOLESALE HYPERMARKET BUKIT MERTAJAM",MYDIN,BUKIT_MERTAJAM
"JAYA GROCER KL EAST MALL",JAYA_GROCER,KL_EAST_MALL
```

### 2. Train the Model

Run the training script:
```bash
python train_model.py
```

This will:
- Load and preprocess the training data
- Train the model using TF-IDF + Random Forest
- Evaluate the model performance
- Save the trained model to `receipt_ner_model.pkl`

### 3. Make Predictions

#### Interactive Mode
```bash
python predict.py
```

#### Programmatic Usage
```python
from train_model import ReceiptNERModel

# Load model
model = ReceiptNERModel()
model.load_model('receipt_ner_model.pkl')

# Predict
result = model.predict("MYDIN WHOLESALE HYPERMARKET BUKIT MERTAJAM")
print(result)
# Output: {
#   'merchant': 'MYDIN',
#   'location': 'BUKIT_MERTAJAM',
#   'merchant_confidence': 0.95,
#   'location_confidence': 0.92
# }
```

## Model Details

### Algorithm
- **Vectorizer**: TfidfVectorizer with 1-3 n-grams
- **Classifier**: Random Forest with 100 estimators
- **Multi-output**: Uses MultiOutputClassifier for simultaneous merchant and location prediction

### Preprocessing
- Removes extra whitespace
- Normalizes special characters
- Lowercase conversion
- Unicode normalization

### Features
- Uses up to 1000 TF-IDF features
- Captures unigrams, bigrams, and trigrams
- Character and word-level patterns

## Adding More Training Data

To improve model accuracy:

1. Add more examples to `sample_data.csv`
2. Include variations of merchant names:
   - Different formatting (uppercase, lowercase, mixed)
   - Common OCR errors
   - Different location descriptions
3. Re-train by running `python train_model.py`

## Integration with OCR

```python
import pytesseract
from PIL import Image
from train_model import ReceiptNERModel

# Load model
ner_model = ReceiptNERModel()
ner_model.load_model('receipt_ner_model.pkl')

# Extract text from receipt image
image = Image.open('receipt.jpg')
ocr_text = pytesseract.image_to_string(image)

# Get first few lines (usually contains header)
header_text = ' '.join(ocr_text.split('\n')[:3])

# Extract merchant and location
result = ner_model.predict(header_text)
print(f"Merchant: {result['merchant']}")
print(f"Location: {result['location']}")
```

## Performance Tips

1. **More Training Data**: Add at least 50-100 examples per merchant/location
2. **Balanced Dataset**: Ensure each merchant and location appears multiple times
3. **Variation**: Include different text formats and OCR variations
4. **Clean Data**: Remove severely corrupted OCR results from training data

## Advanced: Using Pre-trained Models

For better performance with limited data, consider using:
- **spaCy NER**: Train custom entity recognition
- **BERT-based models**: Fine-tune transformer models
- **GPT models**: Use few-shot learning

Example spaCy integration available upon request.

## License

MIT License

## Support

For issues or questions, please open an issue in the repository.
