#!/usr/bin/env python3
"""
BilaBila Mart location scraper

Extracts location data from https://www.bilabila.co/our-locations
and saves to store-scraper/data/bilabila_locations.json
"""

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import httpx
import time

# Location data extracted from website (69 locations)
BILABILA_LOCATIONS = [
    {"name": "BilaBila Mart - 28 Mont' Kiara", "url": "https://maps.app.goo.gl/augt8HdNcSfmLS7j8"},
    {"name": "BilaBila Mart - Agile Bukit Bintang", "url": "https://share.google/m2WAw6uhOHtCbusH3"},
    {"name": "BilaBila Mart - Arte Cheras", "url": "https://maps.app.goo.gl/x48wHnDNSh6NLzit5"},
    {"name": "BilaBila Mart - Arte Mont Kiara", "url": "https://goo.gl/maps/uh79En3R7NhhYPKs5"},
    {"name": "BilaBila Mart - Asia Pacific University (APU)", "url": "https://maps.app.goo.gl/6zD3kPbiDVKnwLba6"},
    {"name": "BilaBila Mart - Aster Residences", "url": "https://maps.app.goo.gl/NekvLqPAeFz3c2C76"},
    {"name": "BilaBila Mart - Axon Bukit Bintang", "url": "https://maps.app.goo.gl/U1fXcWfHzf3PEakS6"},
    {"name": "BilaBila Mart - Bangsar Hill Park", "url": "https://share.google/rF3yWMn6ZRlxYRUkR"},
    {"name": "BilaBila Mart - Casa Green Bukit Jalil", "url": "https://maps.app.goo.gl/kYME9NVd3sZpKLBd8"},
    {"name": "BilaBila Mart - Ceylonz Suites", "url": "https://goo.gl/maps/UJK1VwFs1rtyudMr7"},
    {"name": "BilaBila Mart - Ceylon 2", "url": "https://goo.gl/maps/byZq6H5gabXwgdpM6"},
    {"name": "BilaBila Mart - Chambers KL", "url": "https://maps.app.goo.gl/XeAxy21YftRR2tPn6"},
    {"name": "BilaBila Mart - Cubic Botanical", "url": "https://maps.app.goo.gl/qD6fLpxGDaUXE3146"},
    {"name": "BilaBila Mart - Dorsett Bukit Bintang", "url": "https://share.google/dwcfaYCHBkRERkzcU"},
    {"name": "BilaBila Mart - Desa Green", "url": "https://goo.gl/maps/cCqDnfSHunuhUQtF9"},
    {"name": "BilaBila Mart - D'Ivo", "url": "https://share.google/6dhfBYUDMFinmpjU7"},
    {"name": "BilaBila Mart - Expressionz Suites", "url": "https://goo.gl/maps/VCKJD2us38kSXhEaA"},
    {"name": "BilaBila Mart - Hampton Damansara", "url": "https://maps.app.goo.gl/hqyuiM5ry7k8f7Bk8"},
    {"name": "BilaBila Mart - Impiana KLCC Hotel", "url": "https://goo.gl/maps/742eKdXQJP6B2FHs9"},
    {"name": "BilaBila Mart - Jalan Kasah", "url": "https://share.google/WbOtmydagoTq63aqO"},
    {"name": "BilaBila Mart - Kaleidoscope", "url": "https://maps.app.goo.gl/ZeAoJTeoA2Zik6Xk6"},
    {"name": "BilaBila Mart - Lavile KL", "url": "https://goo.gl/maps/2AD62hEppCrsL9kn8"},
    {"name": "BilaBila Mart - M Centura", "url": "https://g.co/kgs/1Tj7i7Z"},
    {"name": "BilaBila Mart - MH Platinum 2", "url": "https://maps.app.goo.gl/VERmptWE6j8sDvYv7"},
    {"name": "BilaBila Mart - Millerz Square (Level G)", "url": "https://maps.app.goo.gl/XEnC4xQiQMdZ1yYL7"},
    {"name": "BilaBila Mart - Millerz Square (Level 8)", "url": "https://goo.gl/maps/RPRhC4BJRq4L1Fyz7"},
    {"name": "BilaBila Mart - M Vertica", "url": "https://goo.gl/maps/QAJ81csTSCWAXLPn6"},
    {"name": "BilaBila Mart - M Vertica 2", "url": "https://goo.gl/maps/QAJ81csTSCWAXLPn6"},  # Same as M Vertica
    {"name": "BilaBila Mart - Neu Suites", "url": "https://goo.gl/maps/sS1JycNtswmFzzmk9"},
    {"name": "BilaBila Mart - Nest 2 Residence", "url": "https://share.google/3GT4gHbLANN45r7JJ"},
    {"name": "BilaBila Mart - Nidoz Residences", "url": "https://goo.gl/maps/7qqfzJUbvs9Zv2rE8"},
    {"name": "BilaBila Mart - Novum Bangsar South", "url": "https://goo.gl/maps/4E8VyPAHxBKXVmGh9"},
    {"name": "BilaBila Mart - Parc 3", "url": "https://g.co/kgs/zRX9GDG"},
    {"name": "BilaBila Mart - Platinum Arena", "url": "https://goo.gl/maps/KfVFhguTUchTpU3T9"},
    {"name": "BilaBila Mart - Regalia Suites", "url": "https://goo.gl/maps/WXWWdhx3R4jD9uuQ9"},
    {"name": "BilaBila Mart - Riveria City", "url": "https://share.google/ynX5eonWFA84Eap9R"},
    {"name": "BilaBila Mart - REXKL", "url": "https://goo.gl/maps/y1nUEg5pMKbJ1WDF7"},
    {"name": "BilaBila Mart - Riana South", "url": "https://maps.app.goo.gl/cc9B1Nvef91T4h2E7"},
    {"name": "BilaBila Mart - Savio Residences", "url": "https://maps.app.goo.gl/Nvrbj3vBpfXC4KEdA"},
    {"name": "BilaBila Mart - Scarletz Suites", "url": "https://goo.gl/maps/RPK7DjpE9v8WARt6A"},
    {"name": "BilaBila Mart - Seni Mont Kiara", "url": "https://maps.app.goo.gl/Ng8TsBLFd6FrwafS9"},
    {"name": "BilaBila Mart - Setia Bakti", "url": "https://maps.app.goo.gl/mxGXNvtHBBsUvUNi6"},
    {"name": "BilaBila Mart - Sky Awani 3", "url": "https://goo.gl/maps/6JaCcEZcUef2S3Kr5"},
    {"name": "BilaBila Mart - Sofiya Residences", "url": "https://maps.app.goo.gl/46PCGx64of3NpKri8"},
    {"name": "BilaBila Mart - South Brooks Condominium", "url": "https://maps.app.goo.gl/LQfWKiaRjA2UYv7G8"},
    {"name": "BilaBila Mart - South View Bangsar South", "url": "https://goo.gl/maps/RGrSADpmGQiPr99A6"},
    {"name": "BilaBila Mart - Suasana Bukit Ceylon", "url": "https://maps.app.goo.gl/9NfimUDUdY8ccDsy7"},
    {"name": "BilaBila Mart - Sunway Velocity 2", "url": "https://maps.app.goo.gl/VwMeXPDkDxPhjStD7"},
    {"name": "BilaBila Mart - Taman Seputeh", "url": "https://goo.gl/maps/LAFoxTgPrke197nC6"},
    {"name": "BilaBila Mart - TAR UMT", "url": "https://goo.gl/maps/uEBnLPPc4vpr6nZGA"},
    {"name": "BilaBila Mart - The Leafz", "url": "https://share.google/BLMWxNFuxX1l7G3b2"},
    {"name": "BilaBila Mart - The Robertson", "url": "https://goo.gl/maps/pxeF5zzJYbM7cf4Z8"},
    {"name": "BilaBila Mart - The Havre", "url": "https://goo.gl/maps/1MmJHEZNwPqw2Jk98"},
    {"name": "BilaBila Mart - The Valley Residences", "url": "https://maps.app.goo.gl/cR8vk5aHnWQJyXTV9"},
    {"name": "BilaBila Mart - Tria Seputeh", "url": "https://maps.app.goo.gl/DucgRakFcNDjnVgU6"},
    {"name": "BilaBila Mart - Tuan 2egasy", "url": "https://share.google/JDVI8BaSevqEeBnjW"},
    {"name": "BilaBila Mart - UCSI Residence 2", "url": "https://goo.gl/maps/gQf8aPXqp33xBXx3A"},
    {"name": "BilaBila Mart - Vogue Suites 1", "url": "https://goo.gl/maps/9jbNE5nTtmbPqeBA8"},
    {"name": "BilaBila Mart - Wisma Life Care", "url": "https://g.co/kgs/i8Dkxzg"},
    # Selangor locations
    {"name": "BilaBila Mart - AraTre' Residences", "url": "https://goo.gl/maps/BwjmmM9N8FqHLGn28"},
    {"name": "BilaBila Mart - Bandar Utama 4", "url": "https://goo.gl/maps/u2CyQsWbiRbZ6xBD8"},
    {"name": "BilaBila Mart - Canopy Hills", "url": "https://goo.gl/maps/cT8n1WCYdEBsepbm9"},
    {"name": "BilaBila Mart - Dian Residences", "url": "https://maps.app.goo.gl/s566sg4HRcDha4km6"},
    {"name": "BilaBila Mart - Empire City", "url": "https://goo.gl/maps/ZTKaGpsAdK2KUG5d6"},
    {"name": "BilaBila Mart - Equine Residence", "url": "https://goo.gl/maps/WAGzPaJ4qmD4Ev3E7"},
    {"name": "BilaBila Mart - Maisson", "url": "https://goo.gl/maps/THW4xCy4DjKE3LkPA"},
    {"name": "BilaBila Mart - Mossaz", "url": "https://maps.app.goo.gl/tq4jakUMkpmbeCci8"},
    {"name": "BilaBila Mart - MSU Shah Alam", "url": "https://goo.gl/maps/jgPNQoK24me1jYXX9"},
    {"name": "BilaBila Mart - Ryan & Miho", "url": "https://goo.gl/maps/GmUkjdB3R5FK2p6R8"},
    {"name": "BilaBila Mart - Saujana Villa", "url": "https://goo.gl/maps/aFjPxAr5yaXteCi89"},
    {"name": "BilaBila Mart - Segi Kota Damansara", "url": "https://maps.app.goo.gl/kv56uPV1KbRi5fmq9"},
    {"name": "BilaBila Mart - Splash Mania", "url": "https://maps.app.goo.gl/UBzPUAutj4mPhAiGA"},
    {"name": "BilaBila Mart - SS12 Subang Jaya", "url": "https://goo.gl/maps/mzNvymYrgxATsG41A"},
    {"name": "BilaBila Mart - Sunway House Waterfront Residence", "url": "https://maps.app.goo.gl/1yA4hgjXgYUcoP8z9"},
    {"name": "BilaBila Mart - Sunway Serene", "url": "https://goo.gl/maps/NDqCENyX4GrJ6rFj7"},
    {"name": "BilaBila Mart - The Arcuz", "url": "https://maps.app.goo.gl/TZAnELC9z4sfbuW7A"},
    {"name": "BilaBila Mart - University of Cyberjaya (UoC)", "url": "https://maps.app.goo.gl/qT1MPCUqU9aP4K1r9"},
    # Penang locations
    {"name": "BilaBila Mart - 22 Macalisterz", "url": "https://maps.app.goo.gl/JVzaUUoTNt5CiYhH6"},
    {"name": "BilaBila Mart - Hutton Suites", "url": "https://maps.app.goo.gl/5Yn65DnQcwjRffDv8"},
    {"name": "BilaBila Mart - Urban Suites", "url": "https://maps.app.goo.gl/7whARcv3dpC2KwzX8"},
    {"name": "BilaBila Mart - SCAPES Hotel", "url": "https://maps.app.goo.gl/tLB5NiomKGexMPPM8"},
    {"name": "BilaBila Mart - Windmill Upon Hills", "url": "https://maps.app.goo.gl/R7dYHNYXFE8wmQBAA"},
]

