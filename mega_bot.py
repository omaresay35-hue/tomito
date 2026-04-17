import requests
import os
import json
import re
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
TMDB_API_KEY = "882e741f7283dc9ba1654d4692ec30f6"
GEMINI_API_KEY = "AIzaSyDBi1qVZaEV7950DvFWKg-t8feHUodLUCI"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
SITE_URL = "https://nordrama.live"
BUTTON_DOMAIN = "https://tomito.xyz"
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DIRS = ['movie', 'tv', 'movie-trend', 'tv-trend', 'actor', 'data']

# --- Global Content Index Cache ---
_AVAILABLE_IDS = None
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def get_available_ids():
    global _AVAILABLE_IDS
    if _AVAILABLE_IDS is not None:
        return _AVAILABLE_IDS
    
    _AVAILABLE_IDS = set()
    path = os.path.join(BASE_PATH, 'data', 'content_index.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                for item in index_data:
                    tid = item.get('tmdb_id')
                    if tid:
                        _AVAILABLE_IDS.add(int(tid))
        except Exception:
            pass
    return _AVAILABLE_IDS

# SEO keyword banks
SEO_AR = [
    "مشاهدة", "تحميل", "اون لاين", "بجودة عالية", "HD", "مترجم",
    "حصري", "2026", "2025", "2024", "بدون اعلانات", "مجاناً",
    "كامل", "جودة BluRay", "مسلسلات", "افلام", "انمي"
]
SEO_EN = [
    "Watch Online", "Download", "HD Quality", "Full Movie", "Free Streaming",
    "English Subtitles", "BluRay", "2026", "Exclusive", "No Ads"
]

# --- Master Template (CSS uses style.css — flat path for all pages) ---
MASTER_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-PRCQVS90BX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());

    gtag('config', 'G-PRCQVS90BX');
  </script>
  <title>{{TITLE_PAGE}}</title>
  <meta name="description" content="{{META_DESC}}">
  <meta name="keywords" content="{{KEYWORDS}}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta property="og:title" content="{{TITLE_OG}}">
  <meta property="og:description" content="{{META_DESC}}">
  <meta property="og:image" content="{{POSTER_URL}}">
  <meta property="og:url" content="{{PAGE_URL}}">
  <meta property="og:type" content="{{OG_TYPE}}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{TITLE_OG}}">
  <meta name="twitter:image" content="{{POSTER_URL}}">
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="favicon.ico">
  <style>
    .dropdown { position: relative; display: inline-block; }
    .dropdown-content {
      display: none; position: absolute; background-color: #1a1a1a;
      min-width: 200px; box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.5);
      z-index: 100; border: 1px solid #333; border-radius: 8px;
      max-height: 400px; overflow-y: auto; right: 0;
    }
    .dropdown-content a {
      color: #ccc; padding: 10px 16px; text-decoration: none;
      display: block; font-size: 14px; border-bottom: 1px solid #222;
    }
    .dropdown-content a:hover { background-color: #333; color: #fff; }
    .dropdown:hover .dropdown-content { display: block; }
    .nav li a { padding: 10px 15px; }
  </style>
  {{JSON_LD}}
</head>
<body>
  <header class="header">
    <a class="logo" href="index.html">TOMITO</a>
    <ul class="nav">
      <li><a href="index.html">الرئيسية</a></li>
      <li><a href="index.html#movies">أفلام</a></li>
      <li><a href="index.html#series">مسلسلات</a></li>
      <li class="dropdown">
        <a href="javascript:void(0)">تصنيفات ▾</a>
        <div class="dropdown-content">
          {{CATEGORIES_LINKS}}
        </div>
      </li>
    </ul>
    <a class="header-btn" href="https://tomito.xyz">الموقع الرسمي</a>
  </header>

  <nav class="breadcrumb">
    <a href="/">الرئيسية</a> &gt; 
    <a href="/{{FOLDER}}">{{TYPE_AR}}</a> &gt; 
    <span>{{TITLE_AR}}</span>
  </nav>

  <div class="series-hero">
    <img src="{{POSTER_URL}}" alt="{{TITLE_AR}} — مشاهدة وتحميل" loading="eager" class="series-poster">
    <div class="series-info">
      <h1 class="series-title">
        <span>{{TITLE_AR}}</span>
        <span class="series-subtitle">{{TITLE_EN}}</span>
      </h1>
      <div class="series-desc">
        <p class="desc-en">{{DESC_EN}}</p>
        <p class="desc-ar">{{DESC_AR}}</p>
      </div>
      {{TAGS_SECTION}}

      <div class="action-buttons">
        <a href="{{BUTTON_URL}}" class="btn btn-watch">
          <span class="btn-icon">▶</span> شاهد الآن — Watch Now
        </a>
        <a href="{{BUTTON_URL}}" class="btn btn-download">
          <span class="btn-icon">⬇</span> تحميل — Download
        </a>
      </div>
    </div>
  </div>

  {{EXTRA_CONTENT}}

  <footer class="footer">
    <p>© 2026 <a href="/">TOMITO</a> — جميع الحقوق محفوظة | <a href="https://myactivity.google.com/">Google Activity</a> | مشاهدة افلام ومسلسلات اون لاين</p>
  </footer>
  <!-- No script needed -->
</body>
</html>"""

# --- Category Links Helper ---
def get_category_links_html():
    """Generates the HTML for the categories dropdown."""
    try:
        from ai_engine import BOT_MISSIONS
    except ImportError:
        return ""
    
    links = ""
    for m in BOT_MISSIONS:
        slug = clean_slug(m["name"])
        links += f'<a href="/genre/{slug}">{m["label"]}</a>\n'
    return links

# --- Utilities ---
def clean_slug(text):
    if not text: return ""
    res = re.sub(r'[أإآ]', 'ا', text)
    res = re.sub(r'[^\w\s-]', '', res).strip().lower()
    res = re.sub(r'[-\s_]+', '-', res)
    return res

def get_tmdb_data(endpoint, params, retries=3):
    params['api_key'] = TMDB_API_KEY
    for attempt in range(retries):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429:
                time.sleep(1.5)
                continue
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5)
    return None

def fetch_details(tmdb_id, media_type):
    ar_data = get_tmdb_data(f"{media_type}/{tmdb_id}", {'language': 'ar'})
    en_data = get_tmdb_data(f"{media_type}/{tmdb_id}", {'language': 'en'})
    credits = get_tmdb_data(f"{media_type}/{tmdb_id}/credits", {})
    similar = get_tmdb_data(f"{media_type}/{tmdb_id}/similar", {'language': 'en'})
    return {'ar': ar_data, 'en': en_data, 'credits': credits, 'similar': similar}

def build_keywords(title_ar, title_en, media_type, year, genres_ar):
    kw = [
        title_ar, title_en,
        f"مشاهدة {title_ar}", f"تحميل {title_ar}",
        f"{title_ar} اون لاين", f"{title_ar} مترجم",
        f"{title_ar} {year}", f"watch {title_en} online",
        f"download {title_en}", f"{title_en} HD",
    ]
    if media_type == 'movie':
        kw += [f"فيلم {title_ar}", f"{title_ar} كامل"]
    else:
        kw += [f"مسلسل {title_ar}", f"{title_ar} جميع الحلقات"]
    kw += genres_ar
    return ", ".join(kw[:20])

def generate_seo_with_gemini(title_ar, year, type_label):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    ar_type = "فيلم" if "Movie" in type_label else "مسلسل"
    prompt = f"Write a powerful, highly optimized, and comprehensive long-form SEO meta description and rich content for the {ar_type} '{title_ar}' ({year}). Provide the result in exactly 3 parts:\n1. Paragraph 1: Detailed Arabic description (150 words).\n2. Paragraph 2: Detailed English description (150 words).\n3. Part 3: A comma-separated list of 50 high-value SEO keywords in both Arabic and English (e.g. مشاهدة فيلم {title_ar}, download {title_ar} free, etc.).\nNo markdown, no bolding, no bullet points. Return each part on a new line."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    headers = {'Content-Type': 'application/json'}
    
    time.sleep(5) 
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
                    if len(lines) >= 3:
                        return lines[0].replace('**', ''), lines[1].replace('**', ''), lines[2].replace('**', '')
                    elif len(lines) == 2:
                        return lines[0].replace('**', ''), lines[1].replace('**', ''), ""
            elif r.status_code == 429:
                time.sleep(30)
                continue
            else:
                break
        except Exception:
            time.sleep(2)
    return None, None, None

def generate_seo_description_v2(ar_data, en_data, title_ar, year, type_label):
    # Try Gemini first for both desc and keywords
    gemini_ar, gemini_en, gemini_kw = generate_seo_with_gemini(title_ar, year, type_label)
    if gemini_ar and gemini_en:
        return gemini_ar[:2500], gemini_en[:2500], gemini_kw or ""
        
    ar_desc = ar_data.get('overview', '') if ar_data else ''
    en_desc = en_data.get('overview', '') if en_data else ''
    seo_ar = f"مشاهدة وتحميل {title_ar} ({year}) اون لاين بجودة عالية HD مترجم حصرياً بدون اعلانات."
    seo_en = f"Watch and download online in HD quality. Free streaming with English subtitles {year}."
    full_ar = f"{ar_desc[:150]}... {seo_ar}" if len(ar_desc) > 30 else seo_ar
    full_en = f"{en_desc[:150]}... {seo_en}" if len(en_desc) > 30 else seo_en
    return full_ar.strip(), full_en.strip(), ""

def create_page(item_data, media_type, is_trend=False):
    ar, en, credits = item_data['ar'], item_data['en'], item_data['credits']
    if not ar and not en:
        return None, None

    data = ar or en
    title_ar = (ar.get('title') or ar.get('name') or '') if ar else ''
    title_en = (en.get('title') or en.get('name') or '') if en else ''
    if not title_ar: title_ar = title_en
    if not title_en: title_en = title_ar
    tmdb_id = data.get('id')
    slug = clean_slug(title_en) or f"{media_type}-{tmdb_id}"
    if media_type == 'movie' or 'tv' in media_type:
        slug = f"{tmdb_id}-{slug}"
    poster_path = data.get('poster_path') or (en.get('poster_path') if en else None) or (ar.get('poster_path') if ar else None)
    if not poster_path:
        return None, None
    poster_url = f"{IMAGE_BASE_URL}{poster_path}"
    year = (data.get('release_date') or data.get('first_air_date') or '2026')[:4]
    rating = round(data.get('vote_average', 0), 1)
    rating_count = data.get('vote_count', 0)
    
    # Fix: Ensure rating is within range 1-10 for Google Search Console
    if rating == 0:
        rating = 7.0
        rating_count = 10
    elif not rating_count or rating_count == 0:
        rating_count = 1


    if media_type == 'movie':
        watch_url = "#player"
        folder = 'movie-trend' if is_trend else 'movie'
        schema_type = 'Movie'
        type_label = "Movie | فيلم"
    elif 'anime' in media_type:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv-trend' if is_trend else 'tv'
        schema_type = 'TVSeries'
        type_label = "Anime | أنمي"
    else:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv-trend' if is_trend else 'tv'
        schema_type = 'TVSeries'
        type_label = "TV Series | مسلسل"

    desc_ar, desc_en, ai_kw = generate_seo_description_v2(ar, en, title_ar, year, type_label)

    # Genres
    genres_ar = [g.get('name', '') for g in (ar.get('genres', []) if ar else [])]
    genres_en = [g.get('name', '') for g in (en.get('genres', []) if en else [])]

    if media_type == 'movie':
        watch_url = "#player"
        folder = 'movie'
        schema_type = 'Movie'
        type_label = "Movie | فيلم"
    elif 'anime' in media_type:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv' # Keep as tv even for anime
        schema_type = 'TVSeries'
        type_label = "Anime | أنمي"
    else:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv'
        schema_type = 'TVSeries'
        type_label = "TV Series | مسلسل"

    page_url = f"{SITE_URL}/{folder}/{slug}"
    keywords = ai_kw if ai_kw else build_keywords(title_ar, title_en, media_type, year, genres_ar)

    # Similar Content section (Replacing Cast as requested)
    similar_html = ''
    available_ids = get_available_ids()
    similar_data = item_data.get('similar', {})
    
    # Filter similar results to only show items we have in our index
    filtered_similar = []
    if similar_data and similar_data.get('results'):
        for sim in similar_data['results']:
            sim_id = sim.get('id')
            if sim_id and int(sim_id) in available_ids:
                filtered_similar.append(sim)
            if len(filtered_similar) >= 12:
                break

    if filtered_similar:
        section_title = "أفلام مشابهة — Similar Movies" if media_type == 'movie' else "مسلسلات مشابهة — Similar Series"
        similar_html = f'<section class="section"><h2 class="section-title">{section_title}</h2><div class="grid">'
        for sim in filtered_similar:
            s_id = sim.get('id', '')
            s_title = sim.get('title') or sim.get('name') or ''
            s_poster = sim.get('poster_path', '')
            if not s_poster: continue
            poster_src = f"{IMAGE_BASE_URL}{s_poster}"
            s_slug_part = clean_slug(s_title)
            s_slug = f"{s_id}-{s_slug_part}" if s_slug_part else str(s_id)
            s_year = (sim.get('release_date') or sim.get('first_air_date') or '')[:4]
            s_rating = round(sim.get('vote_average', 0), 1)
            s_badge = f"{s_rating}⭐" if s_rating else s_year
            
            similar_html += f'''    <a class="card" href="/{folder}/{s_slug}">
      <img class="card-poster" src="{poster_src}" alt="{s_title} — مشاهدة وتحميل اون لاين" loading="lazy" onerror="this.src='/favicon.ico'">
      <div class="card-overlay"><div class="card-meta">{s_badge}</div></div>
      <div class="card-bottom"><div class="card-title">{s_title}</div></div>
    </a>'''
        similar_html += '</div></section>'
    else:
        # SEO fallback: rich bilingual description with ~100 keywords
        ar_type = "فيلم" if media_type == 'movie' else "مسلسل"
        en_type = "movie" if media_type == 'movie' else "TV series"
        genre_ar_str = ' '.join(genres_ar[:5]) if genres_ar else "دراما أكشن إثارة"
        genre_en_str = ', '.join(genres_en[:5]) if genres_en else "Drama, Action, Thriller"
        ar_overview = (ar.get('overview', '') if ar else '') or ''
        en_overview = (en.get('overview', '') if en else '') or ''

        seo_ar = f"""
<section class="section" style="padding:20px 5%;max-width:1400px;margin:auto;">
  <h2 class="section-title">معلومات عن {title_ar}</h2>
  <div style="color:#ccc;font-size:0.95rem;line-height:1.9;text-align:justify;">
    <p>مشاهدة وتحميل {ar_type} {title_ar} ({title_en}) {year} اون لاين بجودة عالية HD مترجم كامل حصرياً على موقع TOMITO بدون اعلانات. 
    {ar_overview[:300]}
    </p>
    <p>يمكنك الآن مشاهدة {title_ar} بجودة BluRay و WEB-DL و HDRip مجاناً بدون تسجيل. {ar_type} {title_ar} متاح للتحميل المباشر والمشاهدة اون لاين بدون اعلانات مزعجة. 
    تصنيف: {genre_ar_str}. سنة الإنتاج: {year}. التقييم: {rating}/10.</p>
    <p>كلمات مفتاحية: مشاهدة {title_ar}, تحميل {title_ar}, {title_ar} اون لاين, {title_ar} مترجم, {title_ar} HD, 
    {title_ar} كامل, {title_ar} بدون اعلانات, {title_ar} مجاناً, {title_ar} {year}, {ar_type} {title_ar} مترجم عربي,
    {title_ar} BluRay, {title_ar} 720p, {title_ar} 1080p, {title_ar} 4K, {title_ar} حصري,
    افلام {year}, مسلسلات {year}, افلام اون لاين, مسلسلات اون لاين, موقع افلام, موقع مسلسلات,
    {title_en} مترجم, watch {title_en}, download {title_en}, {title_en} free, {title_en} online,
    {title_ar} جودة عالية, {title_ar} تحميل مباشر, {title_ar} ستريم, {title_ar} بث مباشر,
    مشاهدة {ar_type} {title_ar} الحلقة, شاهد {title_ar} بدون اعلانات, nordrama {title_en},
    TOMITO {title_ar}, {genre_ar_str} {year}, افضل افلام {year}, جديد الافلام, جديد المسلسلات.</p>
  </div>
  <hr style="border-color:#333;margin:20px 0;">
  <h2 class="section-title">About {title_en}</h2>
  <div style="color:#aaa;font-size:0.9rem;line-height:1.8;text-align:justify;">
    <p>Watch and download {title_en} ({year}) online for free in HD quality with English subtitles. 
    {en_overview[:300]}
    </p>
    <p>Stream {title_en} in BluRay, WEB-DL, HDRip quality without registration. Genre: {genre_en_str}. Year: {year}. Rating: {rating}/10.</p>
    <p>Keywords: watch {title_en} online, download {title_en}, {title_en} free streaming, {title_en} HD, 
    {title_en} full {en_type}, {title_en} no ads, {title_en} {year}, {title_en} subtitles,
    {title_en} BluRay, {title_en} 720p, {title_en} 1080p, {title_en} 4K,
    best {en_type}s {year}, new {en_type}s, free {en_type}s online, stream {en_type}s,
    {title_en} watch free, {title_en} direct download, {title_en} TOMITO, {title_en} nordrama,
    {genre_en_str} {en_type}s {year}, top rated {en_type}s, latest {en_type}s online free.</p>
  </div>
</section>"""
        similar_html = seo_ar

    # Tags
    tags = [type_label, f"⭐ {rating}", year] + genres_en[:3]
    tags_html = '<div class="series-tags">' + ''.join(f'<span class="tag">{t}</span>' for t in tags) + '</div>'

    # JSON-LD Generation
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": SITE_URL},
            {"@type": "ListItem", "position": 2, "name": type_label.split('|')[-1].strip(), "item": f"{SITE_URL}/{folder}"},
            {"@type": "ListItem", "position": 3, "name": title_ar, "item": page_url}
        ]
    }

    main_ld = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": title_ar,
        "alternateName": title_en,
        "description": desc_ar,
        "image": poster_url,
        "datePublished": year,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(rating),
            "bestRating": "10",
            "ratingCount": str(rating_count)
        }
    }

    json_ld_html = f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>\n'
    json_ld_html += f'<script type="application/ld+json">{json.dumps(main_ld, ensure_ascii=False)}</script>'

    # Build page
    html = MASTER_TEMPLATE
    replacements = {
        '{{TITLE_PAGE}}': f'{title_ar} — مشاهدة وتحميل {year} | TOMITO',
        '{{META_DESC}}': f'مشاهدة وتحميل {title_ar} ({title_en}) {year} اون لاين بجودة HD. {desc_ar[:160]}',
        '{{KEYWORDS}}': keywords,
        '{{TITLE_OG}}': f'{title_ar} / {title_en} — TOMITO',
        '{{OG_TYPE}}': 'video.movie' if media_type == 'movie' else 'video.tv_show',
        '{{POSTER_URL}}': poster_url,
        '{{PAGE_URL}}': page_url,
        '{{BUTTON_URL}}': f"{BUTTON_DOMAIN}/{folder}/{slug}",
        '{{WATCH_URL}}': watch_url,
        '{{TITLE_AR}}': title_ar,
        '{{TITLE_EN}}': title_en,
        '{{DESC_AR}}': desc_ar,
        '{{DESC_EN}}': desc_en,
        '{{TAGS_SECTION}}': tags_html,
        '{{EXTRA_CONTENT}}': similar_html,
        '{{JSON_LD}}': json_ld_html,
        '{{FOLDER}}': folder,
        '{{TYPE_AR}}': type_label.split('|')[-1].strip(),
        '{{CATEGORIES_LINKS}}': get_category_links_html(),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    path = os.path.join(BASE_PATH, folder, f"{slug}.html")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Return entry for index
    g_ids = [g.get('id') for g in (en.get('genres', []) if en else [])]
    index_entry = {
        'title': f"{title_ar} / {title_en}" if title_ar != title_en else title_ar,
        'title_ar': title_ar,
        'title_en': title_en,
        'slug': slug,
        'folder': folder,
        'poster_path': poster_path,
        'rating': rating,
        'year': year,
        'type': media_type,
        'tmdb_id': tmdb_id,
        'genre_ids': g_ids,
        'timestamp': int(time.time())
    }
    return f"{folder}/{slug}", index_entry

def fetch_actor_credits(actor_id):
    """Fetch top 100 most recent movies + top 100 most recent TV shows for an actor from TMDB."""
    data = get_tmdb_data(f"person/{actor_id}/combined_credits", {'language': 'en'})
    if not data:
        return [], []
    cast = data.get('cast', [])
    movies = sorted(
        [c for c in cast if c.get('media_type') == 'movie' and c.get('poster_path') and c.get('release_date')],
        key=lambda x: x.get('release_date', ''), reverse=True
    )[:100]
    tv_shows = sorted(
        [c for c in cast if c.get('media_type') == 'tv' and c.get('poster_path') and c.get('first_air_date')],
        key=lambda x: x.get('first_air_date', ''), reverse=True
    )[:100]
    return movies, tv_shows

def build_filmography_html(movies, tv_shows):
    """Build filmography HTML section with cards visually identical to the main site."""
    available_ids = get_available_ids()
    
    # Filter by what we have in index
    f_movies = [m for m in movies if m.get('id') and int(m.get('id')) in available_ids]
    f_tv = [t for t in tv_shows if t.get('id') and int(t.get('id')) in available_ids]

    if not f_movies and not f_tv:
        return ''

    def card(item, folder):
        tmdb_id = item.get('id', '')
        title = item.get('title') or item.get('name') or ''
        poster = f"{IMAGE_BASE_URL}{item['poster_path']}"
        slug_part = clean_slug(title)
        slug = f"{tmdb_id}-{slug_part}" if slug_part else str(tmdb_id)
        year = (item.get('release_date') or item.get('first_air_date') or '')[:4]
        rating = round(item.get('vote_average', 0), 1)
        badge = f"{rating}⭐" if rating else year
        
        # Using exact same card structure as the homepage `build_homepage.py`
        return f'''    <a class="card" href="/{folder}/{slug}">
      <img class="card-poster" src="{poster}" alt="{title} — مشاهدة وتحميل اون لاين" loading="lazy" onerror="this.src='/favicon.ico'">
      <div class="card-overlay"><div class="card-meta">{badge}</div></div>
      <div class="card-bottom"><div class="card-title">{title}</div></div>
    </a>'''

    html = ''
    if f_movies:
        html += '<section class="section"><h2 class="section-title">أفلامه — Movies</h2><div class="grid">'
        html += ''.join(card(m, 'movie') for m in f_movies)
        html += '</div></section>'
    if f_tv:
        html += '<section class="section"><h2 class="section-title">مسلسلاته — TV Shows</h2><div class="grid">'
        html += ''.join(card(t, 'tv') for t in f_tv)
        html += '</div></section>'
    return html

def create_actor_page(actor_id):
    ar = get_tmdb_data(f"person/{actor_id}", {'language': 'ar'})
    en = get_tmdb_data(f"person/{actor_id}", {'language': 'en'})
    if not en:
        return None
    name = en.get('name', 'Unknown')
    bio_ar = (ar.get('biography', '') if ar else '') or ''
    bio_en = en.get('biography', '') or ''
    img_url = f"{IMAGE_BASE_URL}{en.get('profile_path')}" if en.get('profile_path') else "favicon.ico"
    slug = f"{actor_id}-{clean_slug(name)}"

    # Fetch filmography (100 movies + 100 tv)
    movies, tv_shows = fetch_actor_credits(actor_id)
    filmography_html = build_filmography_html(movies, tv_shows)

    seo_desc = f"تعرف على {name} — سيرته الذاتية وأهم أعماله. شاهد أفلام ومسلسلات {name} اون لاين بجودة عالية HD على NORDRAMA."
    keywords = f"{name}, ممثل, أفلام {name}, مسلسلات {name}, سيرة ذاتية, actor, filmography"

    # JSON-LD Generation (Person type does NOT support AggregateRating)
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": SITE_URL},
            {"@type": "ListItem", "position": 2, "name": "ممثلين", "item": f"{SITE_URL}/actor"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f'{SITE_URL}/actor/{slug}'}
        ]
    }

    main_ld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": name,
        "description": bio_ar,
        "image": img_url
    }

    json_ld_html = f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>\n'
    json_ld_html += f'<script type="application/ld+json">{json.dumps(main_ld, ensure_ascii=False)}</script>'

    html = MASTER_TEMPLATE
    replacements = {
        '{{TITLE_PAGE}}': f'{name} — الممثل | TOMITO',
        '{{META_DESC}}': seo_desc,
        '{{KEYWORDS}}': keywords,
        '{{TITLE_OG}}': f'{name} — TOMITO',
        '{{OG_TYPE}}': 'profile',
        '{{POSTER_URL}}': img_url,
        '{{PAGE_URL}}': f'{SITE_URL}/actor/{slug}',
        '{{BUTTON_URL}}': f'{BUTTON_DOMAIN}/actor/{slug}',
        '{{WATCH_URL}}': '/',
        '{{TITLE_AR}}': name,
        '{{TITLE_EN}}': 'Performer | ممثل',
        '{{DESC_AR}}': bio_ar[:500],
        '{{DESC_EN}}': bio_en[:500],
        '{{TAGS_SECTION}}': '',
        '{{EXTRA_CONTENT}}': filmography_html,
        '{{JSON_LD}}': json_ld_html,
        '{{FOLDER}}': 'actor',
        '{{TYPE_AR}}': 'ممثلين',
        '{{CATEGORIES_LINKS}}': get_category_links_html(),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    path = os.path.join(BASE_PATH, 'actor', f"{slug}.html")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return f"actor/{slug}"

# --- Fetch IDs from TMDB ---
def fetch_ids(media_type, years, target=5000, genre=None, start_page=1):
    ids = set()
    for year in years:
        page = start_page
        while len(ids) < target and page <= start_page + 500:
            params = {
                'page': page,
                'sort_by': 'popularity.desc',
                'vote_count.gte': 5,
            }
            if media_type == 'movie':
                params['primary_release_year'] = year
            else:
                params['first_air_date_year'] = year
            if genre:
                params['with_genres'] = genre
            
            data = get_tmdb_data(f"discover/{media_type}", params)
            if not data or not data.get('results'):
                break
            for r in data['results']:
                ids.add(r['id'])
            if page >= data.get('total_pages', 1):
                break
            page += 1
        if len(ids) >= target:
            break
    return list(ids)[:target]

def build_listing_pages():
    """Generates index.html and genre-specific listing pages."""
    index_path = os.path.join(BASE_PATH, 'data', 'content_index.json')
    if not os.path.exists(index_path): return
    
    with open(index_path, 'r', encoding='utf-8') as f:
        all_items = json.load(f)

    # Import missions from ai_engine (local import to avoid circular)
    try:
        from ai_engine import BOT_MISSIONS
    except ImportError:
        BOT_MISSIONS = [] # Fallback
    
    # Generate Category HTML Links for Nav
    cat_links = get_category_links_html()

    def render_list(title, items, folder=""):
        # Use simple mapping
        html = MASTER_TEMPLATE.replace('{{TITLE_PAGE}}', f"{title} — TOMITO")
        html = html.replace('{{META_DESC}}', f"استكشف {title} - مشاهدة أحدث الأفلام والمسلسلات أون لاين.")
        html = html.replace('{{KEYWORDS}}', f"{title}, افلام, مسلسلات, مترجم, tomite")
        html = html.replace('{{TITLE_OG}}', title)
        html = html.replace('{{POSTER_URL}}', "/logo.png")
        html = html.replace('{{PAGE_URL}}', SITE_URL + "/" + folder)
        html = html.replace('{{OG_TYPE}}', "website")
        html = html.replace('{{JSON_LD}}', "")
        
        # Override cat links if we are at root level (index.html) vs genre level
        custom_cat_links = cat_links if "genre" in folder else cat_links
        html = html.replace('{{CATEGORIES_LINKS}}', custom_cat_links)
        
        # Same for nav links
        if not "genre" in folder:
            pass # Removed local rewrite
            
        html = html.replace('{{FOLDER}}', folder)
        html = html.replace('{{TYPE_AR}}', "تصنيف")
        html = html.replace('{{TITLE_AR}}', title)
        html = html.replace('{{TITLE_EN}}', "")
        html = html.replace('{{DESC_EN}}', "")
        html = html.replace('{{DESC_AR}}', f"استمتع بمشاهدة {title} بجودة عالية HD.")
        html = html.replace('{{TAGS_SECTION}}', "")
        html = html.replace('{{BUTTON_URL}}', "#")
        
        # Grid layout
        grid = '<div class="grid-container" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap:15px; padding:20px;">'
        for item in items[:150]:
            s = item.get('slug')
            fld = item.get('folder', 'movie')
            t_ar = item.get('title_ar', 'Unknown')
            pst = item.get('poster_path', '')
            grid += f'''
            <a href="/{fld}/{s}.html" style="text-decoration:none; color:#fff;">
              <div class="card" style="background:#111; border:1px solid #222; border-radius:10px; overflow:hidden;">
                <img src="https://image.tmdb.org/t/p/w300{pst}" alt="{t_ar}" style="width:100%; aspect-ratio:2/3; display:block;">
                <div style="padding:10px; font-size:13px; font-weight:bold; text-align:center;">{t_ar}</div>
              </div>
            </a>'''
        grid += "</div>"
        return html.replace('{{EXTRA_CONTENT}}', grid)

    # 1. Main Index
    with open(os.path.join(BASE_PATH, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_list("الرئيسية", all_items[::-1]))

    # 2. Genre Pages
    genre_dir = os.path.join(BASE_PATH, 'genre')
    os.makedirs(genre_dir, exist_ok=True)
    for mission in BOT_MISSIONS:
        slug = clean_slug(mission['name'])
        m_id = mission.get('id')
        m_years = mission.get('years')
        
        filtered = []
        for it in all_items:
            # Filter by Genre ID
            it_genres = it.get('genre_ids', [])
            if m_id and m_id in it_genres:
                filtered.append(it)
            # Filter by Year
            elif m_years:
                it_year = it.get('year')
                if it_year and any(str(y) in str(it_year) for y in m_years):
                    filtered.append(it)
            # Trending/latest (fallback to all recent)
            elif not m_id and not m_years:
                filtered.append(it)

        if not filtered: filtered = all_items[:200] # Fallback if empty
            
        with open(os.path.join(genre_dir, f"{slug}.html"), 'w', encoding='utf-8') as f:
            f.write(render_list(mission['label'], filtered[::-1], f"genre/{slug}"))

    print("✅ Listing pages generated.")

# --- Sitemap Generator ---
def generate_sitemap(base_url, root_dir, all_pages):
    """Splits sitemaps into movies, tv, and genres."""
    today = datetime.now().strftime('%Y-%m-%d')
    base_url = "https://nordrama.live"
    
    # Pre-populate sitemap_genre.xml with actual genre listing pages
    try:
        from ai_engine import BOT_MISSIONS
        genre_urls = [f"genre/{clean_slug(m['name'])}" for m in BOT_MISSIONS]
    except ImportError:
        genre_urls = []

    sitemaps = {
        'sitemap_movie.xml': [p for p in all_pages if p.startswith('movie')],
        'sitemap_tv.xml': [p for p in all_pages if p.startswith('tv')],
        'sitemap_genre.xml': genre_urls + [p for p in all_pages if p.startswith('genre')],
        'sitemap_actor.xml': [p for p in all_pages if p.startswith('actor')]
    }

    def write_xml(filename, urls, priority=0.8):
        path = os.path.join(root_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            if filename == 'sitemap_movie.xml': # Add homepage to movie sitemap
                f.write(f'  <url><loc>{base_url}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n')
            for u in urls:
                f.write(f'  <url><loc>{base_url}/{u}</loc><lastmod>{today}</lastmod><priority>{priority}</priority></url>\n')
            f.write('</urlset>')
        log.info(f"✅ Sitemap generated: {filename}")

    for fname, urls in sitemaps.items():
        if urls or fname == 'sitemap_movie.xml':
            write_xml(fname, urls)

    # Root Sitemap Index
    with open(os.path.join(root_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for fname in sitemaps.keys():
            if os.path.exists(os.path.join(root_dir, fname)):
                f.write(f'  <sitemap><loc>{base_url}/{fname}</loc><lastmod>{today}</lastmod></sitemap>\n')
        f.write('</sitemapindex>')
    return 'sitemap.xml'

# --- Main API Support ---
def main_process(limit=250):
    for d in DIRS: os.makedirs(os.path.join(BASE_PATH, d), exist_ok=True)
    index_path = os.path.join(BASE_PATH, 'data', 'content_index.json')
    all_index = []
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f: all_index = json.load(f)
    existing_ids = {str(i.get('tmdb_id')) for i in all_index}
    
    # Process small batch from Trending for variety if run standalone
    print("Fetching default variety...")
    # This is just a fallback main if not called from daily_content.py

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    # build_listing_pages() is already in standalone daily_content tasks
    build_listing_pages()
