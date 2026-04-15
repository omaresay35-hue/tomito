#!/usr/bin/env python3
import os
import sys
import json
import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

# -- إعداد المسارات --
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from mega_bot import (
    get_tmdb_data,
    fetch_details,
    create_page,
    generate_sitemap,
    SITE_URL,
)

# -- الإعدادات --
TARGET       = 100  
SEEN_FILE    = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE   = os.path.join(BASE_PATH, 'data', 'content_index.json')
LOG_FILE     = os.path.join(BASE_PATH, 'daily_content.log')
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")

# قائمة الأنواع (Genres) لضمان تنوع المحتوى
GENRES = {
    'movie': [28, 12, 16, 35, 80, 27, 10749, 878], # أكشن، مغامرة، أنيميشن، كوميديا، جريمة، رعب، رومانسي، خيال علمي
    'tv': [10759, 18, 35, 80, 10765, 9648] # أكشن، دراما، كوميديا، جريمة، خيال علمي، غموض
}

# -- إعداد Gemini --
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# -- Logging --
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ── SEO Engine (Gemini) ─────────────────────────────────────────────────────

def get_ai_seo_content(title, overview, media_type):
    if not GEMINI_KEY or not overview: return None
    prompt = f"""
    أنت خبير SEO لموقع أفلام (nordrama.live). قم بتحليل: ({title}) نوعه ({media_type}).
    الوصف الأصلي: {overview}.
    المطلوب إنتاج محتوى حصري 100% (SEO Title، 15 Tags قوية، وصف مشوق +100 كلمة).
    أجب بصيغة JSON فقط:
    {{ "seo_title": "...", "keywords": "...", "ai_description": "..." }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except: return None

# ── Smart Collector (Trending + Genres + Backfill) ─────────────────────────

def collect_smart_content(media_type, seen_ids):
    collected = []
    
    # 1. الأولوية: التريند الحالي (الجديد)
    log.info(f"🔍 Searching Trending {media_type}...")
    for page in range(1, 5):
        data = get_tmdb_data(f'trending/{media_type}/day', {'page': page})
        if not data or 'results' not in data: break
        for item in data['results']:
            tid = str(item.get('id'))
            if tid not in seen_ids:
                collected.append(tid); seen_ids.add(tid)
                if len(collected) >= TARGET: return collected

    # 2. البحث بالأنواع (Action, Horror, etc.) لضمان التنوع
    log.info(f"📂 Searching by Genres for {media_type}...")
    for genre_id in GENRES[media_type]:
        if len(collected) >= TARGET: break
        for page in range(1, 3):
            params = {'page': page, 'with_genres': genre_id, 'sort_by': 'popularity.desc'}
            data = get_tmdb_data(f'discover/{media_type}', params)
            if not data or 'results' not in data: break
            for item in data['results']:
                tid = str(item.get('id'))
                if tid not in seen_ids:
                    collected.append(tid); seen_ids.add(tid)
                    if len(collected) >= TARGET: break

    # 3. الرجوع للسنوات السابقة (Backfill)
    current_year = datetime.now().year
    for year in [current_year, current_year-1, current_year-2]:
        if len(collected) >= TARGET: break
        log.info(f"⏳ Backfilling {media_type} from {year}...")
        for page in range(1, 5):
            params = {'page': page, 'year' if media_type == 'movie' else 'first_air_date_year': year, 'sort_by': 'popularity.desc'}
            data = get_tmdb_data(f'discover/{media_type}', params)
            if not data or 'results' not in data: break
            for item in data['results']:
                tid = str(item.get('id'))
                if tid not in seen_ids:
                    collected.append(tid); seen_ids.add(tid)
                    if len(collected) >= TARGET: return collected
    return collected

# ── Processing & Main ───────────────────────────────────────────────────────

def process_items(tmdb_ids, media_type):
    new_entries, new_pages = [], []
    lock = threading.Lock()
    def worker(tid):
        details = fetch_details(tid, media_type)
        if not details or not details.get('overview'): return
        ai_data = get_ai_seo_content(details.get('title') or details.get('name'), details['overview'], media_type)
        if ai_data:
            details['title'], details['overview'], details['tags'] = ai_data['seo_title'], ai_data['ai_description'], ai_data['keywords']
        page_path, entry = create_page(details, media_type, is_trend=True)
        if page_path and entry:
            with lock: new_entries.append(entry); new_pages.append(page_path)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(worker, tmdb_ids)
    return new_entries, new_pages

def main():
    log.info(f"🚀 Launching SEO Beast Mode (Genres + Trends)")
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f: d = json.load(f); seen = {'movie': set(map(str, d.get('movie', []))), 'tv': set(map(str, d.get('tv', [])))}
    else: seen = {'movie': set(), 'tv': set()}
    
    all_index = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f: all_index = json.load(f)

    all_pages_paths = []
    for m_type in ['movie', 'tv']:
        ids = collect_smart_content(m_type, seen[m_type])
        entries, pages = process_items(ids, m_type)
        with open(os.path.join(BASE_PATH, 'data', f'trend_{m_type}.json'), 'w') as f: json.dump(entries, f, ensure_ascii=False)
        all_index.extend(entries); all_pages_paths.extend(pages)

    with open(SEEN_FILE, 'w') as f: json.dump({'movie': list(seen['movie']), 'tv': list(seen['tv'])}, f)
    with open(INDEX_FILE, 'w') as f: json.dump(all_index, f, ensure_ascii=False, indent=2)
    
    if all_pages_paths: generate_sitemap(SITE_URL, BASE_PATH, all_pages_paths)
    log.info("🏁 Task Complete!")

if __name__ == '__main__': main()
