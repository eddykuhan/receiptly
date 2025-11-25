import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import joblib

# ----------------------------------------------------
# 1. Load CSV Dataset
# ----------------------------------------------------
CSV_PATH = "sample_data.csv"   # <= change if needed

df = pd.read_csv(CSV_PATH)

print("Loaded dataset shape:", df.shape)
print(df.head())

# ----------------------------------------------------
# 2. Load Embedding Model
# ----------------------------------------------------
print("\nLoading embedding model (MiniLM)...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Convert text → embeddings
print("Encoding header_text to embeddings...")
X = embedder.encode(df["header_text"].tolist(), show_progress_bar=True)

# Labels
y_merchant = df["merchant_label"]
y_location = df["location_label"]

# ----------------------------------------------------
# 3. Split Train / Test
# ----------------------------------------------------
X_train_m, X_test_m, y_train_m, y_test_m = train_test_split(
    X, y_merchant, test_size=0.2, random_state=42
)

X_train_l, X_test_l, y_train_l, y_test_l = train_test_split(
    X, y_location, test_size=0.2, random_state=42
)

# ----------------------------------------------------
# 4. Train Merchant Classifier
# ----------------------------------------------------
print("\nTraining MERCHANT classifier...")
clf_merchant = LogisticRegression(max_iter=3000)
clf_merchant.fit(X_train_m, y_train_m)

merchant_preds = clf_merchant.predict(X_test_m)

print("\nMERCHANT Classification Report:")
print(classification_report(y_test_m, merchant_preds))
print("MERCHANT Accuracy:", accuracy_score(y_test_m, merchant_preds))

# ----------------------------------------------------
# 5. Train Location Classifier
# ----------------------------------------------------
print("\nTraining LOCATION classifier...")
clf_location = LogisticRegression(max_iter=3000)
clf_location.fit(X_train_l, y_train_l)

location_preds = clf_location.predict(X_test_l)

print("\nLOCATION Classification Report:")
print(classification_report(y_test_l, location_preds))
print("LOCATION Accuracy:", accuracy_score(y_test_l, location_preds))

# ----------------------------------------------------
# 6. Save Models to Disk
# ----------------------------------------------------
print("\nSaving models...")

joblib.dump(clf_merchant, "merchant_classifier.pkl")
joblib.dump(clf_location, "location_classifier.pkl")
joblib.dump(embedder, "embedding_model.pkl")

print("\nSaved:")
print(" - merchant_classifier.pkl")
print(" - location_classifier.pkl")
print(" - embedding_model.pkl")
