"""
Receiptly Core - Shared canonicalization library.

Provides attribute extraction, matching, and candidate generation
for product canonicalization across receipt processing and retail ETL.
"""

from .attribute_extractor import AttributeExtractor
from .matcher import AmazonStyleMatcher
from .candidate_generator import CandidateGenerator
from .normalizer import normalize_text

__version__ = "0.1.0"

__all__ = [
    "AttributeExtractor",
    "AmazonStyleMatcher", 
    "CandidateGenerator",
    "normalize_text",
]
