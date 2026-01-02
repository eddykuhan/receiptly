"""
Amazon-style Matcher for canonicalization.

Implements hard constraints + weighted scoring to select best match
from candidate pool.
"""
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer
import numpy as np
import torch


class AmazonStyleMatcher:
    """
    Match items using Amazon's approach:
    1. Hard constraints (reject non-viable matches)
    2. Weighted scoring across multiple attributes
    3. Confidence threshold (0.75 minimum)
    """
    
    def __init__(self, embedding_model: Optional[SentenceTransformer] = None):
        """
        Initialize with optional embedding model.
        
        Args:
            embedding_model: SentenceTransformer for text similarity
                            (defaults to 'all-MiniLM-L6-v2')
        """
        if embedding_model is None:
            # Auto-detect and use GPU if available
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            self.embedding_model.encode(['test'], show_progress_bar=False)  # Set default
            print(f"[Matcher] Using device: {device}")
        else:
            self.embedding_model = embedding_model
    
    def find_best_match(
        self,
        query_attributes: Dict,
        candidates: List[Dict],
        threshold: float = 0.75
    ) -> Tuple[Optional[Dict], float, Dict]:
        """
        Find best match from candidates using hard constraints + scoring.
        
        Args:
            query_attributes: Extracted attributes from input item
            candidates: List of candidate canonical items
            threshold: Minimum score to accept match (default 0.75)
            
        Returns:
            Tuple of (best_match, score, score_breakdown)
            best_match is None if no candidate passes threshold
        """
        if not candidates:
            return None, 0.0, {}
        
        # Step 1: Apply hard constraints
        viable_candidates = self._apply_hard_constraints(
            query_attributes, candidates
        )
        
        if not viable_candidates:
            return None, 0.0, {'reason': 'All candidates rejected by hard constraints'}
        
        # Step 2: Score viable candidates
        best_match = None
        best_score = 0.0
        best_breakdown = {}
        
        for candidate in viable_candidates:
            score, breakdown = self._calculate_match_score(
                query_attributes, candidate
            )
            
            if score > best_score:
                best_score = score
                best_match = candidate
                best_breakdown = breakdown
        
        # Step 3: Check threshold
        if best_score < threshold:
            return None, best_score, best_breakdown
        
        return best_match, best_score, best_breakdown
    
    def _apply_hard_constraints(
        self,
        query_attrs: Dict,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Apply hard constraints to filter candidates.
        Constraints:
        1. Size mismatch >5% → REJECT
        2. Brand conflict (different brands) → REJECT
        3. Category mismatch (if available) → REJECT
        4. Pack count mismatch → REJECT (multi-pack vs single pack are different products)
        
        Args:
            query_attrs: Query attributes
            candidates: Candidate items
            
        Returns:
            Filtered list of viable candidates
        """
        viable = []
        
        for candidate in candidates:
            # Constraint 1: Pack count must match (multi-packs are different products)
            if query_attrs.get('pack_count') and candidate.get('pack_count'):
                query_pack = int(query_attrs['pack_count'])
                candidate_pack = int(candidate['pack_count'])
                
                # Different pack counts → reject (e.g., 6-pack vs single)
                if query_pack != candidate_pack:
                    continue
            
            # Constraint 2: Size must match within 5% tolerance
            if query_attrs.get('size_normalized') and candidate.get('size_normalized'):
                query_size = float(query_attrs['size_normalized'])
                candidate_size = float(candidate['size_normalized'])
                
                # Different units → reject
                if query_attrs.get('size_unit') != candidate.get('size_unit'):
                    continue
                
                # Size difference > 5% → reject
                size_diff = abs(query_size - candidate_size) / query_size
                if size_diff > 0.05:
                    continue
            
            # Constraint 3: Brand must match (if both present)
            if query_attrs.get('brand') and candidate.get('brand'):
                query_brand = query_attrs['brand'].lower()
                candidate_brand = candidate['brand'].lower()
                
                # Exact match required for brand
                if query_brand != candidate_brand:
                    continue
            
            # Constraint 4: Category must match (if both present and not unknown)
            # DISABLED: Categories vary too much across stores (e.g., "Beverages" vs "Instant Coffee")
            # Brand + Size + Pack Count are sufficient hard constraints
            # Category will still contribute to scoring
            # if query_attrs.get('category') and candidate.get('category'):
            #     query_category = query_attrs['category'].lower()
            #     candidate_category = candidate['category'].lower()
            #     
            #     # Skip check if query category is generic/unknown
            #     if query_category not in ['unknown', 'all products', 'general']:
            #         if query_category != candidate_category:
            #             continue
            
            # Passed all constraints
            viable.append(candidate)
        
        return viable
    
    def _calculate_match_score(
        self,
        query_attrs: Dict,
        candidate: Dict
    ) -> Tuple[float, Dict]:
        """
        Calculate weighted match score.
        Weights (Amazon-inspired):
        - Brand: 25%
        - Size: 30%
        - Text similarity: 25%
        - Token overlap: 10%
        - Price: 10%
        
        Args:
            query_attrs: Query attributes
            candidate: Candidate item
            
        Returns:
            Tuple of (total_score, score_breakdown)
        """
        scores = {}
        
        # 1. Brand score (25%)
        brand_score = self._score_brand(
            query_attrs.get('brand'),
            candidate.get('brand')
        )
        scores['brand'] = brand_score * 0.25
        
        # 2. Size score (30%)
        size_score = self._score_size(
            query_attrs.get('size_normalized'),
            candidate.get('size_normalized')
        )
        scores['size'] = size_score * 0.30
        
        # 3. Text similarity score (25%)
        text_score = self._score_text_similarity(
            query_attrs.get('item_name', ''),
            candidate.get('item_name', '')
        )
        scores['text_similarity'] = text_score * 0.25
        
        # 4. Token overlap score (10%)
        token_score = self._score_token_overlap(
            query_attrs.get('name_tokens', []),
            candidate.get('name_tokens', [])
        )
        scores['token_overlap'] = token_score * 0.10
        
        # 5. Price score (10%)
        price_score = self._score_price(
            query_attrs.get('price'),
            candidate.get('price')
        )
        scores['price'] = price_score * 0.10
        
        # Total score
        total_score = sum(scores.values())
        
        return total_score, scores
    
    def _score_brand(self, query_brand: Optional[str], candidate_brand: Optional[str]) -> float:
        """Score brand match (0.0 to 1.0)."""
        if not query_brand or not candidate_brand:
            return 0.5  # Neutral score if missing
        
        if query_brand.lower() == candidate_brand.lower():
            return 1.0
        
        # Fuzzy match for typos
        similarity = fuzz.ratio(query_brand.lower(), candidate_brand.lower()) / 100
        return similarity
    
    def _score_size(self, query_size: Optional[float], candidate_size: Optional[float]) -> float:
        """Score size match (0.0 to 1.0)."""
        if query_size is None or candidate_size is None:
            return 0.5  # Neutral score if missing
        
        # Convert to float to handle Decimal from database
        query_size = float(query_size)
        candidate_size = float(candidate_size)
        
        # Exact match
        if query_size == candidate_size:
            return 1.0
        
        # Gradual penalty for size difference
        diff = abs(query_size - candidate_size) / query_size
        
        if diff <= 0.01:  # 1% tolerance
            return 0.95
        elif diff <= 0.03:  # 3% tolerance
            return 0.85
        elif diff <= 0.05:  # 5% tolerance
            return 0.70
        else:
            # Should be filtered by hard constraints, but just in case
            return max(0.0, 1.0 - diff)
    
    def _score_text_similarity(self, query_text: str, candidate_text: str) -> float:
        """Score text similarity using embeddings (0.0 to 1.0)."""
        if not query_text or not candidate_text:
            return 0.0
        
        # Normalize text: remove hyphens, extra spaces for better matching
        query_normalized = ' '.join(query_text.replace('-', ' ').split())
        candidate_normalized = ' '.join(candidate_text.replace('-', ' ').split())
        
        # Generate embeddings
        query_emb = self.embedding_model.encode([query_normalized], show_progress_bar=False)[0]
        candidate_emb = self.embedding_model.encode([candidate_normalized], show_progress_bar=False)[0]
        
        # Cosine similarity
        similarity = np.dot(query_emb, candidate_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(candidate_emb)
        )
        
        # Normalize to 0-1 range (cosine similarity can be -1 to 1)
        return (similarity + 1) / 2
    
    def _score_token_overlap(self, query_tokens: List[str], candidate_tokens: List[str]) -> float:
        """Score token overlap using Jaccard similarity (0.0 to 1.0)."""
        if not query_tokens or not candidate_tokens:
            return 0.0
        
        # Normalize tokens: remove hyphens and split hyphenated words
        def normalize_tokens(tokens):
            normalized = []
            for token in tokens:
                # Split hyphenated words and add both forms
                if '-' in token:
                    normalized.extend(token.split('-'))
                normalized.append(token.replace('-', ''))
            return normalized
        
        query_set = set(normalize_tokens(query_tokens))
        candidate_set = set(normalize_tokens(candidate_tokens))
        
        intersection = len(query_set & candidate_set)
        union = len(query_set | candidate_set)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _score_price(self, query_price: Optional[float], candidate_price: Optional[float]) -> float:
        """Score price similarity (0.0 to 1.0)."""
        if query_price is None or candidate_price is None:
            return 0.5  # Neutral score if missing
        
        # Prices can vary by location/promotion, so use soft matching
        diff = abs(query_price - candidate_price) / candidate_price
        
        if diff <= 0.05:  # 5% tolerance
            return 1.0
        elif diff <= 0.10:  # 10% tolerance
            return 0.8
        elif diff <= 0.20:  # 20% tolerance
            return 0.6
        elif diff <= 0.30:  # 30% tolerance
            return 0.4
        else:
            return max(0.0, 1.0 - diff)


# Example usage and testing
if __name__ == "__main__":
    matcher = AmazonStyleMatcher()
    
    # Test case: Receipt item "Farm Fresh Pure Fresh /"
    query_attrs = {
        'item_name': 'Farm Fresh Pure Fresh /',
        'brand': 'Farm Fresh',
        'size_normalized': 2.0,
        'size_unit': 'L',
        'name_tokens': ['farm', 'fresh', 'pure'],
        'category': 'Dairy',
        'price': 11.50
    }
    
    # Mock candidates
    candidates = [
        {
            'id': 1,
            'item_name': 'Farm Fresh Pure Fresh Milk 2L',
            'brand': 'Farm Fresh',
            'size': '2L',
            'size_normalized': 2.0,
            'size_unit': 'L',
            'name_tokens': ['farm', 'fresh', 'pure', 'milk'],
            'category': 'Dairy',
            'price': 11.90
        },
        {
            'id': 2,
            'item_name': 'Farm Fresh Low Fat Milk 1.5L',
            'brand': 'Farm Fresh',
            'size': '1.5L',
            'size_normalized': 1.5,
            'size_unit': 'L',
            'name_tokens': ['farm', 'fresh', 'low', 'fat', 'milk'],
            'category': 'Dairy',
            'price': 9.50
        }
    ]
    
    best_match, score, breakdown = matcher.find_best_match(
        query_attrs, candidates, threshold=0.75
    )
    
    print("Matching Results:")
    print("=" * 80)
    print(f"Query: {query_attrs['item_name']}")
    print(f"\nBest Match: {best_match['item_name'] if best_match else 'None'}")
    print(f"Score: {score:.3f}")
    print(f"\nScore Breakdown:")
    for component, value in breakdown.items():
        print(f"  {component}: {value:.3f}")
