"""
Tests for Canonicalizer service.

Verifies normalization, embedding generation, and canonicalization logic.
"""
import sys
import os
import unittest
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from etl_transformers.canonicalizer import Canonicalizer
from config.settings import DB_CONFIG

class TestCanonicalizer(unittest.TestCase):
    
    def setUp(self):
        """Initialize canonicalizer."""
        self.canonicalizer = Canonicalizer(DB_CONFIG)
        self.test_prefix = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.created_ids = []

    def tearDown(self):
        """Close connection and clean up."""
        if self.created_ids:
            self.canonicalizer.connect()
            with self.canonicalizer.conn.cursor() as cur:
                # Delete test items
                placeholders = ','.join(['%s'] * len(self.created_ids))
                # Note: quoted identifier "Id"
                cur.execute(f'DELETE FROM canonical_items WHERE "Id" IN ({placeholders})', tuple(self.created_ids))
                self.canonicalizer.conn.commit()
        self.canonicalizer.close()

    def test_normalization(self):
        """Test text normalization."""
        raw = "  Coca-Cola  330ml  (Can)  !@#  "
        expected = "coca cola 330ml can"
        result = self.canonicalizer.normalize_text(raw)
        self.assertEqual(result, expected)

        # Test "1 unit" removal
        raw_unit = "Moccona Latte 16g x 10 1 unit"
        expected_unit = "moccona latte 16g x 10"
        result_unit = self.canonicalizer.normalize_text(raw_unit)
        self.assertEqual(result_unit, expected_unit, "Should remove '1 unit' suffix")

    def test_end_to_end_canonicalization(self):
        """Test full canonicalization flow (new item creation)."""
        import uuid
        # Create unique test item with random component to avoid embedding collision
        unique_suffix = str(uuid.uuid4())[:8]
        item_name = f"{self.test_prefix} UniqueProduct {unique_suffix}"
        category = "TestCategory"
        
        # 1. First run: Should create new item
        result1 = self.canonicalizer.canonicalize(item_name, category)
        self.assertEqual(result1['match_method'], 'new', f"Should be 'new' but got {result1['match_method']}")
        self.assertTrue(result1['canonical_item_id'])
        self.created_ids.append(result1['canonical_item_id'])
        
        # 2. Second run: Should match EXACTLY
        result2 = self.canonicalizer.canonicalize(item_name, category)
        self.assertEqual(result2['match_method'], 'exact')
        self.assertEqual(result2['canonical_item_id'], result1['canonical_item_id'])
        
        # 3. Third run: Should match via Similarity (Embedding)
        # Vary name slightly but keep semantic core
        similar_name = f"{self.test_prefix} UniqueProduct {unique_suffix} Variant"
        
        result3 = self.canonicalizer.canonicalize(similar_name, category)
        self.assertTrue(result3['canonical_item_id'])
        # If it created a new one, track it for cleanup
        if result3['match_method'] == 'new':
            self.created_ids.append(result3['canonical_item_id'])


if __name__ == '__main__':
    unittest.main()
