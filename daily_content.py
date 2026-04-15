#!/usr/bin/env python3
import os
import sys
import json
import logging
import threading
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
# Import new AI engine
from ai_engine import generate_seo_content

# -- Path Setup --
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from mega_bot import (
    get_tmdb_data,
    fetch_details,
    create_page,
    generate_sitemap,
    SITE_URL,
)

# -- Settings --
BATCH_SIZE   = 5   # For testing, push every 5 pages
TARGET_TOTAL = 10  # Target: 5 movies and 5 TV shows for testing
SEEN_FILE    = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE   = os.path.join(BASE_PATH, 'data', 'content_index.json')

# -- Logging --
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def git_push():
    """Trigger the git sync script."""
    log.info("🚀 Triggering Git Push...")
    try:
        subprocess.run(["bash", os.path.join(BASE_PATH, "git_sync.sh")], check=True)
    except Exception as e:
        log.error(f"❌ Git Push Failed: {e}")

def collect_varied_content(media_type, seen_ids, target):
    """Fetches content from multiple TMDB endpoints to ensure variety."""
    collected = []
    
    # Endpoints to check
    endpoints = [
        (f'trending/{media_type}/day', {}),
        (f'trending/{media_type}/week', {}),
    ]
    if media_type == 'tv':
        endpoints.append(('tv/airing_today', {}))
    
    log.info(f"🔍 Searching for {media_type} variety...")
    for endpoint, params in endpoints:
        for page in range(1, 3):
            p = params.copy()
            p['page'] = page
            data = get_tmdb_data(endpoint, p)
            if not data or 'results' not in data: break
            for item in data['results']:
                tid = str(item.get('id'))
                if tid not in seen_ids:
                    collected.append(tid)
                    seen_ids.add(tid)
                    if len(collected) >= target: return collected

    # Backfill if target not reached
    log.info(f"⏳ Backfilling {media_type} from history...")
    current_year = datetime.now().year
    for year in range(current_year, 1900, -1):
        if len(collected) >= target: break
        for page in range(1, 3):
            params = {
                'page': page,
                'year' if media_type == 'movie' else 'first_air_date_year': year,
                'sort_by': 'popularity.desc'
            }
            data = get_tmdb_data(f'discover/{media_type}', params)
            if not data or 'results' not in data: break
            for item in data['results']:
                tid = str(item.get('id'))
                if tid not in seen_ids:
                    collected.append(tid)
                    seen_ids.add(tid)
                    if len(collected) >= target: return collected
    return collected

def worker(tid, media_type, new_entries, lock, counter):
    details = fetch_details(tid, media_type)
    if not details: return
    
    # Use OpenRouter for SEO
    title = (details['en'].get('title') or details['en'].get('name')) if details['en'] else "Unknown"
    overview = (details['en'].get('overview') or details['ar'].get('overview')) if details.get('ar') or details.get('en') else ""
    
    if not overview: return
    
    ai = generate_seo_content(title, overview, media_type)
    if ai:
        # Patch details for create_page
        if details['ar']:
            details['ar']['title'] = ai.get('seo_title', title)
            details['ar']['overview'] = ai.get('ai_description', overview)
        if details['en']:
            details['en']['overview'] = ai.get('ai_description', overview)
            
    # create_page handles folder creation and returns path
    page_path, entry = create_page(details, media_type, is_trend=True)
    if page_path and entry:
        with lock:
            new_entries.append(entry)
            counter[0] += 1

def main():
    # Initialize seen as specific sets to satisfy linter/logic
    seen_movie = set()
    seen_tv = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f: 
                d = json.load(f)
                seen_movie = set(map(str, d.get('movie', [])))
                seen_tv = set(map(str, d.get('tv', [])))
        except: pass
    
    seen = {'movie': seen_movie, 'tv': seen_tv}
    
    all_index = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f: 
            try: all_index = json.load(f)
            except: pass

    for m_type in ['movie', 'tv']:
        log.info(f"🚀 Starting {m_type} Generation...")
        ids = collect_varied_content(m_type, seen[m_type], TARGET_TOTAL // 2)
        
        # Process in batches of BATCH_SIZE
        for i in range(0, len(ids), BATCH_SIZE):
            batch_ids = ids[i : i + BATCH_SIZE]
            batch_entries = []
            lock = threading.Lock()
            counter = [0]
            
            log.info(f"📦 Processing Batch {(i//BATCH_SIZE) + 1} ({len(batch_ids)} items)...")
            with ThreadPoolExecutor(max_workers=3) as executor:
                for tid in batch_ids: 
                    executor.submit(worker, tid, m_type, batch_entries, lock, counter)
            
            if batch_entries:
                with lock:
                    # Update Index
                    all_index.extend(batch_entries)
                    with open(INDEX_FILE, 'w') as f:
                        json.dump(all_index, f, ensure_ascii=False, indent=2)
                    
                    # Update Seen
                    with open(SEEN_FILE, 'w') as f:
                        json.dump({'movie': list(seen_movie), 'tv': list(seen_tv)}, f)
                    
                    # Generate Sitemap for new pages
                    # mega_bot.create_page returns page_path like 'tv/slug' or 'movie/slug'
                    all_paths = [f"{e['folder']}/{e['slug']}.html" for e in all_index]
                    generate_sitemap(SITE_URL, BASE_PATH, all_paths)
                    
                    # Push to Git
                    git_push()

        
    log.info("🏁 All Batches Complete!")

if __name__ == '__main__': main()

