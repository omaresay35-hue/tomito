#!/usr/bin/env python3
import os
import sys
import json
import logging
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
TARGET       = 100  # الهدف: 100 فيلم و 100 مسلسل يومياً
SEEN_FILE    = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE   = os.path.join(BASE_PATH, 'data', 'content_index.json')
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")

# -- إعداد Gemini --
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# -- Logging --
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ── Smart Deep Collector (The 1900 Scraper) ──────────────────────────────────

def collect_deep_content(media_type, seen_ids):
    """
    يبحث في الجديد، وإذا لم يجد، يعود في التاريخ عاماً بعد عام حتى 1900.
    """
    collected = []
    
    # 1. المرحلة الأولى: التريند (الجديد)
    log.info(f"🔍 Checking Trending {media_type}...")
    for page in range(1, 5):
        data = get_tmdb_data(f'trending/{media_type}/day', {'page': page})
        if not data or 'results' not in data: break
        for item in data['results']:
            tid = str(item.get('id'))
            if tid not in seen_ids:
                collected.append(tid)
                seen_ids.add(tid)
                if len(collected) >= TARGET: return collected

    # 2. المرحلة الثانية: الحفار (Backfill to 1900)
    current_year = datetime.now().year
    log.info(f"⏳ Backfilling {media_type} Mode: ON. Digging through history...")
    
    for year in range(current_year, 1900, -1): # يرجع بالسنوات لور
        if len(collected) >= TARGET: break
        
        # البحث في أفضل 3 صفحات لكل سنة لضمان الجودة
        for page in range(1, 4):
            params = {
                'page': page,
                'year' if media_type == 'movie' else 'first_air_date_year': year,
                'sort_by': 'popularity.desc',
                'with_original_language': 'en' # التركيز على المحتوى الأجنبي (الإنجليزي)
            }
            data = get_tmdb_data(f'discover/{media_type}', params)
            if not data or 'results' not in data: break
            
            for item in data['results']:
                tid = str(item.get('id'))
                if tid not in seen_ids:
                    collected.append(tid)
                    seen_ids.add(tid)
                    if len(collected) >= TARGET:
                        log.info(f"✅ Target Reached! Found 100 {media_type}s down to year {year}.")
                        return collected
    return collected

# ── Processing & SEO ─────────────────────────────────────────────────────────

def get_ai_seo(title, overview, media_type):
    if not GEMINI_KEY or not overview: return None
    prompt = f"أنت خبير SEO لموقع (nordrama.live). اصنع عنواناً جذاباً ووصفاً حصرياً (+100 كلمة) و15 تاغ لفيلم/مسلسل: {title}. الأصل: {overview}. أجب JSON فقط."
    try:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except: return None

def worker(tid, media_type, new_entries, new_pages, lock):
    details = fetch_details(tid, media_type)
    if not details or not details.get('overview'): return
    
    ai = get_ai_seo(details.get('title') or details.get('name'), details['overview'], media_type)
    if ai:
        details['title'], details['overview'], details['tags'] = ai['seo_title'], ai['ai_description'], ai['keywords']
    
    page_path, entry = create_page(details, media_type, is_trend=True)
    if page_path and entry:
        with lock:
            new_entries.append(entry)
            new_pages.append(page_path)

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f: 
            d = json.load(f)
            seen = {'movie': set(map(str, d.get('movie', []))), 'tv': set(map(str, d.get('tv', [])))}
    else: seen = {'movie': set(), 'tv': set()}
    
    all_index = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f: all_index = json.load(f)

    all_pages_paths = []
    for m_type in ['movie', 'tv']:
        ids = collect_deep_content(m_type, seen[m_type])
        
        new_entries, new_pages = [], []
        lock = threading.Lock()
        with ThreadPoolExecutor(max_workers=5) as executor:
            for tid in ids: executor.submit(worker, tid, m_type, new_entries, new_pages, lock)
        
        with open(os.path.join(BASE_PATH, 'data', f'trend_{m_type}.json'), 'w') as f:
            json.dump(new_entries, f, ensure_ascii=False)
            
        all_index.extend(new_entries)
        all_pages_paths.extend(new_pages)

    # حفظ البيانات المحدثة
    with open(SEEN_FILE, 'w') as f:
        json.dump({'movie': list(seen['movie']), 'tv': list(seen['tv'])}, f)
    with open(INDEX_FILE, 'w') as f:
        json.dump(all_index, f, ensure_ascii=False, indent=2)
    
    if all_pages_paths: generate_sitemap(SITE_URL, BASE_PATH, all_pages_paths)
    log.info("🏁 Deep Scraping Complete!")

if __name__ == '__main__': main()
