import json
import os
import urllib.parse
import requests
import re
import time

TMDB_API_KEY = '882e741f7283dc9ba1654d4692ec30f6'
BASE_URL = 'https://api.themoviedb.org/3'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'
DATA_DIR = 'data'
CACHE_FILE = 'poster_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def clean_title_junk(text):
    if not text: return ""
    # Normalize Alif early for consistent matching
    res = re.sub(r'[أإآ]', 'ا', text)
    junk = [
        '- فاصل اعلاني', 'فاصل اعلاني', '- فاصل-اعلاني', 'فاصل-اعلاني',
        'مشاهدة وتحميل', 'مترجم اون لاين', 'بجودة عالية', 'كامل مترجم',
        'فيلم', 'مسلسل', 'انمي', 'برنامج', 'اعلان', 'حصرية', 'حصري'
    ]
    for j in junk:
        res = res.replace(j, '')
    res = re.sub(r'[\(\[].*?[\)\]]', '', res)
    # Strip everything starting from Season/Episode keywords
    res = re.sub(r'\s+(الموسم|الحلقة|Season|Episode).*', '', res, flags=re.I)
    # Strip trailing digits (likely season numbers) unless it's a 4-digit year like 2026
    res = re.sub(r'\s+(?!\d{4}$)\d+$', '', res)
    return res.strip().replace('  ', ' ')

def clean_search_query(text):
    # Strip seasonal/episode info then replace hyphen/junk with space
    res = clean_title_junk(text)
    res = res.replace('-', ' ').replace('_', ' ')
    # User said "Moon Knight الموسم الاول" = no, "Moon Knight" = yes
    # Also "dire space blasete0 -"
    res = re.sub(r'[^a-z0-9\u0600-\u06FF\s]', ' ', res.lower())
    return re.sub(r'\s+', ' ', res).strip()

def clean_slug(text, strip_all=True):
    if not text: return ""
    if strip_all:
        res = clean_title_junk(text)
    else:
        # Keep seasonal/episode info for unique watch pages but clean junk
        res = re.sub(r'[أإآ]', 'ا', text)
        junk = ['- فاصل اعلاني', 'فاصل اعلاني', '- فاصل-اعلاني', 'فاصل-اعلاني', 'مشاهدة وتحميل', 'مترجم اون لاين', 'بجودة عالية', 'كامل مترجم', 'فيلم', 'مسلسل', 'انمي', 'برنامج', 'اعلان', 'حصرية', 'حصري']
        for j in junk: res = res.replace(j, '')
        res = re.sub(r'[\(\[].*?[\)\]]', '', res)
    
    res = res.replace(' ', '-').lower()
    res = re.sub(r'[^\w\-]', '', res)
    res = re.sub(r'-+', '-', res).strip('-')
    return res

