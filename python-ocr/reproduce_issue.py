from thefuzz import fuzz

# The OCR text reported by the user
ocr_line = "APOIN MOHAMED HOLDINGS BHD"
ocr_line_lower = ocr_line.lower()

# The known variations for Mydin from store_name_extractor.py
variations = ['mydin', 'mydin mohamed holdings', 'mydin hypermarket']

print(f"Testing fuzzy matching for line: '{ocr_line}'")
print("-" * 50)

for variation in variations:
    # Test token_set_ratio (used for long names)
    score_token_set = fuzz.token_set_ratio(variation, ocr_line_lower)
    
    # Test ratio (used for short names, just for comparison)
    score_ratio = fuzz.ratio(variation, ocr_line_lower)
    
    print(f"Variation: '{variation}'")
    print(f"  token_set_ratio: {score_token_set}")
    print(f"  ratio:           {score_ratio}")
    
    if score_token_set > 80:
        print("  -> MATCH FOUND (Threshold > 80)")
    else:
        print("  -> NO MATCH")
    print("-" * 20)
