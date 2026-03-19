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
    search_query = title.replace('مسلسل ', '').replace('برنامج ', '').replace('فيلم ', '').replace('كامل ', '').replace('مترجم ', '').strip()
    search_query = re.sub(r'\s+الحلقة\s+\d+.*', '', search_query)
    search_query = re.sub(r'\s+202\d', '', search_query)
    search_query = re.sub(r'\s+الموسم\s+.*', '', search_query)
    search_query = re.sub(r'\s+-\s+.*', '', search_query) # remove suffixes after dash
    search_query = search_query.strip()
    
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

def extract_episode_number(title):
    match = re.search(r'الحلقة\s+(\d+)', title)
    return match.group(1) if match else "1"

def clean_slug(title):
    # Remove prefix words
    cleaned = title.replace('مسلسل ', '').replace('برنامج ', '').replace('فيلم ', '').strip()
    # Remove years like 2026, 2025, 2024
    cleaned = re.sub(r'\s*202\d\s*', ' ', cleaned).strip()
    # Create slug
    slug = cleaned.replace(' ', '-').replace('/', '-').lower()
    slug = re.sub(r'-+', '-', slug)
    # Filter alphanum, dashes and non-ascii (for Arabic support)
    return "".join([c for c in slug if (ord(c) > 127) or c.isalnum() or c == '-'])

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
             if any(x in link for x in ['/tv/', '/movie/', '/series/', '/episode/', '/ramadan/', '/ramadan-trailer/', '/watch-ramadan/']):
                 return f'href="{watch_url}"'
             if link == 'https://www.tomito.xyz': return f'href="{watch_url}"'
        if any(x in link for x in ['shhid4u', 'shahhed', 'shhaheid', 'shaaheid']): return f'href="{watch_url}"'
        return m.group(0)
    
    html = re.sub(btn_pattern, btn_repl, html)

    if item_type == 'series' and episodes:
        # Premium Glassmorphism UI for Episodes
        style = """
<style>
    .episodes-section { margin-top: 50px; padding: 20px; border-top: 1px solid rgba(255,255,255,0.1); }
    .section-title { font-size: 2em; margin-bottom: 30px; color: #fff; text-align: center; font-weight: 700; letter-spacing: 1px; }
    .episodes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
    .episode-card {
        display: flex; align-items: center; gap: 20px; padding: 20px;
        background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px;
        text-decoration: none; color: #fff; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .episode-card:hover {
        background: rgba(255, 255, 255, 0.1); border-color: #e50914;
        transform: translateY(-5px) scale(1.02); box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }
    .ep-number {
        font-size: 1.5em; font-weight: 900; color: #e50914; min-width: 40px; text-align: center;
        text-shadow: 0 0 10px rgba(229, 9, 20, 0.3);
    }
    .ep-info { display: flex; flex-direction: column; }
    .ep-title { font-size: 1.1em; font-weight: 600; line-height: 1.4; color: #eee; }
    .ep-action { font-size: 0.8em; color: #aaa; margin-top: 5px; }
</style>
"""
        ep_list_html = style + '<div class="episodes-section">\n    <h2 class="section-title">الحلقات المتاحة</h2>\n    <div class="episodes-grid">\n'
        for i, ep in enumerate(episodes):
            ep_url = ep.get('watch_url', '#')
            ep_list_html += f"""
        <a href="{ep_url}" class="episode-card" target="_blank">
          <div class="ep-number">{i+1}</div>
          <div class="ep-info">
            <div class="ep-title">{ep['title']}</div>
            <div class="ep-action">مشاهدة الآن على Tomito</div>
          </div>
        </a>"""
        ep_list_html += '\n    </div>\n  </div>'
        
        # JavaScript for dynamic episode handling
        js_code = """
<script>
    const urlParams = new URLSearchParams(window.location.search);
    const epNum = urlParams.get('episode');
    if (epNum) {
        const episodes = """ + json.dumps({extract_episode_number(e['title']): e['watch_url'] for e in episodes}, ensure_ascii=False) + """;
        const selectedUrl = episodes[epNum];
        if (selectedUrl) {
            document.querySelectorAll('a[href*="tomito.xyz"]').forEach(link => {
                if (link.classList.contains('btn-primary') || link.classList.contains('btn-secondary')) {
                    link.href = selectedUrl;
                }
            });
            const titleEl = document.querySelector('.series-title span');
            if (titleEl && !titleEl.textContent.includes('الحلقة')) {
                titleEl.textContent += ' - الحلقة ' + epNum;
            }
        }
    }
</script>
"""
        html = html.replace('</body>', f'{ep_list_html}\n{js_code}\n</body>')

    return html

