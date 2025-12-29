import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.canonicalizer import canonicalize_item
from models.llm_client import LLMClient

async def test_standardization():
    test_items = [
        "DL UHT FULL CREAM 1L",
        "FARM FRESH PURE MILK 1L",
        "MILO POWDER 1KG",
        "KACANG HITAM 400G",
        "UDANG HARIMAU XL"
    ]
    
    print("=== Testing Vector RAG Standardization ===")
    for item in test_items:
        print(f"\nRAW: {item}")
        try:
            canonical = await canonicalize_item(item)
            print(f"CANONICAL: {canonical}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_standardization())
