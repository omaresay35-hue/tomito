import json
import os
import urllib.parse
import requests
import re
import time

TMDB_API_KEY = '882e741f7283dc9ba1654d4692ec30f6'
BASE_URL = 'https://api.themoviedb.org/3'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_tmdb_data(endpoint, params=None):
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    params['language'] = 'ar'
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            return []
    except Exception:
        return []

def search_tmdb_poster(title):
    search_query = title.replace('مسلسل ', '').replace('برنامج ', '').replace('فيلم ', '').strip()
    search_query = re.sub(r'\s+الحلقة\s+\d+.*', '', search_query)
    search_query = re.sub(r'2026', '', search_query).strip()
    
    params = {'api_key': TMDB_API_KEY, 'language': 'ar', 'query': search_query}
    url = f"{BASE_URL}/search/multi"
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                for res in results:
                    if res.get('poster_path'):
                        return f"{IMAGE_BASE_URL}{res.get('poster_path')}"
        return None
    except Exception:
        return None

def extract_series_parent(title):
    pattern = r'(.*?)\s+الحلقة\s+\d+.*'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return title

def clean_ramadan_slug(title):
    cleaned = title.replace('مسلسل ', '').replace('برنامج ', '').strip()
    slug = cleaned.replace(' ', '-').replace('/', '-').lower()
    return "".join([c for c in slug if c.isalnum() or c == '-'])

def generate_html(std_item, template_content, episodes=None):
    title = std_item.get('title', '')
    original_title = std_item.get('orig_title', '')
    poster = std_item.get('poster', '')
    description = std_item.get('desc', '') or "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    year = std_item.get('year', '2026')
    rating = std_item.get('rating', '⭐ 7.8')
    item_type = std_item.get('type', 'series')
    watch_url = std_item.get('watch_url', 'https://www.tomito.xyz')
    
    html = template_content
    html = html.replace('24 / 24 | TOMITO MOVIES', f'{title} | TOMITO')
    html = html.replace('<title>24 (2001) | Watch online on TOMITO</title>', f'<title>{title} ({year}) | Watch online on TOMITO</title>')
    html = html.replace('مسلسل 24 (2001)', f'{title} ({year})')
    html = html.replace('<span>24</span>', f'<span>{title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{original_title}</span>')
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster)
    
    desc_escaped = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    template_desc = 'Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season.'
    html = html.replace(template_desc, desc_escaped)
    
    html = html.replace('<span class="tag">2001</span>', f'<span class="tag">{year}</span>')
    html = html.replace('<span class="tag">⭐ 7.8</span>', f'<span class="tag">{rating}</span>')
    
    if item_type == 'movie':
        html = html.replace('TV Series | مسلسل', 'Movie | فيلم')
    elif item_type == 'episode':
        html = html.replace('TV Series | مسلسل', 'Episode | حلقة')
    
    html = html.replace('https://tomito.xyz/tv/1973-24', watch_url)
    
    btn_pattern = r'href="(https?://[^"]*?)"'
    def btn_repl(m):
        link = m.group(1)
        if 'tomito.xyz' in link:
             if '/tv/' in link or '/movie/' in link or '/series/' in link or '/episode/' in link or '/ramadan/' in link or '/ramadan-trailer/' in link:
                 return f'href="{watch_url}"'
             if link == 'https://www.tomito.xyz': return f'href="{watch_url}"'
        if 'shhid4u' in link or 'shahhed' in link or 'shhaheid' in link: return f'href="{watch_url}"'
        return m.group(0)
    
    html = re.sub(btn_pattern, btn_repl, html)

    if item_type == 'series' and episodes:
        ep_list_html = '<div class="episodes-section">\n    <h2 class="section-title">الحلقات المتاحة</h2>\n    <div class="grid">\n'
        for i, ep in enumerate(episodes):
            ep_slug = ep['title'].replace(' ', '-').replace('/', '-').lower()
            ep_slug = "".join([c for c in ep_slug if c.isalnum() or c == '-'])
            ep_url = f"../watch/{ep_slug}.html"
            ep_list_html += f"""
        <a href="{ep_url}" class="episode-card" style="display:flex; align-items:center; gap:15px; padding:15px; background:rgba(255,255,255,0.05); border-radius:8px; text-decoration:none; color:#fff; border:1px solid rgba(255,255,255,0.1); transition:all 0.3s;">
          <div class="ep-number" style="font-size:1.2em; font-weight:bold; color:#e50914;">{i+1}</div>
          <div class="ep-info">
            <div class="ep-title">{ep['title']}</div>
          </div>
        </a>"""
        ep_list_html += '\n    </div>\n  </div>'
        html = html.replace('</body>', f'{ep_list_html}\n</body>')

    return html

def create_slug(title):
    slug = title.replace(' ', '-').replace('/', '-').lower()
    return "".join([c for c in slug if c.isalnum() or c == '-'])