def load_json(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return []

def search_tmdb_info(title, cache):
    search_query = clean_search_query(title)
    if not search_query or search_query.isdigit(): return None
    if search_query in cache:
        res = cache[search_query]
        if isinstance(res, dict) and res.get('id'):
            return res
        # If it's a string or dict without ID, we re-fetch to get the ID
    
    params = {'api_key': TMDB_API_KEY, 'language': 'ar', 'query': search_query}
    url = f"{BASE_URL}/search/multi"
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                for res in results:
                    if res.get('poster_path'):
                         info = {
                             'poster': f"{IMAGE_BASE_URL}{res.get('poster_path')}",
                             'id': res.get('id'),
                             'type': res.get('media_type', 'tv'),
                             'orig_title': res.get('title') or res.get('name')
                         }
                         cache[search_query] = info
                         return info
        cache[search_query] = None
        return None
    except Exception:
        return None

def generate_html(std_item, template_content, episodes=None):
    title = clean_title_junk(std_item.get('title', ''))
    display_title = std_item.get('title', '')
    original_title = std_item.get('orig_title', '')
    poster = std_item.get('poster', '')
    description = std_item.get('desc', '') or "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    year = std_item.get('year', '2026')
    
    # Construct optimal watch URL
    match_ep = re.search(r'الحلقة\s+(\d+)', display_title)
    match_se = re.search(r'الموسم\s+(\d+)', display_title)
    ep_n = match_ep.group(1) if match_ep else "1"
    se_n = match_se.group(1) if match_se else "1"
    
    # Check if we are generating a "watch" page (usually individual episodes)
    is_watch_page = "الحلقة" in display_title or "الموسم" in display_title
    
    # User wants watch-ramadan format for ALL Arabic series/Ramadan shows
    if is_watch_page and (std_item.get('label') == "رمضان" or std_item.get('category') == 'series'):
        # Ensure spaces are replaced with hyphens for the watch-ramadan path
        bt = clean_title_junk(display_title).replace(' ', '-')
        watch_url = f"https://tomito.xyz/watch-ramadan/{urllib.parse.quote(bt)}?episode={ep_n}"
    elif is_watch_page and std_item.get('type') == 'movie' and std_item.get('tmdb_id'):
        # React routing: /watch/movie/:id
        watch_url = f"https://tomito.xyz/watch/movie/{std_item['tmdb_id']}"
    elif is_watch_page and std_item.get('tmdb_id') and std_item.get('type') == 'tv':
        # React routing: /watch/tv/:id?season=S&episode=E
        watch_url = f"https://tomito.xyz/watch/tv/{std_item['tmdb_id']}?season={se_n}&episode={ep_n}"
    else:
        # Default search query fallback
        sq = clean_search_query(display_title)
        watch_url = f"https://www.tomito.xyz/search?q={urllib.parse.quote(sq)}"
    
    seo_title = f"{display_title} — مشاهدة 2026 فابور مجاناً على تومتو"
    
    html = template_content
    html = html.replace('24 / 24 | TOMITO MOVIES', seo_title)
    html = html.replace('<title>24 (2001) | Watch online on TOMITO</title>', f'<title>{seo_title}</title>')
    html = html.replace('مسلسل 24 (2001)', f'{display_title} ({year})')
    html = html.replace('<span>24</span>', f'<span>{display_title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{original_title}</span>')
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster)
    
    desc_escaped = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    template_desc = 'Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season.'
    html = html.replace(template_desc, desc_escaped)
    
    btn_pattern = r'href="(https?://[^"]*?)"'
    def btn_repl(m):
        link = m.group(1)
        if any(x in link for x in ['nordrama.live', 'tomito.xyz', 'shhaheid', 'shaaheid', 'shhid4u']):
            if any(x in link for x in ['/index', '/style.css', 'favicon.ico']): return m.group(0)
            return f'href="{watch_url}"'
        return m.group(0)
    
    html = re.sub(btn_pattern, btn_repl, html)
    html = html.replace('.html"', '"').replace('.html#', '#')

    if episodes:
        # Professional episode grid layout
        ep_list_html = '<div class="episodes-section" style="width: 100%; max-width: 1200px; margin: 20px auto; padding: 0 20px;">\n    <h2 class="section-title">الحلقات المتاحة</h2>\n    <div class="episodes-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px;">\n'
        for ep in episodes:
            et = ep['title']
            # Determine suitable link for this episode (direct watch-ramadan or search)
            match_ep_local = re.search(r'الحلقة\s+(\d+)', et)
            ep_n_local = match_ep_local.group(1) if match_ep_local else "1"
            
            # Use same logic as watch_url but specific for this episode
            if std_item.get('label') == "رمضان" or std_item.get('category') == 'series':
                bt_local = clean_title_junk(et).replace(' ', '-')
                ep_link = f"https://tomito.xyz/watch-ramadan/{urllib.parse.quote(bt_local)}?episode={ep_n_local}"
            else:
                sq_local = clean_search_query(et)
                ep_link = f"https://www.tomito.xyz/search?q={urllib.parse.quote(sq_local)}"
            
            # Extract episode number if possible
            ep_num = ep_n_local if match_ep_local else "?"
            
            ep_list_html += f"""
        <a href="{ep_link}" class="episode-card" target="_blank" style="text-decoration: none; color: inherit; background: #1a1a1a; padding: 15px; border-radius: 8px; transition: 0.3s; display: flex; align-items: center; border: 1px solid #333;">
          <div class="ep-number" style="background: #e50914; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-left: 15px; flex-shrink: 0;">{ep_num}</div>
          <div class="ep-info">
            <div class="ep-title" style="font-weight: bold; margin-bottom: 5px;">{et}</div>
            <div class="ep-action" style="font-size: 0.85em; color: #e50914;">مشاهدة الآن</div>
          </div>
        </a>"""
        ep_list_html += '\n    </div>\n  </div>'
        html = html.replace('</body>', f'{ep_list_html}\n</body>')

    return html