# State classification based on location names
STATE_KEYWORDS = {
    "Kuala Lumpur": [
        "Mont Kiara", "Bukit Bintang", "Cheras", "Bukit Jalil", "KLCC", "Bangsar",
        "Desa Green", "Suites", "Kasah", "Seputeh", "Bintang", "Taman", "Danau",
        "Wisma", "Residen", "Chambers", "Cubic", "Dorsett", "Expressionz", "Hampton",
        "Impiana", "Kaleidoscope", "Lavile", "Centura", "Platinum", "Millerz", "Vertica",
        "Neu", "Nest", "Nidoz", "Novum", "Parc", "Regalia", "Riveria", "REXKL", "Riana",
        "Savio", "Scarletz", "Seni", "Setia", "Sky Awani", "Sofiya", "South", "Suasana",
        "Valley", "Tria", "TAR UMT", "Vogue", "Wisma", "APU", "Ceylonz", "Ceylon",
        "Cubic", "Agile", "Arte", "Aster", "Axon", "Casa", "D'Ivo", "Leafz",
        "Robertson", "Havre", "Tuan"
    ],
    "Selangor": [
        "Shah Alam", "Subang", "Damansara", "Bandar Utama", "AraTre", "Equine",
        "Mossaz", "Saujana", "Segi", "Splash", "SS12", "Sunway", "Cyberjaya",
        "Maisson", "Empire", "Dian", "Canopy", "Ryan", "Arcuz", "Waterfront", "Serene"
    ],
    "Penang": [
        "Macalisterz", "Hutton", "Urban", "SCAPES", "Windmill"
    ],
    "Perak": [
        "Tambun", "Onsen"
    ],
}

