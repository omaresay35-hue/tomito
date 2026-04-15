#!/usr/bin/env python3
import os
import sys
import json
import logging
import threading
import subprocess
import random
import argparse
from datetime import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
# Import new AI engine
from ai_engine import generate_seo_content, BOT_MISSIONS, get_mission

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
BATCH_SIZE   = 50   # Trigger git push every 50 pages
TARGET_TOTAL = 50   # Each bot processes 50 items per mission
SEEN_FILE    = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE   = os.path.join(BASE_PATH, 'data', 'content_index.json')

# -- Logging --
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def git_push(mission_name):
    """Trigger the git sync script."""
    log.info(f"🚀 Triggering Git Push for mission: {mission_name}...")
    try:
        subprocess.run(["bash", os.path.join(BASE_PATH, "git_sync.sh")], check=True)
    except Exception as e:
        log.error(f"❌ Git Push Failed: {e}")

def collect_mission_content(mission, seen_ids, target):
    """Fetches content based on the specific mission (genre, era, or trending)."""
    collected = []
    m_type = mission['type']
    
    for media_type in ['movie', 'tv']:
        log.info(f"🔍 [Mission: {mission['name']}] Searching for {media_type} items...")
        
        for page in range(1, 10):
            params = {'page': page, 'sort_by': 'popularity.desc'}
            endpoint = f'discover/{media_type}'
            
            if m_type == 'genre':
                params['with_genres'] = mission['id']
            elif m_type == 'era':
                year_start, year_end = mission['range']
                # Determine which year to pick based on hour of day to ensure coverage rotation
                hour_seed = datetime.now().hour
                year_range_size = year_end - year_start + 1
                year = year_start + (hour_seed % year_range_size)
                
                year_param = 'primary_release_year' if media_type == 'movie' else 'first_air_date_year'
                params[year_param] = year
            elif m_type == 'trending':
                endpoint = f'trending/{media_type}/day'
            elif m_type == 'mini_series' and media_type == 'tv':
                params['with_type'] = '4' # Mini Series in TMDB
            else:
                # If mission doesn't apply to this media_type (e.g. mini_series for movie)
                if m_type == 'mini_series' and media_type == 'movie':
                    break # Skip
            
            data = get_tmdb_data(endpoint, params)
            if not data or 'results' not in data: break
            
            for item in data['results']:
                # Filter for 2025-2026 if trending mission
                if m_type == 'trending':
                    date = item.get('release_date') or item.get('first_air_date') or ''
                    if not (date.startswith('2025') or date.startswith('2026')):
                        continue

                tid = str(item.get('id'))
                if tid not in seen_ids[media_type]:
                    collected.append((tid, media_type))
                    seen_ids[media_type].add(tid)
                    if len(collected) >= target: return collected
    return collected

def worker(tid, media_type, batch_entries, lock, counter, model_name):
    details = fetch_details(tid, media_type)
    if not details: return
    
    # Use OpenRouter for SEO
    title = (details['en'].get('title') or details['en'].get('name')) if details['en'] else "Unknown"
    overview = (details['en'].get('overview') or details['ar'].get('overview')) if details.get('ar') or details.get('en') else ""
    
    if not overview: return
    
    ai = generate_seo_content(title, overview, media_type, model_override=model_name)
    if ai:
        if details['ar']:
            details['ar']['title'] = ai.get('seo_title', title)
            details['ar']['overview'] = ai.get('ai_description', overview)
        if details['en']:
            details['en']['overview'] = ai.get('ai_description', overview)
            
    page_path, entry = create_page(details, media_type, is_trend=True)
    if page_path and entry:
        logging.info(f"   ✅ [Done] {title}")
        with lock:
            batch_entries.append(entry)
            counter[0] += 1
    else:
        logging.warning(f"   ❌ [Failed] {title}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mission', type=int, help='Index of the mission to run (0-25)')
    parser.add_argument('--no-push', action='store_true', help='Skip git push')
    args = parser.parse_args()

    # Get model and mission details
    model_name, mission = get_mission(args.mission)
    log.info(f"🤖 Starting Multi-Bot Mission: {mission['name']} using {model_name}")

    # Initialize seen sets
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

    # Collect content for this specific mission
    tasks = collect_mission_content(mission, seen, TARGET_TOTAL)
    
    if not tasks:
        log.info("📭 No new items found for this mission.")
        return

    # Process in batches
    for i in range(0, len(tasks), BATCH_SIZE):
        batch_tasks = tasks[i : i + BATCH_SIZE]
        batch_entries = []
        lock = threading.Lock()
        counter = [0]
        
        log.info(f"📦 Processing Batch {(i//BATCH_SIZE) + 1} ({len(batch_tasks)} items)...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(worker, tid, mt, batch_entries, lock, counter, model_name): tid for (tid, mt) in batch_tasks}
            for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
                try:
                    future.result()
                    if idx % 5 == 0 or idx == len(batch_tasks):
                        log.info(f"📊 Progress: {idx}/{len(batch_tasks)} items processed...")
                except Exception as e:
                    log.error(f"⚠️ Error processing item: {e}")
        
        if batch_entries:
            with lock:
                all_index.extend(batch_entries)
                with open(INDEX_FILE, 'w') as f:
                    json.dump(all_index, f, ensure_ascii=False, indent=2)
                
                with open(SEEN_FILE, 'w') as f:
                    json.dump({'movie': list(seen_movie), 'tv': list(seen_tv)}, f)
                
                # Update Sitemaps
                all_paths = [f"{e['folder']}/{e['slug']}.html" for e in all_index]
                generate_sitemap(SITE_URL, BASE_PATH, all_paths)
                
                if not args.no_push:
                    git_push(mission['name'])
    
    log.info(f"🏁 Mission {mission['name']} Complete!")

if __name__ == '__main__': main()
