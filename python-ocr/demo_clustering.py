import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# 1. The Data
data = {
  "items": [
    { "itemId": "1", "itemName": "FARM FRESH PURE FRESH" },
    { "itemId": "2", "itemName": "3M COMMAND MINI" },
    { "itemId": "3", "itemName": "BROCOLLI" },
    { "itemId": "4", "itemName": "CHIC THI" },
    { "itemId": "5", "itemName": "CURRY LEAF 15G" },
    { "itemId": "6", "itemName": "CUTTER KNIFE H" },
    { "itemId": "7", "itemName": "ELBA WALL FAN" },
    { "itemId": "8", "itemName": "FARM FRESH FRS" },
    { "itemId": "9", "itemName": "FRENCH BEAN 25" },
    { "itemId": "10", "itemName": "GUAVA LO" },
    { "itemId": "11", "itemName": "GUAVA SE" },
    { "itemId": "12", "itemName": "LUSHIOUS\nVALUE" },
    { "itemId": "13", "itemName": "MEN SLIPPER H-" },
    { "itemId": "14", "itemName": "MYRASA NOC, 1." },
    { "itemId": "15", "itemName": "PANTENE CONDIT" },
    { "itemId": "16", "itemName": "", }, # Empty name
    { "itemId": "17", "itemName": "BLUEBERRY 125G C12" },
    { "itemId": "18", "itemName": "CADBURY ROSES TUB PS 600G" },
    { "itemId": "19", "itemName": "HALBA CAMPUR (125G)" },
    { "itemId": "20", "itemName": "MUSTARD SEED (BIJI SAWI) (200G)" },
    { "itemId": "21", "itemName": "WHITE SESAME SEED (BIJIAN PUTIH) (125G)" },
    { "itemId": "22", "itemName": "" },
    { "itemId": "23", "itemName": "BLACK PEPPER CHICKEN\nLEG BONELESS" },
    { "itemId": "24", "itemName": "JAMAICAN JECK C.LEG B'LESS" },
    { "itemId": "25", "itemName": "KACANG HITAM (+/- 400G) *1" },
    { "itemId": "26", "itemName": "KACANG TANAH CHINA (+/- 400G) *1" },
    { "itemId": "27", "itemName": "KO UDANG HARIMAU FARM XXL (CC)" },
    { "itemId": "28", "itemName": "LK FRESH NATURAL FARM NO ANTI&GROWTH *1" },
    { "itemId": "29", "itemName": "TILLAMOOK CHOCOLATE PEANUT 480Z" },
    { "itemId": "30", "itemName": "WHOLE CHICKEN STANDARD" },
    { "itemId": "31", "itemName": "CP6_CONNOR" }
  ]
}

items = [i for i in data["items"] if i["itemName"].strip()]
names = [i["itemName"] for i in items]

print(f"Processing {len(names)} items...")

# 2. Vectorization (TF-IDF)
# Analyzer='char_wb' helps with typos and partial matches by looking at character n-grams
vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
tfidf_matrix = vectorizer.fit_transform(names)

# 3. Clustering
# Distance threshold: Lower means stricter matching. 
# Cosine distance = 1 - cosine_similarity. 
# If similarity is 0.7, distance is 0.3.
# Let's try a threshold that allows for "FARM FRESH FRS" and "FARM FRESH PURE FRESH" to match.
clustering = AgglomerativeClustering(
    n_clusters=None, 
    distance_threshold=0.6, # Adjust this based on testing
    metric='cosine', 
    linkage='average'
)
clustering.fit(tfidf_matrix.toarray())

# 4. Group Results
clusters = {}
for idx, label in enumerate(clustering.labels_):
    if label not in clusters:
        clusters[label] = []
    clusters[label].append(names[idx])

# 5. Print Groups with > 1 item
print("\n--- Found Clusters ---")
for label, group in clusters.items():
    if len(group) > 1:
        print(f"Cluster {label}:")
        for name in group:
            print(f"  - {name}")

# Check specific pair
print("\n--- Specific Check ---")
pair = ["FARM FRESH PURE FRESH", "FARM FRESH FRS"]
vecs = vectorizer.transform(pair)
sim = cosine_similarity(vecs[0], vecs[1])[0][0]
print(f"Similarity between '{pair[0]}' and '{pair[1]}': {sim:.4f}")
