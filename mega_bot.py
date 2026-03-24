import requests
import os
import json
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
TMDB_API_KEY = "882e741f7283dc9ba1654d4692ec30f6"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
SITE_URL = "https://tomito.xyz"
BASE_PATH = "/home/tomito/tomito"
DIRS = ['movies', 'series', 'anime', 'actors', 'watch', 'data']

# --- Master Template ---
MASTER_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{TITLE_PAGE}}</title>
  <meta name="description" content="{{META_DESC}}">
  <meta property="og:title" content="{{TITLE_OG}}">
  <meta property="og:description" content="{{META_DESC}}">
  <meta property="og:image" content="{{POSTER_URL}}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="/style.css">
  <link rel="icon" href="{{POSTER_URL}}">
</head>
<body>
  <header class="header">
    <a class="logo" href="/">TOMITO</a>
    <ul class="nav">
      <li><a href="/">الرئيسية</a></li>
      <li><a href="/index#ramadan">رمضان 2026</a></li>
      <li><a href="/movies">أفلام و مسلسلات</a></li>
    </ul>
    <a class="header-btn" href="{{WATCH_URL}}">الموقع الرسمي</a>
  </header>

  <div class="series-hero">
    <img src="{{POSTER_URL}}" alt="{{TITLE_AR}}" loading="eager">
    <div class="series-info">
      <h1 class="series-title" style="display: flex; flex-direction: column; gap: 5px;">
        <span>{{TITLE_AR}}</span>
        <span style="font-size: 0.6em; color: #aaa;">{{TITLE_EN}}</span>
      </h1>
      <div class="series-desc">
        <div style="margin-bottom: 20px; font-family: sans-serif;">{{DESC_EN}}</div>
        <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px; color: #ccc; font-family: 'Tajawal', sans-serif;">{{DESC_AR}}</div>
      </div>
      {{TAGS_SECTION}}

      <div style="margin-top:30px; display:flex; gap:15px; flex-wrap:wrap;">
        <a href="{{WATCH_URL}}" target="_blank" class="btn btn-primary"
          style="background:#e50914; color:#fff; border-radius:6px; font-weight:900; padding:12px 30px; text-decoration:none;">▶
          Watch Now / شاهد الآن</a>
        <a href="{{WATCH_URL}}" target="_blank" class="btn btn-secondary"
          style="background:rgba(255,255,255,0.1); color:#fff; border-radius:6px; font-weight:900; padding:12px 30px; text-decoration:none; border:1px solid rgba(255,255,255,0.2);">⬇
          Download / تحميل</a>
      </div>
    </div>
  </div>

  {{EXTRA_CONTENT}}

  <footer class="footer">
    <p>© 2026 <a href="/">TOMITO MOVIES</a> — جميع الحقوق محفوظة</p>
  </footer>