def main():
    template_path = 'movies/24.html'
    if not os.path.exists(template_path): return
    with open(template_path, 'r', encoding='utf-8') as f: template_content = f.read()

    # Cleanup
    for folder in ['ramadan-trailer', 'movies', 'watch', 'series', 'anime']:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith('.html') and f != '24.html': os.remove(os.path.join(folder, f))
        os.makedirs(folder, exist_ok=True)

    categories = {
        'ramadan': ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json'],
        'movies': ['all_movies1.json'],
        'anime': ['anime.json'],
        'series': ['series.json']
    }
    cat_titles = {'ramadan': 'مسلسلات رمضان 2026', 'movies': 'أفلام حصرية 2026', 'anime': 'أنمي وكرتون 2026', 'series': 'مسلسلات عربية وأجنبية 2026'}

    cache = load_cache()
    processed_urls = set()
    index_sections = {}

    # Initial grouping pass
    series_groups = {} # slug -> {'parent': {}, 'episodes': [], 'cat_id': ''}
    
    for cat_id, files in categories.items():
        for f in files:
            data = load_json(os.path.join(DATA_DIR, f))
            for item in data:
                title = item.get('title', '')
                if not title: continue
                # slug for grouping is ALWAYS stripped
                slug = clean_slug(title, strip_all=True)
                if not slug: continue
                
                if slug not in series_groups:
                    series_groups[slug] = {'parent': item, 'episodes': [], 'cat_id': cat_id}
                
                # Check if it's an episode or season specific
                if 'الحلقة' in title or 'الموسم' in title or 'Season' in title or 'Episode' in title:
                    series_groups[slug]['episodes'].append(item)
                else:
                    # If it's a more generic entry, use it as the parent reference
                    current_parent_title = series_groups[slug]['parent'].get('title', '')
                    if 'الحلقة' in current_parent_title or 'الموسم' in current_parent_title:
                        series_groups[slug]['parent'] = item

    # Generation pass
    for slug, group in series_groups.items():
        cat_id = group['cat_id']
        parent = group['parent']
        eps = sorted(group['episodes'], key=lambda x: x.get('title', ''))
        
        info = search_tmdb_info(parent['title'], cache)
        poster = info.get('poster') if info else parent.get('poster')
        if not poster: poster = "https://www.tomito.xyz/favicon.ico"
        
        folder = 'ramadan-trailer' if cat_id == 'ramadan' else cat_id
        
        # 1. Generate Parent Page (Series Overview/Trailer)
        page_path = os.path.join(folder, f"{slug}.html")
        
        std_item = {
            'title': parent['title'], 
            'orig_title': info.get('orig_title', '') if info else '', 
            'poster': poster, 
            'desc': parent.get('description', ''), 
            'year': '2026',
            'tmdb_id': info.get('id') if info else None,
            'type': info.get('type', 'tv') if info else 'tv',
            'label': "رمضان" if cat_id == 'ramadan' else "",
            'category': cat_id
        }
        
        if not os.path.exists(page_path):
            html = generate_html(std_item, template_content, episodes=eps if eps else None)
            with open(page_path, 'w', encoding='utf-8') as pf: pf.write(html)
        
        href = f"{folder}/{slug}"
        if cat_id not in index_sections: index_sections[cat_id] = []
        index_sections[cat_id].append({'title': clean_title_junk(parent['title']), 'poster': poster, 'href': href, 'label': "حصري" if cat_id == 'ramadan' else ("فيلم" if cat_id == 'movies' else "مسلسل")})
        processed_urls.add(f"https://tomito.xyz/{href}")
        
        # 2. Generate Episode Pages (Optional, in watch/)
        for ep in group['episodes']:
            ep_slug = clean_slug(ep['title'], strip_all=False)
            if ep_slug == slug: continue # Avoid overwriting parent if names match exactly
            
            ep_path = os.path.join('watch', f"{ep_slug}.html")
            ep_std = {
                'title': ep['title'], 
                'orig_title': info.get('orig_title', '') if info else '', 
                'poster': poster, 
                'desc': ep.get('description', ''), 
                'year': '2026',
                'tmdb_id': info.get('id') if info else None,
                'type': info.get('type', 'tv') if info else 'tv',
                'label': "رمضان" if cat_id == 'ramadan' else "",
                'category': cat_id
            }
            ep_html = generate_html(ep_std, template_content)
            with open(ep_path, 'w', encoding='utf-8') as pf: pf.write(ep_html)
            processed_urls.add(f"https://tomito.xyz/watch/{ep_slug}")

    # Update index.html
    sections_html = ""
    for cat_id, items in index_sections.items():
        sections_html += f'\n<section class="section" id="{cat_id}">\n  <h2 class="section-title">{cat_titles[cat_id]}</h2>\n  <div class="grid">\n'
        for item in items:
            sections_html += f'\n    <a class="card" href="{item["href"]}">\n      <img class="card-poster" src="{item["poster"]}" alt="{item["title"]}" loading="lazy">\n      <div class="card-overlay"><div class="card-meta">{item["label"]}</div></div>\n      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item["title"]}</div></div></div>\n    </a>'
        sections_html += "\n  </div>\n</section>"

    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f: content = f.read()
        start_tag, end_tag = '<!-- DYNAMIC_CONTENT_START -->', '<!-- DYNAMIC_CONTENT_END -->'
        pattern = re.compile(re.escape(start_tag) + r'.*?' + re.escape(end_tag), re.DOTALL)
        if pattern.search(content):
            new_content = pattern.sub(f"{start_tag}\n{sections_html}\n{end_tag}", content)
            new_content = new_content.replace('.html"', '"').replace('.html#', '#')
            with open('index.html', 'w', encoding='utf-8') as f: f.write(new_content)

    # Sitemap
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write('  <url><loc>https://tomito.xyz/</loc><priority>1.0</priority></url>\n')
        for url in sorted(list(processed_urls)): f.write(f'  <url><loc>{url}</loc><priority>0.8</priority></url>\n')
        f.write('</urlset>')

    save_cache(cache)
    print("Success!")

if __name__ == '__main__':
    main()
