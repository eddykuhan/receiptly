"""
Text normalization utilities for product canonicalization.
"""
import re


def normalize_text(text: str) -> str:
    """
    Normalize product text for matching.
    
    Args:
        text: Raw product text
        
    Returns:
        Normalized text (lowercase, alphanumeric + spaces, cleaned)
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s1\sunit$', '', text)  # Remove "1 unit" suffix
    text = re.sub(r'\s+', ' ', text.strip())
    return text