</body>
</html>"""

# --- Utilities ---
def clean_slug(text):
    if not text: return ""
    res = re.sub(r'[أإآ]', 'ا', text)
    res = re.sub(r'[^\w\s-]', '', res).strip().lower()
    res = re.sub(r'[-\s_]+', '-', res)
    return res

def get_tmdb_data(endpoint, params):
    params['api_key'] = TMDB_API_KEY
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
        if response.status_code == 200: return response.json()
    except: pass
    return None

def fetch_details(tmdb_id, media_type):
    ar_data = get_tmdb_data(f"{media_type}/{tmdb_id}", {'language': 'ar'})
    en_data = get_tmdb_data(f"{media_type}/{tmdb_id}", {'language': 'en'})
    credits = get_tmdb_data(f"{media_type}/{tmdb_id}/credits", {})
    return {'ar': ar_data, 'en': en_data, 'credits': credits}

def generate_seo_description(ar_data, en_data):
    ar_desc = ar_data.get('overview', '') if ar_data else ''
    en_desc = en_data.get('overview', '') if en_data else ''
    k_ar = "مشاهدة وتحميل مباشر، بجودة عالية HD، حصرياً 2026، مترجم عربي."
    k_en = "Watch and download online, High Quality HD, Exclusive 2026, English Subtitles."
    return (f"{ar_desc}\n\n{k_ar}" if ar_desc else k_ar), (f"{en_desc}\n\n{k_en}" if en_desc else k_en)

# --- Page Generation ---
def create_page(item_data, media_type):
    ar, en, credits = item_data['ar'], item_data['en'], item_data['credits']
    if not ar and not en: return None
    
    title_ar = ar.get('title') or ar.get('name') or (en.get('title') or en.get('name') if en else 'Unknown')
    title_en = en.get('title') or en.get('name') or (ar.get('title') or ar.get('name') if ar else 'Unknown')
    tmdb_id = ar.get('id') if ar else en.get('id')
    slug = clean_slug(title_en) or f"{media_type}-{tmdb_id}"
    poster_path = ar.get('poster_path') or en.get('poster_path')
    poster_url = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else "https://www.tomito.xyz/favicon.ico"
    year = (ar.get('release_date') or ar.get('first_air_date') or '2026')[:4]
    rating = ar.get('vote_average', 0)
    desc_ar, desc_en = generate_seo_description(ar, en)
    
    if media_type == 'movie':
        watch_url = f"{SITE_URL}/movie/{tmdb_id}/watch"
    elif 'tv' in media_type:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
    else:
        watch_url = f"{SITE_URL}/watch/{media_type}/{tmdb_id}"
    
    type_label = "Movie | فيلم" if media_type == 'movie' else "TV Series | مسلسل"
    if 'anime' in media_type: type_label = "Anime | أنمي"

    # Extra Content: Cast
    cast_section = '<div class="cast-section" style="padding: 40px 20px; max-width: 1200px; margin: 0 auto;">\n<h2 style="color: #fff; margin-bottom: 20px;">طاقم العمل / Cast</h2>\n<div style="display: flex; gap: 15px; overflow-x: auto; padding-bottom: 10px;">'
    if credits and credits.get('cast'):
        for actor in credits['cast'][:15]:
            cast_section += f'''
            <a href="/actors/{actor["id"]}-{clean_slug(actor["name"])}" style="text-decoration: none; color: #fff; text-align: center; min-width: 100px;">
                <img src="{IMAGE_BASE_URL}{actor["profile_path"] if actor.get("profile_path") else ""}" alt="{actor["name"]}" style="width: 100px; height: 150px; object-fit: cover; border-radius: 8px; border: 1px solid #333;" onerror="this.src='/favicon.ico'">
                <div style="font-size: 0.8em; margin-top: 5px; width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{actor["name"]}</div>
            </a>'''
    cast_section += '</div>\n</div>'

    tags_html = f'<div class="series-tags"><span class="tag">{type_label}</span><span class="tag">⭐ {rating}</span><span class="tag">{year}</span></div>'
    
    html = MASTER_TEMPLATE.replace('{{TITLE_PAGE}}', f'{title_ar} — مشاهدة وتحميل 2026') \
                          .replace('{{META_DESC}}', f'مشاهدة وتحميل {title_ar} ({year}) أون لاين بجودة عالية HD. {desc_ar[:100]}') \
                          .replace('{{TITLE_OG}}', f'{title_ar} / {title_en}') \
                          .replace('{{POSTER_URL}}', poster_url) \
                          .replace('{{WATCH_URL}}', watch_url) \
                          .replace('{{TITLE_AR}}', title_ar) \
                          .replace('{{TITLE_EN}}', title_en) \
                          .replace('{{DESC_AR}}', desc_ar) \
                          .replace('{{DESC_EN}}', desc_en) \
                          .replace('{{TAGS_SECTION}}', tags_html) \
                          .replace('{{EXTRA_CONTENT}}', cast_section)

    folder = 'movies' if media_type == 'movie' else ('anime' if 'anime' in media_type else 'series')
    path = os.path.join(BASE_PATH, folder, f"{slug}.html")
    with open(path, 'w', encoding='utf-8') as f: f.write(html)
    return f"{folder}/{slug}"

def create_actor_page(actor_id):
    ar, en = get_tmdb_data(f"person/{actor_id}", {'language': 'ar'}), get_tmdb_data(f"person/{actor_id}", {'language': 'en'})
    if not en: return None
    name, bio_ar, bio_en = en.get('name'), (ar.get('biography', '') if ar else ''), en.get('biography', '')
    img_url = f"{IMAGE_BASE_URL}{en.get('profile_path')}" if en.get('profile_path') else "https://www.tomito.xyz/favicon.ico"
    slug = f"{actor_id}-{clean_slug(name)}"

    html = MASTER_TEMPLATE.replace('{{TITLE_PAGE}}', f'{name} | ممثلي توميتو') \
                          .replace('{{META_DESC}}', f'تعرف على الممثل {name}، سيرته الذاتية وأهم أعماله لعام 2026.') \
                          .replace('{{TITLE_OG}}', name) \
                          .replace('{{POSTER_URL}}', img_url) \
                          .replace('{{WATCH_URL}}', '#') \
                          .replace('{{TITLE_AR}}', name) \
                          .replace('{{TITLE_EN}}', "Performer / ممثل") \
                          .replace('{{DESC_AR}}', bio_ar) \
                          .replace('{{DESC_EN}}', bio_en) \
                          .replace('{{TAGS_SECTION}}', '') \
                          .replace('{{EXTRA_CONTENT}}', '')

    path = os.path.join(BASE_PATH, 'actors', f"{slug}.html")
    with open(path, 'w', encoding='utf-8') as f: f.write(html)
    return f"actors/{slug}"

# --- Main ---
def main(limit=1000):
    for d in DIRS:
        path = os.path.join(BASE_PATH, d)
        os.makedirs(path, exist_ok=True)
        # Cleanup old .html files
        if d in ['movies', 'series', 'anime', 'actors']:
            for f in os.listdir(path):
                if f.endswith('.html'): os.remove(os.path.join(path, f))
    
    # Increase TMDB page fetching to reach 1000 items (20 per page)
    def fetch_ids(media_type, year, target=1000, genre=None):
        ids = []
        page = 1
        while len(ids) < target and page <= 50:
            params = {
                'primary_release_year' if media_type == 'movie' else 'first_air_date_year': year,
                'page': page,
                'sort_by': 'popularity.desc'
            }
            if genre: params['with_genres'] = genre
            data = get_tmdb_data(f"discover/{media_type}", params)
            if not data or not data.get('results'): break
            for r in data['results']:
                if len(ids) < target: ids.append(r['id'])
            page += 1
        return ids

    movie_ids = fetch_ids('movie', 2026, target=limit)
    tv_ids = fetch_ids('tv', 2026, target=limit)
    anime_ids = fetch_ids('tv', 2026, target=limit, genre='16')
    
    actor_ids = set()
    all_pages = []

    def work(tid, mtype):
        details = fetch_details(tid, mtype)
        if not details: return
        if details['credits'] and details['credits'].get('cast'):
            # Only process top 3 actors as separate pages per item to avoid explosion
            for a in details['credits']['cast'][:3]: actor_ids.add(a['id'])
        url = create_page(details, mtype)
        if url: all_pages.append(f"{SITE_URL}/{url}")

    print(f"Processing {len(movie_ids)} movies, {len(tv_ids)} series, {len(anime_ids)} anime...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        for mid in movie_ids: ex.submit(work, mid, 'movie')
        for tid in tv_ids: ex.submit(work, tid, 'tv')
        for aid in anime_ids: ex.submit(work, aid, 'tv-anime')
    
    print(f"Processing {len(actor_ids)} actors...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        # Capping actors to 1000 per run as requested
        for arid in list(actor_ids)[:1000]: 
            url = create_actor_page(arid)
            if url: all_pages.append(f"{SITE_URL}/{url}")

    with open(os.path.join(BASE_PATH, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write(f'  <url><loc>{SITE_URL}/</loc><priority>1.0</priority></url>\n')
        for url in sorted(all_pages): f.write(f'  <url><loc>{url}</loc><priority>0.8</priority></url>\n')
        f.write('</urlset>')
    print("Execution Finished!")

if __name__ == "__main__":
    main(limit=1000)
