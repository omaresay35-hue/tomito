#!/usr/bin/env python3
import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from mega_bot import (
    get_tmdb_data,
    fetch_details,
    create_page,
    generate_sitemap,
    SITE_URL,
    BASE_PATH as BOT_BASE,
)

TARGET      = 100
MAX_LOOKBACK = 60
SEEN_FILE   = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE  = os.path.join(BASE_PATH, 'data', 'content_index.json')
LOG_FILE    = os.path.join(BASE_PATH, 'daily_content.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

def load_seen_ids() -> dict:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {'movie': set(data.get('movie', [])), 'tv': set(data.get('tv', []))}
        except Exception: pass
    return {'movie': set(), 'tv': set()}

def save_seen_ids(seen: dict):
    data = {'movie': list(seen['movie']), 'tv': list(seen['tv'])}
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def load_content_index() -> list:
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception: pass
    return []

def save_content_index(index: list):
    index.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def fetch_by_date(media_type: str, date_str: str) -> list:
    results = []
    page = 1
    date_gte_key = 'primary_release_date.gte' if media_type == 'movie' else 'first_air_date.gte'
    date_lte_key = 'primary_release_date.lte' if media_type == 'movie' else 'first_air_date.lte'
    while True:
        params = {'page': page, 'sort_by': 'popularity.desc', date_gte_key: date_str, date_lte_key: date_str, 'vote_count.gte': 0}
        data = get_tmdb_data(f'discover/{media_type}', params)
        if not data or not data.get('results'): break
        results.extend(data['results'])
        if page >= data.get('total_pages', 1): break
        page += 1
        time.sleep(0.1)
    return results

def collect_new_ids(media_type: str, seen_ids: set, today: datetime) -> list:
    collected = []
    days_back = 0
    while len(collected) < TARGET and days_back <= MAX_LOOKBACK:
        date_str = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        items = fetch_by_date(media_type, date_str)
        for item in items:
            tmdb_id = item.get('id')
            if tmdb_id and tmdb_id not in seen_ids:
                collected.append(tmdb_id)
                seen_ids.add(tmdb_id)
                if len(collected) >= TARGET: break
        log.info(f"  [{media_type}] date={date_str} → {len(items)} found, total={len(collected)}")
        days_back += 1
    return collected[:TARGET]

def generate_pages(tmdb_ids: list, media_type: str, existing_index: list) -> tuple[list, list]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    new_entries, new_pages, errors = [], [], 0
    lock = threading.Lock()
    def process_one(tmdb_id):
        nonlocal errors
        try:
            details = fetch_details(tmdb_id, media_type)
            if not details or (not details['ar'] and not details['en']): return
            page_path, index_entry = create_page(details, media_type, is_trend=True)
            if page_path and index_entry:
                with lock:
                    new_entries.append(index_entry)
                    new_pages.append(page_path)
        except Exception as e:
            log.warning(f"Error {tmdb_id}: {e}")
            with lock: errors += 1
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_one, tid) for tid in tmdb_ids]
        for f in as_completed(futures): pass
    return new_entries, new_pages

def main():
    today = datetime.now()
    log.info(f"=== DAILY RUN {today.strftime('%Y-%m-%d')} ===")
    os.makedirs(os.path.join(BASE_PATH, 'movie'), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, 'tv'), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, 'data'), exist_ok=True)
    seen, all_index = load_seen_ids(), load_content_index()
    all_pages = [f"{item['folder']}/{item['slug']}" for item in all_index]
    
    movie_ids = collect_new_ids('movie', seen['movie'], today)
    movie_entries, movie_pages = generate_pages(movie_ids, 'movie', all_index)
    
    tv_ids = collect_new_ids('tv', seen['tv'], today)
    tv_entries, tv_pages = generate_pages(tv_ids, 'tv', all_index)
    
    trend_entries = movie_entries + tv_entries
    with open(os.path.join(BASE_PATH, 'data', 'trend_movies.json'), 'w', encoding='utf-8') as f:
        json.dump(movie_entries, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_PATH, 'data', 'trend_tv.json'), 'w', encoding='utf-8') as f:
        json.dump(tv_entries, f, ensure_ascii=False, indent=2)
        
    all_index += trend_entries
    all_pages += movie_pages + tv_pages
    save_content_index(all_index)
    save_seen_ids(seen)
    generate_sitemap(SITE_URL, BASE_PATH, all_pages)
    
    try:
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_PATH, 'build_homepage.py')], check=True)
    except: pass
    log.info("Done ✅")

if __name__ == '__main__':
    main()
