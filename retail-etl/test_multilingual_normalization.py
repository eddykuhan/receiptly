"""
Test multilingual normalization for product names.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from receiptly_core import normalize_text

# Test cases
test_cases = [
    ("KNIFE COOKING OIL 2KG", "knife cooking oil 2kg"),
    ("KNIFE MINYAK MASAK 2KG", "knife cooking oil 2kg"),  # Should match after translation
    ("Minyak Goreng Cap Burung 1L", "cooking oil cap burung 1l"),
    ("SUSU DUTCH LADY FULL CREAM", "milk dutch lady full cream"),
    ("Tepung Gandum 1KG", "wheat flour 1kg"),
    ("Gula Pasir Putih", "granulated sugar putih"),
    ("Roti Gardenia White Bread", "bread gardenia white bread"),
]

print("=" * 80)
print("Multilingual Normalization Test")
print("=" * 80)

for original, expected in test_cases:
    normalized = normalize_text(original)
    match_status = "✓" if normalized == expected else "✗"
    
    print(f"\n{match_status} Original:   '{original}'")
    print(f"  Normalized: '{normalized}'")
    if normalized != expected:
        print(f"  Expected:   '{expected}'")

# Test the specific case mentioned by user
print("\n" + "=" * 80)
print("User's Specific Case:")
print("=" * 80)

item1 = "KNIFE COOKING OIL 2KG"
item2 = "KNIFE MINYAK MASAK 2KG"

norm1 = normalize_text(item1)
norm2 = normalize_text(item2)

print(f"\nItem 1: '{item1}'")
print(f"  → '{norm1}'")
print(f"\nItem 2: '{item2}'")
print(f"  → '{norm2}'")
print(f"\nMatch: {norm1 == norm2} {'✓' if norm1 == norm2 else '✗'}")