def main():
    template_path = 'movies/24.html'
    if not os.path.exists(template_path): return
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    json_files = ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json']
    series_map = {}
    poster_cache = {}
    all_std_items = []

    for jf in json_files:
        data = load_json(jf)
        for item in data:
            title = item.get('title', '')
            if not title: continue
            base_title = extract_series_parent(title)
            
            if base_title not in poster_cache:
                print(f"Searching TMDB for: {base_title}")
                tmdb_poster = search_tmdb_poster(base_title)
                json_poster = item.get('poster', '')
                if json_poster and 'image.tmdb.org' in json_poster:
                    json_poster = json_poster.replace('/w500/', '/original/').replace('/w342/', '/original/')
                poster_cache[base_title] = tmdb_poster or json_poster
                time.sleep(0.05)
            elif not poster_cache[base_title]:
                json_poster = item.get('poster', '')
                if json_poster:
                    if 'image.tmdb.org' in json_poster:
                        json_poster = json_poster.replace('/w500/', '/original/').replace('/w342/', '/original/')
                    poster_cache[base_title] = json_poster
            
            item_type = item.get('type', 'series')
            if item_type == 'episode':
                if base_title not in series_map:
                    series_map[base_title] = {'parent': None, 'episodes_dict': {}}
                t_key = title.strip()
                if t_key not in series_map[base_title]['episodes_dict'] and poster_cache[base_title]:
                    series_map[base_title]['episodes_dict'][t_key] = item
            elif item_type == 'series':
                if title not in series_map:
                    series_map[title] = {'parent': None, 'episodes_dict': {}}
                series_map[title]['parent'] = item
            elif item_type == 'movie':
                item_slug = clean_slug(title)
                std_item = {
                    'title': title, 'orig_title': title, 'poster': poster_cache.get(title, item.get('poster', '')),
                    'desc': item.get('description', ''), 'year': '2026', 'rating': '⭐ حصري',
                    'type': 'movie', 'watch_url': f"https://tomito.xyz/movies/{item_slug}", 'source': 'json'
                }
                if std_item['poster']: all_std_items.append(std_item)

    processed_titles = set()
    cards_html = ""
    new_urls = []
    
    os.makedirs('ramadan-trailer', exist_ok=True)
    os.makedirs('movies', exist_ok=True)
    os.makedirs('watch', exist_ok=True)
    
    # Process Series (Trailer Landing Pages)
    for title, info in series_map.items():
        episodes_list = list(info['episodes_dict'].values())
        if not info['parent'] and episodes_list:
            info['parent'] = {
                'title': title, 'orig_title': title, 'poster': poster_cache.get(title, ""),
                'desc': episodes_list[0].get('description', ""), 'year': '2026', 'rating': '⭐ حصري',
                'type': 'series', 'source': 'json'
            }
        
        parent = info['parent']
        if not parent or not parent.get('poster'): continue
        
        series_slug = clean_slug(title)
        parent['watch_url'] = f"https://tomito.xyz/ramadan-trailer/{series_slug}" # Placeholder, actual clicks on card go to trailer page
        
        # Prepare episode links for the series trailer page
        eps_for_rendering = []
        for ep in episodes_list:
            ep_num = extract_episode_number(ep['title'])
            ep_slug = f"{series_slug}-ep-{ep_num}"
            eps_for_rendering.append({
                'title': ep['title'],
                'watch_url': f"https://nordrama.live/watch/{ep_slug}" # Local page before tomito
            })
            
            # Generate Individual Episode (Trailer) Page in /watch/
            ep_std = {
                'title': ep['title'], 'orig_title': ep['title'], 'poster': parent['poster'],
                'desc': ep.get('description', parent.get('desc', parent.get('description', ''))), 'year': '2026', 'rating': '⭐ حصري',
                'type': 'episode', 'watch_url': f"https://tomito.xyz/watch-ramadan/{series_slug}?episode={ep_num}",
                'source': 'json'
            }
            html = generate_html(ep_std, template_content)
            with open(os.path.join('watch', f"{ep_slug}.html"), 'w', encoding='utf-8') as f:
                f.write(html)
            new_urls.append(f"https://nordrama.live/watch/{ep_slug}")
            
        # Generate Series (Trailer) Landing Page
        html = generate_html(parent, template_content, episodes=eps_for_rendering)
        with open(os.path.join('ramadan-trailer', f"{series_slug}.html"), 'w', encoding='utf-8') as f:
            f.write(html)
        new_urls.append(f"https://nordrama.live/ramadan-trailer/{series_slug}")
        
        # Add to index cards
        cards_html += f"""
    <a class="card" href="ramadan-trailer/{series_slug}">
      <img class="card-poster" src="{parent['poster']}" alt="{title}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">حصري</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{title}</div></div></div>
    </a>"""

    # Process Movies & TMDB items
    for item in all_std_items:
        slug = clean_slug(item['title'])
        folder = 'movies' if item['type'] == 'movie' else 'tv'
        os.makedirs(folder, exist_ok=True)
        html = generate_html(item, template_content)
        with open(os.path.join(folder, f"{slug}.html"), 'w', encoding='utf-8') as f:
            f.write(html)
        new_urls.append(f"https://nordrama.live/{folder}/{slug}")
        
        cards_html += f"""
    <a class="card" href="{folder}/{slug}">
      <img class="card-poster" src="{item['poster']}" alt="{item['title']}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">{'فيلم' if item['type'] == 'movie' else 'مسلسل'}</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item['title']}</div></div></div>
    </a>"""

    # Update index.html
    index_path = 'index.html'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
        pattern = re.compile(re.escape('<div class="grid" id="all">') + r'.*?</div>\s*</section>', re.DOTALL)
        replacement = '<div class="grid" id="all">' + cards_html + "\n  </div>\n</section>"
        if pattern.search(index_content):
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(pattern.sub(replacement, index_content))

    # Update sitemap
    sitemap_path = 'sitemap.xml'
    existing_urls = set()
    if os.path.exists(sitemap_path):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            for loc in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                if loc.text: existing_urls.add(loc.text.replace('.html', ''))
        except Exception: pass
    
    for url in new_urls: existing_urls.add(url.replace('.html', ''))
    
    # Update sitemap
    sitemap_path = 'sitemap.xml'
    existing_urls = set()
    if os.path.exists(sitemap_path):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            for loc in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                if loc is not None and loc.text:
                    existing_urls.add(loc.text.replace('.html', ''))
        except Exception: pass
    
    for url in new_urls:
        existing_urls.add(url.replace('.html', ''))
    
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in sorted(list(existing_urls)):
            f.write(f'  <url><loc>{url}</loc><priority>0.8</priority></url>\n')
        f.write('</urlset>')

if __name__ == '__main__':
    main()
