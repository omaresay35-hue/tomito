#!/usr/bin/env python3
import os
import sys
import json
import logging
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time
import requests
import subprocess

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from mega_bot import get_tmdb_data, fetch_details, create_page, generate_sitemap, SITE_URL, build_listing_pages
import build_homepage
from ai_engine import get_mission, MODELS, OPENROUTER_KEY, clean_ai_text

FAST_MODELS = [
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "google/gemma-3n-e2b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-12b-it:free"
]
SORTED_MODELS = [m for m in FAST_MODELS if m in MODELS] + [m for m in MODELS if m not in FAST_MODELS]

TARGET_TOTAL = 500
BATCH_SIZE = 50
SEEN_FILE = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE = os.path.join(BASE_PATH, 'data', 'content_index.json')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def generate_unified_seo(title, overview, media_type, model):
    ar_type = "فيلم" if media_type == 'movie' else "مسلسل"
    prompt = f"""
أنت مساعد SEO عبقري وسريع. النص الأصلي لـ {ar_type} '{title}' هو: "{overview[:250]}".

مهمتك:
1. إنشاء (SEO Title) جذاب جداً مع كلمات دلالية.
2. إنشاء وصف (Description) قصير وخاطف (سطرين كحد أقصى) يشد القارئ ويجمع بين القصة والجودة.
3. إضافة 10 كلمات مفتاحية قوية جداً.
أجب بصيغة JSON فقط:
{{
  "seo_title": "أفضل عنوان SEO لـ {title}...",
  "ai_description": "وصف جذاب وقصير...",
  "keywords": "كلمات, مفتاحية, حصرية"
}}
"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You return results in JSON format only."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message']['content'].strip()
            content = content.replace('```json', '').replace('```', '').strip()
            data = json.loads(content)
            data['ai_description'] = clean_ai_text(data['ai_description'])
            return data
    except Exception as e:
        pass
    return None

def fetch_items(seen):
    """Fetch total of TARGET_TOTAL items across movie, tv, and trending."""
    tasks = []
    # (media_type, endpoint, is_trend)
    sources = [
        ('movie', 'trending/movie/day', True),
        ('tv', 'trending/tv/day', True),
        ('movie', 'discover/movie', False),
        ('tv', 'discover/tv', False),
    ]
    
    page = 1
    # Rotate through sources evenly
    while len(tasks) < TARGET_TOTAL and page <= 60:
        for media_type, url, is_trend in sources:
            params = {'page': page}
            if not is_trend:
                params['sort_by'] = 'popularity.desc'
                params['vote_count.gte'] = 5
            data = get_tmdb_data(url, params)
            if data and 'results' in data:
                for item in data['results']:
                    tid = str(item['id'])
                    if tid not in seen[media_type]:
                        tasks.append((tid, media_type, is_trend))
                        seen[media_type].add(tid)
                        if len(tasks) >= TARGET_TOTAL: return tasks
        page += 1
    
    # Variety Fallback: If still not enough, fetch from random years
    import random
    if len(tasks) < TARGET_TOTAL:
        log.info(f"🔄 Variety Fallback: Fetching older content (1990-2024)...")
        for _ in range(20): # Try up to 20 random year/page combinations
            media_type = random.choice(['movie', 'tv'])
            year = random.randint(1990, 2024)
            page = random.randint(1, 10)
            params = {
                'page': page,
                'sort_by': 'popularity.desc',
                'vote_count.gte': 10
            }
            if media_type == 'movie': params['primary_release_year'] = year
            else: params['first_air_date_year'] = year
            
            data = get_tmdb_data(f"discover/{media_type}", params)
            if data and 'results' in data:
                for item in data['results']:
                    tid = str(item['id'])
                    if tid not in seen[media_type]:
                        tasks.append((tid, media_type, False))
                        seen[media_type].add(tid)
                        if len(tasks) >= TARGET_TOTAL: return tasks
    return tasks

def worker(item, batch_entries, lock, counter, model_iter_state):
    tid, media_type, is_trend = item
    details = fetch_details(tid, media_type)
    if not details: return
    
    # Use OpenRouter for SEO
    title = (details['en'].get('title') or details['en'].get('name')) if details['en'] else "Unknown"
    overview = (details['en'].get('overview') or details['ar'].get('overview')) if details.get('ar') or details.get('en') else ""
    if not overview: return

    # Rotate models for rate limits and variety
    with lock:
        model = SORTED_MODELS[model_iter_state[0] % len(SORTED_MODELS)]
        model_iter_state[0] += 1
    
    ai = generate_unified_seo(title, overview, media_type, model)
    if ai:
        if details['ar']:
            details['ar']['title'] = ai.get('seo_title', title)
            details['ar']['overview'] = ai.get('ai_description', overview)
        if details['en']:
            details['en']['overview'] = ai.get('ai_description', overview)
            
    page_path, entry = create_page(details, media_type, is_trend=is_trend)
    if page_path and entry:
        with lock:
            batch_entries.append(entry)
            counter[0] += 1
            log.info(f"✅ [{counter[0]}] Created: {title} via {model.split('/')[-1]}")

def main():
    log.info("🤖 Starting Unified Bot")

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

    tasks = fetch_items(seen)
    if not tasks:
        log.info("📭 No new items found.")
        return

    log.info(f"🎯 Target tasks: {len(tasks)}")
    
    model_iter_state = [0]
    # Process in batches
    for i in range(0, len(tasks), BATCH_SIZE):
        batch_tasks = tasks[i : i + BATCH_SIZE]
        batch_entries = []
        lock = threading.Lock()
        counter = [0]
        
        log.info(f"📦 Processing Batch {(i//BATCH_SIZE) + 1} ({len(batch_tasks)} items)...")
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(worker, item, batch_entries, lock, counter, model_iter_state): item for item in batch_tasks}
            concurrent.futures.wait(futures)
        
        if batch_entries:
            with lock:
                all_index.extend(batch_entries)
                with open(INDEX_FILE, 'w') as f:
                    json.dump(all_index, f, ensure_ascii=False, indent=2)
                
                with open(SEEN_FILE, 'w') as f:
                    json.dump({'movie': list(seen_movie), 'tv': list(seen_tv)}, f)
                
                # Update Sitemaps
                all_paths = [f"{e['folder']}/{e['slug']}" for e in all_index]
                generate_sitemap(SITE_URL, BASE_PATH, all_paths)
                
                log.info("🏗️ Rebuilding Homepage & Listing Pages...")
                try:
                    build_listing_pages()
                    build_homepage.build()
                except Exception as e:
                    log.error(f"❌ Error rebuilding pages: {e}")
                
                log.info("✅ Batch complete.")
                
    log.info("🏁 Generation Complete! Run 'bash git_sync.sh' when ready to push.")

if __name__ == '__main__':
    main()
