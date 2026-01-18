# Complete Wiki Scraping Guide

## How to Scrape ALL Wiki Pages

The scraper is now configured to scrape the entire OSRS wiki. Here's how it works:

### Current Configuration

**In `config.yaml`:**
- `max_pages: null` - Scrapes ALL pages (no total limit)
- `category_limit: null` - Scrapes ALL pages from each category (no per-category limit)
- **Expanded categories** - Now includes 15+ categories for comprehensive coverage

### Categories Included

The scraper will get pages from:
- Items
- Quests
- Skills
- Monsters
- Locations
- Bosses
- NPCs
- Minigames
- Equipment
- Weapons
- Armour
- Food
- Potions
- Achievement Diaries
- Combat
- Guides

Plus all 23 skill pages and training guides are automatically added.

## Running Full Scrape

### Step 1: Start the Scraping

```bash
python scrape_wiki.py
```

**This will:**
- Fetch ALL pages from all configured categories (no limits)
- Add skill training guides automatically
- Save to `data/raw/` directory
- Show progress as it goes

**Time Estimate:** 
- ~5,000-10,000+ pages total
- ~2-4 hours depending on wiki response times
- Uses 0.3-0.5 second delays between pages (respectful scraping)

### Step 2: Process All Data

```bash
python process_data.py
```

This processes all scraped pages into chunks.

**Time Estimate:**
- ~30 minutes for 10,000 pages

### Step 3: Build Vector Database

```bash
python create_vector_db.py --clear
```

This creates embeddings for all chunks.

**Time Estimate:**
- ~1-2 hours for large dataset
- First run downloads embedding model (~1.3GB)

## Limiting Scraping (If Needed)

If you want to limit scraping (for testing or faster initial setup):

### Option 1: Limit Total Pages

In `config.yaml`, change:
```yaml
max_pages: 5000  # Only scrape first 5000 pages
```

### Option 2: Limit Per Category

In `config.yaml`, change:
```yaml
category_limit: 500  # Only 500 pages per category
```

### Option 3: Reduce Categories

Remove categories from the list in `config.yaml` if you don't need them.

## Monitoring Progress

The scraper will:
- Log progress to console
- Show pages found per category
- Save progress every 50 pages (so you can stop/resume)
- Display total pages collected

## Storage Requirements

For a full scrape:
- **Raw JSON files:** ~500MB - 2GB
- **Processed chunks:** ~200MB - 800MB
- **Vector database:** ~2GB - 5GB (with embeddings)

## Tips

1. **Run overnight**: Full scrape takes time, run it when you don't need the computer
2. **Check logs**: Monitor `logs/` directory for any errors
3. **Resume capability**: If interrupted, the scraper will skip already-scraped pages
4. **Test first**: Try with `max_pages: 100` first to test the setup

## Troubleshooting

**"Too many requests" errors:**
- Increase delays in `scrape_wiki.py` (currently 0.3-0.5s)
- The scraper respects rate limits automatically

**Out of memory:**
- Process data in batches
- Reduce `batch_size` in `config.yaml`

**Slow scraping:**
- This is normal! The wiki has thousands of pages
- Consider limiting categories if you only need specific topics

