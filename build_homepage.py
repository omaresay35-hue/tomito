#!/usr/bin/env python3
"""Build index.html from data/content_index.json + existing ramadan-trailer pages."""

import os
import json

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://nordrama.live"

def load_index():
    path = os.path.join(BASE_PATH, 'data', 'content_index.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_trending():
    trends = []
    for fname in ['trend_movies.json', 'trend_tv.json']:
        path = os.path.join(BASE_PATH, 'data', fname)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    trends.extend(json.load(f))
            except Exception:
                pass
    return trends

def card_html(item):
    """Generate a card HTML block for a content item."""
    poster = item.get('poster', '/favicon.ico')
    title = item.get('title', '')
    folder = item.get('folder', 'movie')
    slug = item.get('slug', '')
    href = f"/{folder}/{slug}" # Clean URL
    rating = item.get('rating', '')
    badge = f"{rating}⭐" if rating else "حصري"
    
    return f'''    <a class="card" href="{href}" style="text-decoration:none;">
      <img class="card-poster" src="{poster}" alt="{title} — مشاهدة وتحميل اون لاين" loading="lazy" onerror="this.src='/favicon.ico'">
      <div class="card-overlay"><div class="card-meta">{badge}</div></div>
      <div class="card-bottom"><div class="card-title">{title}</div></div>
    </a>'''

def build_carousel(trends):
    if not trends: return ''
    # Top 50 by sort
    trends = sorted(trends, key=lambda x: str(x.get('year', '')), reverse=True)[:50]
    
    cards = ''
    for item in trends:
        folder = item.get('folder', 'movie')
        slug = item.get('slug', '')
        href = f"/{folder}/{slug}"
        poster = item.get('poster', '/favicon.ico')
        title = item.get('title', '')
        rating = item.get('rating', '')
        badge = f"{rating}⭐" if rating else "جديد"
        
        cards += f'''
        <a href="{href}" class="trend-card" title="{title}">
            <div class="trend-badge">{badge}</div>
            <img src="{poster}" alt="{title}" loading="lazy" onerror="this.src='/favicon.ico'">
        </a>'''
        
    css = '''
    <style>
    .trending-container { margin: 20px auto; padding: 0 5%; max-width: 1400px; }
    .trending-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .trending-header h2 { color: #fff; font-size: 1.3rem; margin: 0; font-weight: 700; display: flex; align-items: center; gap: 8px;}
    .trending-header a { color: #FF6D1F; font-size: 0.95rem; text-decoration: none; font-weight: bold; background: rgba(255, 109, 31, 0.1); padding: 4px 12px; border-radius: 20px; transition: 0.2s;}
    .trending-header a:hover { background: #FF6D1F; color: #fff; }
    .slim-carousel { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; -ms-overflow-style: none; }
    .slim-carousel::-webkit-scrollbar { display: none; }
    .trend-card { flex: 0 0 130px; position: relative; border-radius: 10px; overflow: hidden; display: block; aspect-ratio: 2/3; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    .trend-card:hover { transform: scale(1.05) translateY(-5px); z-index: 10; box-shadow: 0 8px 20px rgba(0,0,0,0.5); }
    .trend-card img { width: 100%; height: 100%; object-fit: cover; }
    .trend-badge { position: absolute; top: 6px; right: 6px; background: rgba(255, 109, 31, 0.9); color: #fff; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; z-index: 2; font-weight: bold; backdrop-filter: blur(4px); }
    @media (max-width: 768px) { .trend-card { flex: 0 0 105px; } .trending-container { padding: 0 15px; } }
    </style>
    '''
    
    html = f'''
    {css}
    <section class="trending-container" id="trending">
      <div class="trending-header">
        <h2>🔥 التريند الآن</h2>
        <a href="/trending/">عرض الكل &gt;</a>
      </div>
      <div class="slim-carousel">
        {cards}
      </div>
    </section>
    '''
    return html

def build_trending_page(trends, base_html):
    if not trends: return
    trends.sort(key=lambda x: str(x.get('year', '')), reverse=True)
    cards = '\n'.join(card_html(i) for i in trends)
    
    section = f'''
<section class="section" style="margin-top:20px;">
  <h2 class="section-title">🔥 التريند الآن — Trending Now</h2>
  <div class="grid">
{cards}
  </div>
</section>'''

    # Replace sections reliably instead of relying on exact whitespace
    page_html = base_html.replace('{movies_section}', section).replace('{series_section}', '').replace('{anime_section}', '')
    # Update title
    page_html = page_html.replace('<title>TOMITO', '<title>التريند الآن | TOMITO')
    
    trending_dir = os.path.join(BASE_PATH, 'trending')
    os.makedirs(trending_dir, exist_ok=True)
    out_path = os.path.join(trending_dir, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(page_html)

def build():
    index = load_index()
    
    # Sort by year descending (approximate "Newest")
    index.sort(key=lambda x: str(x.get('year', '')), reverse=True)
    
    # Split by type
    movies = [i for i in index if i.get('folder') == 'movie'][:60]
    series = [i for i in index if i.get('folder') == 'tv'][:60]
    
    # Identify Anime (heuristic)
    anime = [i for i in index if any(g in str(i.get('genres', [])) for g in ['أنمي', 'رسوم متحركة', 'Anime', 'Animation'])][:30]
    
    # Build sections
    def section(sid, title, items, card_fn=card_html):
        if not items:
            return ''
        cards = '\n'.join(card_fn(i) for i in items)
        return f'''
<section class="section" id="{sid}">
  <h2 class="section-title">{title}</h2>
  <div class="grid">
{cards}
  </div>
</section>'''

    movies_section = section('movies', 'أحدث الأفلام — Newest Movies', movies)
    series_section = section('series', 'أحدث المسلسلات — Newest Series', series)
    anime_section = section('anime', 'أنمي مترجم — Anime', anime)

    trends = load_trending()
    carousel_section = build_carousel(trends)

    total = len(movies) + len(series) + len(anime)

    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-PRCQVS90BX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());

    gtag('config', 'G-PRCQVS90BX');
  </script>
  <title>TOMITO — مشاهدة وتحميل أفلام ومسلسلات وأنمي اون لاين 2026 HD مجاناً</title>
  <meta name="description" content="شاهد وحمل أحدث الأفلام والمسلسلات والأنمي 2024-2026 اون لاين بجودة عالية HD مجاناً. مسلسلات رمضان 2026 حصرياً على TOMITO بدون اعلانات.">
  <meta name="keywords" content="مشاهدة افلام اون لاين, تحميل مسلسلات, أنمي مترجم, مسلسلات رمضان 2026, افلام 2026, HD, مجاني, بدون اعلانات, TOMITO, nordrama.live, watch movies online, download series, anime 2026">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta property="og:type" content="website">
  <meta property="og:title" content="TOMITO — أفلام ومسلسلات وأنمي اون لاين 2026">
  <meta property="og:description" content="شاهد أحدث الأفلام والمسلسلات ومسلسلات رمضان 2026 حصرياً بجودة HD.">
  <meta property="og:site_name" content="TOMITO">
  <meta property="og:url" content="{SITE_URL}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="{SITE_URL}">
  <link rel="stylesheet" href="/style.css">
  <link rel="icon" href="/favicon.ico">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "TOMITO",
    "url": "{SITE_URL}",
    "description": "مشاهدة وتحميل أفلام ومسلسلات وأنمي اون لاين بجودة عالية HD 2026",
    "inLanguage": "ar",
    "potentialAction": {{
      "@type": "SearchAction",
      "target": "{SITE_URL}/?q={{search_term_string}}",
      "query-input": "required name=search_term_string"
    }}
  }}
  </script>
