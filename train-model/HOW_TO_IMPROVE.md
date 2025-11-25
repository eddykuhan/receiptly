# How to Improve the Model

This guide explains how to improve model accuracy by adding more training data.

## Quick Start

### 1. Add More Data to CSV

Edit `sample_data.csv` and add more rows:

```csv
header_text,merchant_label,location_label
"MYDIN WHOLESALE HYPERMARKET BUKIT MERTAJAM",MYDIN,BUKIT_MERTAJAM
"MYDIN BUKIT MERTAJAM",MYDIN,BUKIT_MERTAJAM
"mydin wholesale bukit mertajam",MYDIN,BUKIT_MERTAJAM
```

**Important**: Include variations like:
- Different capitalization
- Common OCR errors (l vs 1, O vs 0)
- Shortened versions
- With/without special characters
- Different word orders

### 2. Re-train the Model

```bash
source venv/bin/activate
python train_model.py
```

### 3. Test Your Model

```bash
python predict.py
```

## Adding New Merchants/Locations

Let's say you want to add a new merchant "LOTUS" with location "IPOH":

1. Add examples to `sample_data.csv`:
```csv
"LOTUS SUPERMARKET IPOH",LOTUS,IPOH
"LOTUS IPOH BRANCH",LOTUS,IPOH
"LOTUS SUPERCENTRE IPOH",LOTUS,IPOH
```

2. Re-train:
```bash
source venv/bin/activate
python train_model.py
```

## Data Collection Tips

### 1. Collect Real OCR Output

The best training data comes from actual OCR results:

```python
# Example: Save OCR results for training
from train_model import ReceiptNERModel

# After OCR processing
ocr_text = "MYDIN WHOLESALE BUKIT MERTAJAM"
merchant = "MYDIN"  # Manual label
location = "BUKIT_MERTAJAM"  # Manual label

# Append to CSV
with open('sample_data.csv', 'a') as f:
    f.write(f'"{ocr_text}",{merchant},{location}\n')
```

### 2. Include Common Errors

OCR often makes mistakes. Include these in training:

```csv
"MYD1N WHOLESALE",MYDIN,BUKIT_MERTAJAM
"JAYA GR0CER",JAYA_GROCER,KL_EAST_MALL
"STARBUCK5 COFFEE",STARBUCKS,PAVILION_KL
```

### 3. Minimum Examples per Class

For good accuracy:
- **Minimum**: 10 examples per merchant/location
- **Recommended**: 50+ examples per merchant/location
- **Production**: 100+ examples per merchant/location

## Data Quality Checklist

✅ **DO**:
- Include variations in spacing, capitalization
- Add OCR errors you commonly see
- Use real OCR output when possible
- Balance your dataset (similar number of examples per class)
- Include abbreviated versions

❌ **DON'T**:
- Add completely wrong labels
- Include severely corrupted text
- Use synthetic data only
- Ignore class imbalance

## Automated Data Collection

Create a script to collect training data from your production system:

```python
# data_collector.py
import csv
from datetime import datetime

class TrainingDataCollector:
    def __init__(self, csv_file='training_data.csv'):
        self.csv_file = csv_file
    
    def add_example(self, ocr_text, merchant, location):
        """Add a new training example"""
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ocr_text, merchant, location])
        print(f"Added: {merchant} @ {location}")
    
    def manual_labeling_session(self):
        """Interactive session to label OCR results"""
        print("Training Data Labeling Session")
        print("Enter 'q' to quit\n")
        
        while True:
            ocr_text = input("OCR Text: ").strip()
            if ocr_text.lower() == 'q':
                break
            
            merchant = input("Merchant Label: ").strip().upper()
            location = input("Location Label: ").strip().upper()
            
            self.add_example(ocr_text, merchant, location)
            print("✓ Added\n")

# Usage
collector = TrainingDataCollector()
collector.manual_labeling_session()
```

## Handling Confidence Scores

Low confidence scores indicate the model is uncertain:

```python
result = model.predict(text)

if result['merchant_confidence'] < 0.7:
    # Low confidence - might want to:
    # 1. Show user for manual verification
    # 2. Use fallback logic
    # 3. Mark for review
    print("⚠️ Low confidence prediction")
```

## Incremental Training

When you have new data:

```python
import pandas as pd

# Load existing data
old_data = pd.read_csv('sample_data.csv')

# Load new data
new_data = pd.read_csv('new_training_data.csv')

# Combine
combined = pd.concat([old_data, new_data])
combined = combined.drop_duplicates()  # Remove duplicates

# Save
combined.to_csv('sample_data.csv', index=False)

# Re-train
model = ReceiptNERModel()
model.train('sample_data.csv')
model.save_model()
```

## Model Performance Monitoring

Track your model's performance over time:

```python
# performance_tracker.py
import json
from datetime import datetime

def log_prediction(text, prediction, is_correct):
    """Log predictions for monitoring"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'text': text,
        'prediction': prediction,
        'correct': is_correct
    }
    
    with open('prediction_log.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

# Usage
result = model.predict(receipt_text)
is_correct = verify_with_user(result)  # Your verification logic
log_prediction(receipt_text, result, is_correct)
```

## Advanced: Active Learning

Collect the most valuable training examples:

```python
# Prioritize low-confidence predictions for manual labeling
def get_uncertain_predictions(threshold=0.7):
    """Get predictions below confidence threshold"""
    uncertain_cases = []
    
    # From your prediction logs
    with open('prediction_log.jsonl') as f:
        for line in f:
            pred = json.loads(line)
            if (pred['prediction']['merchant_confidence'] < threshold or
                pred['prediction']['location_confidence'] < threshold):
                uncertain_cases.append(pred)
    
    return uncertain_cases

# Review and add to training data
uncertain = get_uncertain_predictions()
print(f"Found {len(uncertain)} uncertain predictions")
# Manually review and add correct labels to training data
```

## Testing Your Model

Always test with held-out data:

```python
from sklearn.model_selection import train_test_split
import pandas as pd

# Load data
df = pd.read_csv('sample_data.csv')

# Split
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

# Save splits
train_df.to_csv('train_data.csv', index=False)
test_df.to_csv('test_data.csv', index=False)

# Train only on training data
model = ReceiptNERModel()
model.train('train_data.csv')

# Test on test data
# ... testing code ...
```

## Summary Checklist

Before deploying to production:

- [ ] Collected at least 50 examples per merchant/location
- [ ] Included OCR error variations
- [ ] Balanced dataset across all classes
- [ ] Tested on held-out data
- [ ] Achieved >80% accuracy on test set
- [ ] Implemented confidence thresholds
- [ ] Set up monitoring and logging
- [ ] Created a data collection pipeline

## Need Help?

Common issues:

**Low accuracy?**
- Add more training data
- Include more variations
- Check data quality

**New merchant not recognized?**
- Need at least 10 examples
- Include variations
- Re-train model

**Confidence scores too low?**
- Add more examples
- Check for OCR quality issues
- Consider ensemble methods