def main():
    template_path = 'movies/24.html'
    if not os.path.exists(template_path): return
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    all_std_items = []
    json_files = ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json']
    series_map = {}
    poster_cache = {}

    for jf in json_files:
        data = load_json(jf)
        for item in data:
            title = item.get('title', '')
            if not title: continue
            base_title = extract_series_parent(title)
            
            if base_title not in poster_cache:
                print(f"Searching TMDB for: {base_title}")
                tmdb_poster = search_tmdb_poster(base_title)
                poster_cache[base_title] = tmdb_poster or item.get('poster')
                time.sleep(0.1)
            
            # Clean slug for ramadan-trailer watch links
            item_slug = clean_ramadan_slug(title)
            watch_url = f"https://tomito.xyz/ramadan-trailer/{item_slug}"
            
            std_item = {
                'title': title, 'orig_title': title,
                'poster': poster_cache[base_title], 'desc': item.get('description', ''),
                'year': '2026', 'rating': '⭐ حصري', 'type': item.get('type', 'series'),
                'watch_url': watch_url, 'source': 'json'
            }
            
            if std_item['type'] == 'episode':
                if base_title not in series_map:
                    series_map[base_title] = {'parent': None, 'episodes': []}
                series_map[base_title]['episodes'].append(std_item)
            elif std_item['type'] == 'series':
                if title not in series_map:
                    series_map[title] = {'parent': None, 'episodes': []}
                series_map[title]['parent'] = std_item
            else:
                all_std_items.append(std_item)

    for title, info in series_map.items():
        if not info['parent']:
            item_slug = clean_ramadan_slug(title)
            info['parent'] = {
                'title': title, 'orig_title': title, 'poster': poster_cache.get(title, ""),
                'desc': info['episodes'][0]['desc'] if info['episodes'] else "",
                'year': '2026', 'rating': '⭐ حصري', 'type': 'series', 'source': 'json',
                'watch_url': f"https://tomito.xyz/ramadan-trailer/{item_slug}"
            }
        all_std_items.append(info['parent'])

    categories = [('movie/popular', 'movie'), ('tv/popular', 'series')]
    for endpoint, item_type in categories:
        results = fetch_tmdb_data(endpoint)
        for item in results:
            title = item.get('title') or item.get('name')
            if title in poster_cache: continue
            item_id = item.get('id')
            watch_url = f"https://tomito.xyz/{'movie' if item_type == 'movie' else 'tv'}/{item_id}"
            std_item = {
                'title': title, 'orig_title': item.get('original_title') or item.get('original_name'),
                'poster': f"{IMAGE_BASE_URL}{item.get('poster_path')}" if item.get('poster_path') else "",
                'desc': item.get('overview', ''), 'year': (item.get('release_date') or item.get('first_air_date', '2026')).split('-')[0],
                'rating': f"⭐ {item.get('vote_average', '0.0')}", 'type': item_type,
                'watch_url': watch_url, 'source': 'tmdb'
            }
            all_std_items.append(std_item)

    processed_titles = set()
    cards_html = ""
    new_urls = []
    os.makedirs('series', exist_ok=True); os.makedirs('movies', exist_ok=True); os.makedirs('watch', exist_ok=True)
    
    for item in all_std_items:
        if item['title'] in processed_titles: continue
        processed_titles.add(item['title'])
        slug = create_slug(item['title'])
        if item['type'] == 'series':
            folder = 'series'
            eps = series_map.get(item['title'], {}).get('episodes', [])
            html = generate_html(item, template_content, episodes=eps)
            meta = "حصري" if item['source'] == 'json' else "مسلسل"
            cards_html += f"""
    <a class="card" href="{folder}/{slug}.html">
      <img class="card-poster" src="{item['poster']}" alt="{item['title']}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">{meta}</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item['title']}</div></div></div>
    </a>"""
        elif item['type'] == 'movie':
            folder = 'movies'
            html = generate_html(item, template_content)
            cards_html += f"""
    <a class="card" href="{folder}/{slug}.html">
      <img class="card-poster" src="{item['poster']}" alt="{item['title']}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">فيلم</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item['title']}</div></div></div>
    </a>"""
        else:
            folder = 'watch'
            html = generate_html(item, template_content)
        with open(os.path.join(folder, f"{slug}.html"), 'w', encoding='utf-8') as f:
            f.write(html)
        new_urls.append(f"https://nordrama.live/{folder}/{slug}.html")

    for title, info in series_map.items():
        for ep in info['episodes']:
            slug = create_slug(ep['title'])
            file_path = os.path.join('watch', f"{slug}.html")
            html = generate_html(ep, template_content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            new_urls.append(f"https://nordrama.live/watch/{slug}.html")

    index_path = 'index.html'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
        pattern = re.compile(re.escape('<div class="grid" id="all">') + r'.*?</div>\s*</section>', re.DOTALL)
        replacement = '<div class="grid" id="all">' + cards_html + "\n  </div>\n</section>"
        if pattern.search(index_content):
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(pattern.sub(replacement, index_content))

    sitemap_path = 'sitemap.xml'
    if os.path.exists(sitemap_path):
        with open(sitemap_path, 'r', encoding='utf-8') as f:
            sm_content = f.read().strip()
            if sm_content.endswith('</urlset>'): sm_content = sm_content[:-9]
            for url in set(new_urls):
                if f"<loc>{url}</loc>" not in sm_content:
                    sm_content += f"  <url><loc>{url}</loc><priority>0.8</priority></url>\n"
            with open(sitemap_path, 'w', encoding='utf-8') as f:
                f.write(sm_content + '</urlset>')

if __name__ == '__main__':
    main()
