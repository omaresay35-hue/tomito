#!/usr/bin/env python3
"""
daily_content.py — Fetch & generate 100 newest movies + 100 newest TV shows per day.

Logic:
  1. Start from today's date.
  2. Fetch movies/tv released on that date from TMDB (paginated).
  3. Skip already-seen IDs (stored in daily_seen_ids.json).
  4. If < 100 results, go back one day at a time until we reach 100.
  5. Generate HTML pages via mega_bot.create_page().
  6. Update the seen-IDs file and content index.
  7. Rebuild homepage + sitemap.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta

# -- Path setup so we can import mega_bot --
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

# -- Config --
TARGET      = 100          # items per media type per run
MAX_LOOKBACK = 60          # never go further back than 60 days
SEEN_FILE   = os.path.join(BASE_PATH, 'daily_seen_ids.json')
INDEX_FILE  = os.path.join(BASE_PATH, 'data', 'content_index.json')
LOG_FILE    = os.path.join(BASE_PATH, 'daily_content.log')

# -- Logging --
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_seen_ids() -> dict:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'movie': set(data.get('movie', [])),
                    'tv':    set(data.get('tv',    [])),
                }
        except Exception:
            pass
    return {'movie': set(), 'tv': set()}


def save_seen_ids(seen: dict):
    data = {
        'movie': list(seen['movie']),
        'tv':    list(seen['tv']),
    }
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def load_content_index() -> list:
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_content_index(index: list):
    index.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


# ── TMDB date-filtered fetch ─────────────────────────────────────────────────

def fetch_by_date(media_type: str, date_str: str) -> list:
    """Return all TMDB items released on a specific date (paginated)."""
    results = []
    page = 1
    if media_type == 'movie':
        date_gte_key = 'primary_release_date.gte'
        date_lte_key = 'primary_release_date.lte'
    else:
        date_gte_key = 'first_air_date.gte'
        date_lte_key = 'first_air_date.lte'

    while True:
        params = {
            'page': page,
            'sort_by': 'popularity.desc',
            date_gte_key: date_str,
            date_lte_key: date_str,
            'vote_count.gte': 0,
        }
        data = get_tmdb_data(f'discover/{media_type}', params)
        if not data or not data.get('results'):
            break
        results.extend(data['results'])
        if page >= data.get('total_pages', 1):
            break
        page += 1
        time.sleep(0.1)   # be polite to the API

    return results


def collect_new_ids(media_type: str, seen_ids: set, today: datetime) -> list:
    """
    Walk backwards from today until we have TARGET unique, unseen IDs.
    Returns list of TMDB IDs (newest-date first).
    """
    collected = []
    days_back = 0

    while len(collected) < TARGET and days_back <= MAX_LOOKBACK:
        date_str = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        items = fetch_by_date(media_type, date_str)

        for item in items:
            tmdb_id = item.get('id')
            if tmdb_id and tmdb_id not in seen_ids:
                collected.append(tmdb_id)
                seen_ids.add(tmdb_id)          # mark as seen immediately
                if len(collected) >= TARGET:
                    break

        log.info(f"  [{media_type}] date={date_str} → {len(items)} found, "
                 f"total collected={len(collected)}")
        days_back += 1

    return collected[:TARGET]


# ── Page generation ──────────────────────────────────────────────────────────

def generate_pages(tmdb_ids: list, media_type: str,
                   existing_index: list) -> tuple[list, list]:
    """
    Generate HTML pages for the given IDs.
    Returns (new_index_entries, new_page_paths).
    """
    new_entries = []
    new_pages   = []
    errors      = 0

    for tmdb_id in tmdb_ids:
        try:
            details = fetch_details(tmdb_id, media_type)
            if not details or (not details['ar'] and not details['en']):
                continue
            page_path, index_entry = create_page(details, media_type)
            if page_path and index_entry:
                new_entries.append(index_entry)
                new_pages.append(page_path)
        except Exception as e:
            log.warning(f"  Error generating {media_type} {tmdb_id}: {e}")
            errors += 1

    log.info(f"  [{media_type}] pages generated: {len(new_pages)}, errors: {errors}")
    return new_entries, new_pages


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now()
    log.info(f"=== DAILY CONTENT RUN — {today.strftime('%Y-%m-%d %H:%M')} ===")

    # Ensure directories exist
    os.makedirs(os.path.join(BASE_PATH, 'movie'), exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, 'tv'),    exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH, 'data'),  exist_ok=True)

    seen       = load_seen_ids()
    all_index  = load_content_index()
    all_pages  = [f"{item['folder']}/{item['slug']}" for item in all_index]

    # -- Movies --
    log.info("Collecting movie IDs...")
    movie_ids = collect_new_ids('movie', seen['movie'], today)
    log.info(f"  → {len(movie_ids)} new movie IDs collected")

    log.info("Generating movie pages...")
    movie_entries, movie_pages = generate_pages(movie_ids, 'movie', all_index)

    # -- TV Shows --
    log.info("Collecting TV IDs...")
    tv_ids = collect_new_ids('tv', seen['tv'], today)
    log.info(f"  → {len(tv_ids)} new TV IDs collected")

    log.info("Generating TV pages...")
    tv_entries, tv_pages = generate_pages(tv_ids, 'tv', all_index)

    # -- Trending Export --
    trend_entries = movie_entries + tv_entries
    trend_path = os.path.join(BASE_PATH, 'data', 'latest_trend.json')
    with open(trend_path, 'w', encoding='utf-8') as f:
        json.dump(trend_entries, f, ensure_ascii=False, indent=2)
    log.info(f"   Exported {len(trend_entries)} trending items to {trend_path}")

    # Generate standalone trending sitemap
    trend_sitemap_path = os.path.join(BASE_PATH, 'sitemap_trend.xml')
    today_str = today.strftime('%Y-%m-%d')
    with open(trend_sitemap_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write(f'  <url>\n    <loc>https://nordrama.live/trending.html</loc>\n    <lastmod>{today_str}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n')
        for item in trend_entries:
            slug = item.get('slug', '')
            folder = item.get('folder', 'movie')
            f.write(f'  <url>\n    <loc>https://nordrama.live/{folder}/{slug}</loc>\n    <lastmod>{today_str}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n')
        f.write('</urlset>')
    log.info(f"   Generated {trend_sitemap_path}")

    # -- Persist --
    all_index += trend_entries
    all_pages  += movie_pages + tv_pages
    save_content_index(all_index)
    save_seen_ids(seen)

    # -- Sitemap --
    generate_sitemap(SITE_URL, BASE_PATH, all_pages)

    total_new = len(movie_pages) + len(tv_pages)
    log.info(f"\n✅ Done — {len(movie_pages)} movies + {len(tv_pages)} TV pages generated")
    log.info(f"   Total index size: {len(all_index)} items")
    log.info(f"   Seen IDs stored: movie={len(seen['movie'])}, tv={len(seen['tv'])}")

    # -- Rebuild homepage --
    try:
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_PATH, 'build_homepage.py')],
                       check=True)
        log.info("   Homepage rebuilt ✅")
    except Exception as e:
        log.warning(f"   Homepage rebuild failed: {e}")

    return total_new


if __name__ == '__main__':
    main()