def classify_state(location_name: str) -> str:
    """Classify location into state based on name."""
    name_upper = location_name.upper()
    
    for state, keywords in STATE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.upper() in name_upper:
                return state
    
    return "Kuala Lumpur"  # Default

def extract_coords_from_url(url: str) -> Optional[tuple]:
    """
    Extract coordinates from Google Maps URL.
    
    Formats supported:
    - https://maps.app.goo.gl/[code]
    - https://goo.gl/maps/[code]
    - https://share.google/[code]
    - https://g.co/kgs/[code]
    """
    # These are shortened URLs that require following redirects
    # For now, we'll store the URL and note that coordinates need to be fetched via API
    return None

def organize_by_state(locations: List[Dict]) -> Dict[str, List[Dict]]:
    """Organize locations by state."""
    by_state = {}
    
    for loc in locations:
        state = classify_state(loc['name'])
        if state not in by_state:
            by_state[state] = []
        
        by_state[state].append({
            "name": loc['name'].replace("BilaBila Mart - ", ""),
            "map_url": loc['url'],
        })
    
    return by_state

def save_locations(locations: Dict[str, List[Dict]], output_path: str):
    """Save locations to JSON file."""
    data = {
        "store": "BilaBila Mart",
        "website": "https://www.bilabila.co",
        "locations_page": "https://www.bilabila.co/our-locations",
        "total_locations": sum(len(locs) for locs in locations.values()),
        "locations_by_state": locations,
        "notes": [
            "Coordinates need to be extracted by following Google Maps short links",
            "Each location links to Google Maps for full address and details",
            "M Vertica 2 location maps to same coordinates as M Vertica"
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {data['total_locations']} locations to {output_path}")
    print("\nLocations by state:")
    for state, locs in locations.items():
        print(f"  {state}: {len(locs)}")

def main():
    """Main scraper function."""
    print("BilaBila Mart Location Scraper")
    print("=" * 50)
    
    # Organize locations by state
    by_state = organize_by_state(BILABILA_LOCATIONS)
    
    # Save to file
    output_path = "data/bilabila_locations.json"
    save_locations(by_state, output_path)

if __name__ == "__main__":
    main()
