#!/usr/bin/env python3
"""
Merge coordinates from old lotuss_malaysia_locations.json to new file
Matches by branch_name (primary) or phone (fallback)
"""

import json
import re

def normalize_phone(phone):
    """Remove all non-digits from phone number for comparison"""
    if not phone:
        return ""
    return re.sub(r'\D', '', phone)

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath, data):
    """Save JSON file with nice formatting"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    # Load both files
    print("Loading files...")
    old_stores = load_json('data/lotuss_malaysia_locations.json')
    new_stores = load_json('data/lotuss_malaysia_locations_new.json')
    
    print(f"Old file: {len(old_stores)} stores")
    print(f"New file: {len(new_stores)} stores")
    
    # Create lookup dictionaries from old file
    by_branch_name = {}
    by_phone = {}
    
    for store in old_stores:
        branch = store.get('branch_name', '').strip()
        phone = normalize_phone(store.get('phone', ''))
        
        if branch:
            by_branch_name[branch] = store
        if phone:
            by_phone[phone] = store
    
    print(f"\nCreated lookups:")
    print(f"  By branch_name: {len(by_branch_name)} entries")
    print(f"  By phone: {len(by_phone)} entries")
    
    # Match and update coordinates
    matched_by_name = 0
    matched_by_phone = 0
    no_match = 0
    no_coords_in_old = 0
    
    print("\nMatching stores...")
    for new_store in new_stores:
        branch = new_store.get('branch_name', '').strip()
        phone = normalize_phone(new_store.get('phone', ''))
        
        matched_store = None
        match_type = None
        
        # Try matching by branch name first
        if branch in by_branch_name:
            matched_store = by_branch_name[branch]
            match_type = 'branch_name'
            matched_by_name += 1
        # Fallback to phone
        elif phone and phone in by_phone:
            matched_store = by_phone[phone]
            match_type = 'phone'
            matched_by_phone += 1
        else:
            no_match += 1
            print(f"  ❌ No match: {branch} (phone: {new_store.get('phone', 'N/A')})")
            continue
        
        # Copy coordinates if they exist
        if matched_store:
            lat = matched_store.get('latitude')
            lng = matched_store.get('longitude')
            
            if lat is not None and lng is not None:
                new_store['latitude'] = lat
                new_store['longitude'] = lng
                # Also copy rating fields if available
                new_store['rating'] = matched_store.get('rating')
                new_store['total_ratings'] = matched_store.get('total_ratings')
            else:
                no_coords_in_old += 1
                print(f"  ⚠️  Matched but no coords: {branch} (via {match_type})")
    
    # Save updated file
    output_file = 'data/lotuss_malaysia_locations_merged.json'
    save_json(output_file, new_stores)
    
    # Print summary
    print(f"\n{'='*60}")
    print("MERGE SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Matched by branch_name: {matched_by_name}")
    print(f"✅ Matched by phone: {matched_by_phone}")
    print(f"⚠️  Matched but no coords in old file: {no_coords_in_old}")
    print(f"❌ No match found: {no_match}")
    print(f"\nTotal stores processed: {len(new_stores)}")
    
    # Count how many have coordinates now
    with_coords = sum(1 for s in new_stores if s.get('latitude') is not None)
    print(f"Stores with coordinates: {with_coords}/{len(new_stores)}")
    
    print(f"\n✓ Saved to: {output_file}")
    print("\nNext steps:")
    print(f"  1. Review the merge results above")
    print(f"  2. If satisfied, replace the old file:")
    print(f"     mv {output_file} data/lotuss_malaysia_locations.json")

if __name__ == '__main__':
    main()
