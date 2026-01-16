"""Quick script to check what pages we have in the database."""
import json
from pathlib import Path

# Load scraped data
data_file = Path("data/raw/all_pages.json")
if data_file.exists():
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total pages scraped: {len(data)}\n")
    
    # Check for Attack skill related pages
    attack_pages = [p['title'] for p in data if 'attack' in p['title'].lower()]
    print(f"Pages with 'attack' in title ({len(attack_pages)}):")
    for p in attack_pages[:20]:
        print(f"  - {p}")
    
    # Check for training guide pages
    training_pages = [p['title'] for p in data if 'training' in p.get('content', '').lower() or 'training' in p.get('title', '').lower()]
    print(f"\nPages with 'training' in title/content ({len(training_pages)}):")
    for p in training_pages[:20]:
        print(f"  - {p}")
    
    # Check for skill pages
    skill_pages = [p['title'] for p in data if 'skill' in p['title'].lower()]
    print(f"\nPages with 'skill' in title ({len(skill_pages)}):")
    for p in skill_pages[:20]:
        print(f"  - {p}")
else:
    print("No data file found!")

