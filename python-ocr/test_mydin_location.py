from thefuzz import fuzz

# The OCR text reported by the user (with typos)
ocr_line = "MYDIN WHORESALE HYPERMARKET BUKIT HERTAJAM"
ocr_line_lower = ocr_line.lower()

# The known variations for Mydin
variations = ['mydin', 'mydin mohamed holdings', 'mydin hypermarket']

print(f"Testing fuzzy matching for line: '{ocr_line}'")
print("-" * 50)

for variation in variations:
    # Test token_set_ratio (used for long names)
    score_token_set = fuzz.token_set_ratio(variation, ocr_line_lower)
    
    print(f"Variation: '{variation}'")
    print(f"  token_set_ratio: {score_token_set}")
    
    if score_token_set > 80:
        print("  -> MATCH FOUND (Threshold > 80)")
    else:
        print("  -> NO MATCH")
    print("-" * 20)
