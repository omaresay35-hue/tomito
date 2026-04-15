#!/usr/bin/env python3
import os
import sys
import json
import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# -- الإعدادات العامة --
TARGET       = 100
SEEN_FILE    = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE   = os.path.join(BASE_PATH, 'data', 'content_index.json')
LOG_FILE     = os.path.join(BASE_PATH, 'daily_content.log')
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")

# -- إعداد Gemini --
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# -- Logging --
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ── SEO & Gemini Engine ──────────────────────────────────────────────────────

def get_ai_seo_content(title, overview, media_type):
    """يستخدم Gemini لصناعة محتوى SEO حصري 1000%"""
    if not GEMINI_KEY or not overview:
        return None
    
    prompt = f"""
    أنت خبير SEO لموقع أفلام (nordrama.live). قم بتحليل: ({title}) نوعه ({media_type}).
    الوصف الأصلي: {overview}.
    
    المطلوب إنتاج محتوى حصري 100% يتبع هذه الشروط الصارمة:
    1. SEO Title: عنوان جذاب جداً بالعربية والإنجليزية (مثال: مشاهدة فيلم Joker 2 مترجم كامل HD).
    2. Tags: استخرج 15 كلمة مفتاحية قوية بالعربية والإنجليزية مفصولة بفاصلة.
    3. Description: اكتب مراجعة وصفية مشوقة (أكثر من 100 كلمة) بأسلوب سينمائي يركز على القصة والجودة، استهدف كلمات يفضلها جوجل.
    
    أجب بصيغة JSON فقط:
    {{
      "seo_title": "...",
      "keywords": "...",
      "ai_description": "..."
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        log.warning(f" Gemini Error for {title}: {e}")
        return None

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_data():
    seen = {'movie': set(), 'tv': set()}
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
            seen = {'movie': set(d.get('movie', [])), 'tv': set(d.get('tv', []))}
    
    index = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index = json.load(f)
    return seen, index

def save_data(seen, index):
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump({'movie': list(seen['movie']), 'tv': list(seen['tv'])}, f)
    index.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

# ── Core Logic ───────────────────────────────────────────────────────────────

def collect_trending(media_type, seen_ids):
    """جلب التريند من TMDB"""
    collected = []
    for page in range(1, 8):
        data = get_tmdb_data(f'trending/{media_type}/day', {'page': page})
        if not data or 'results' not in data: break
        for item in data['results']:
            tid = item.get('id')
            if tid and tid not in seen_ids:
                collected.append(tid)
                seen_ids.add(tid)
                if len(collected) >= TARGET: break
        if len(collected) >= TARGET: break
    return collected

def process_and_generate(tmdb_ids, media_type):
    """صناعة الصفحات باستخدام الذكاء الاصطناعي والسرعة القصوى"""
    new_entries, new_pages = [], []
    lock = threading.Lock()

    def worker(tid):
        details = fetch_details(tid, media_type)
        if not details or not details.get('overview'): return
        
        # تفعيل وحش السيو (Gemini)
        ai_data = get_ai_seo_content(details.get('title') or details.get('name'), details['overview'], media_type)
        
        if ai_data:
            details['title'] = ai_content['seo_title'] # تحديث العنوان بالعربي/إنجليزي
            details['overview'] = ai_content['ai_description'] # تحديث الوصف لـ +100 كلمة
            details['tags'] = ai_content['keywords'] # إضافة الكلمات المفتاحية
        
        page_path, entry = create_page(details, media_type, is_trend=True)
        if page_path and entry:
            with lock:
                new_entries.append(entry)
                new_pages.append(page_path)

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(worker, tmdb_ids))
    
    return new_entries, new_pages

# ── Execution ────────────────────────────────────────────────────────────────

def main():
    start_time = datetime.now()
    log.info(f"🚀 Launching SEO Beast Run: {start_time}")
    
    os.makedirs(os.path.join(BASE_PATH, 'data'), exist_ok=True)
    seen, all_index = load_data()
    all_pages = [f"{i['folder']}/{i['slug']}" for i in all_index]

    for m_type in ['movie', 'tv']:
        log.info(f"Fetching Trending {m_type}...")
        ids = collect_trending(m_type, seen[m_type])
        entries, pages = process_and_generate(ids, m_type)
        
        # حفظ تريند منفصل لكل نوع (للسلايدر مثلاً)
        with open(os.path.join(BASE_PATH, 'data', f'trend_{m_type}.json'), 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            
        all_index.extend(entries)
        all_pages.extend(pages)

    save_data(seen, all_index)
    generate_sitemap(SITE_URL, BASE_PATH, all_pages)
    
    # تحديث الصفحة الرئيسية
    try:
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_PATH, 'build_homepage.py')], check=True)
    except: pass

    log.info(f"✅ Finished in {datetime.now() - start_time}. All pages are unique and AI-optimized!")

if __name__ == '__main__':
    main()