</head>
<body>

  <header class="header">
    <a class="logo" href="/">TOMITO</a>
    <ul class="nav">
      <li><a href="/">الرئيسية</a></li>
      <li><a href="/#movies">أفلام</a></li>
      <li><a href="/#series">مسلسلات</a></li>
    </ul>
    <a class="header-btn" href="https://tomito.xyz">الموقع الرسمي</a>
  </header>

  <section class="filters-section">
    <div class="filter-container">
      <div class="filter-item">
        <label>التصنيف</label>
        <div class="custom-select">
          <select id="category-select" onchange="filterCategory(this.value)">
            <option value="all">كل التصنيفات</option>
            <option value="movies">أفلام</option>
            <option value="series">مسلسلات</option>
            <option value="anime">أنمي</option>
          </select>
        </div>
      </div>
      <div class="filter-item">
        <label>الترتيب</label>
        <div class="custom-select">
          <select id="sort-select">
            <option value="popular">الأكثر مشاهدة</option>
            <option value="newest">الأحدث أولاً</option>
            <option value="rating">الأعلى تقييماً</option>
          </select>
        </div>
      </div>
    </div>
  </section>

  <!-- DYNAMIC CONTENT -->
{carousel_section}
{movies_section}
{series_section}
{anime_section}

  <footer class="footer">
    <p>© 2026 <a href="/">TOMITO</a> — جميع الحقوق محفوظة | مشاهدة افلام ومسلسلات اون لاين HD مجاناً</p>
  </footer>

  <script>
  function filterCategory(val) {{
    document.querySelectorAll('.section').forEach(s => {{
      if (val === 'all') {{ s.style.display = ''; }}
      else {{ s.style.display = s.id === val ? '' : 'none'; }}
    }});
  }}
  </script>
</body>
</html>'''

    out_path = os.path.join(BASE_PATH, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Built index.html with {total} cards ({len(movies)} movies, {len(series)} series, {len(anime)} anime)")
    
    # We pass the same HTML structure but without injecting the content sections to trending
    raw_wrapper = html.replace(carousel_section, '').replace(movies_section, '{movies_section}').replace(series_section, '{series_section}').replace(anime_section, '{anime_section}')
    build_trending_page(trends, raw_wrapper)

if __name__ == '__main__':
    build()
