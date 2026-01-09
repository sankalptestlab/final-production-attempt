"""
Data extraction utilities
Extract GST, PAN, amounts, etc. from text in multiple languages
"""

import re
from typing import Optional

def extract_gstin(text: str) -> Optional[str]:
    """
    Extract GSTIN from text using regex
    Works across multiple languages as GSTIN format is standardized
    """
    pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_pan(text: str) -> Optional[str]:
    """
    Extract PAN from text using regex
    Works across multiple languages as PAN format is standardized
    """
    pattern = r'\b[A-Z]{5}\d{4}[A-Z]{1}\b'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_amount(text: str) -> Optional[float]:
    """
    Extract loan amount from text
    Supports multiple languages and formats:
    - English: "50 lakh", "5 crore", "50L", "5cr"
    - Hindi: "50 लाख", "5 करोड़"
    """
    patterns = [
        # English patterns
        (r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)\b', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b', 100),
        (r'(\d+(?:\.\d+)?)\s*million', 10),
        # Hindi patterns
        (r'(\d+(?:\.\d+)?)\s*(?:लाख|लाखों)', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:करोड़|करोड़ों)', 100),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1)) * multiplier

    return None

def extract_tenure(text: str) -> Optional[int]:
    """
    Extract tenure in months from text
    Supports English and Hindi
    """
    # Look for explicit months
    month_patterns = [
        r'(\d+)\s*(?:month|months|महीने|महीनों)',
    ]

    for pattern in month_patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    # Look for years and convert to months
    year_patterns = [
        (r'(\d+)\s*(?:year|years|yr|yrs|साल|वर्ष)', 12),
    ]

    for pattern, multiplier in year_patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1)) * multiplier

    return None
