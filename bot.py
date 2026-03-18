import json
import os
import urllib.parse
import requests
import re

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
        # For simplicity, we only fetch 1 page.
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            print(f"Error fetching from {url}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception fetching from {url}: {e}")
        return []

def extract_series_parent(title):
    # Regex for "الحلقة X" or "الحلقة X و Y"
    pattern = r'(.*?)\s+الحلقة\s+\d+.*'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return title

def generate_html(std_item, template_content, episodes=None):
    title = std_item.get('title', '')
    original_title = std_item.get('orig_title', '')
    poster = std_item.get('poster', '')
    description = std_item.get('desc', '') or "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    year = std_item.get('year', '2026')
    rating = std_item.get('rating', '⭐ 7.8')
    item_type = std_item.get('type', 'series')
    watch_url = std_item.get('watch_url', '')
    
    html = template_content
    # Replace metadata
    html = html.replace('24 / 24 | TOMITO MOVIES', f'{title} | TOMITO')
    html = html.replace('<title>24 (2001) | Watch online on TOMITO</title>', f'<title>{title} ({year}) | Watch online on TOMITO</title>')
    
    # Body replacements
    html = html.replace('مسلسل 24 (2001)', f'{title} ({year})')
    html = html.replace('<span>24</span>', f'<span>{title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{original_title}</span>')
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster)
    
    # Description
    desc_escaped = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    template_desc = 'Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season.'
    html = html.replace(template_desc, desc_escaped)
    
    # Tags
    html = html.replace('<span class="tag">2001</span>', f'<span class="tag">{year}</span>')
    html = html.replace('<span class="tag">⭐ 7.8</span>', f'<span class="tag">{rating}</span>')
    
    if item_type == 'movie':
        html = html.replace('TV Series | مسلسل', 'Movie | فيلم')
    elif item_type == 'episode':
        html = html.replace('TV Series | مسلسل', 'Episode | حلقة')
    
    # Link
    html = html.replace('https://tomito.xyz/tv/1973-24', watch_url)

    # Episodes Grid (for series pages)
    episodes_html = ""
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
        
        # Inject before footer/last script or bottom of main
        html = html.replace('</body>', f'{ep_list_html}\n</body>')

    return html

def create_slug(title):
    slug = title.replace(' ', '-').replace('/', '-').lower()
    return "".join([c for c in slug if c.isalnum() or c == '-'])

def main():
    template_path = 'movies/24.html'
    if not os.path.exists(template_path):
        print(f"Template {template_path} not found.")
        return
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    all_std_items = []
    json_files = ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json']
    
    # Grouping
    series_map = {} # title -> {'parent': std_item, 'episodes': []}
    
    # 1. Load from JSON
    for jf in json_files:
        data = load_json(jf)
        for item in data:
            title = item.get('title', '')
            if not title: continue
            
            std_item = {
                'title': title,
                'orig_title': title,
                'poster': item.get('poster', ''),
                'desc': item.get('description', ''),
                'year': '2026',
                'rating': '⭐ حصري',
                'type': item.get('type', 'series'),
                'watch_url': item.get('url', ''),
                'source': 'json'
            }
            
            if std_item['type'] == 'episode':
                parent_title = extract_series_parent(title)
                if parent_title not in series_map:
                    series_map[parent_title] = {'parent': None, 'episodes': []}
                series_map[parent_title]['episodes'].append(std_item)
            elif std_item['type'] == 'series':
                if title not in series_map:
                    series_map[title] = {'parent': None, 'episodes': []}
                series_map[title]['parent'] = std_item
            else:
                all_std_items.append(std_item)

    # Ensure all series in map have a parent (dummy if necessary)
    for title, info in series_map.items():
        if not info['parent']:
            info['parent'] = {
                'title': title,
                'orig_title': title,
                'poster': info['episodes'][0]['poster'] if info['episodes'] else "",
                'desc': info['episodes'][0]['desc'] if info['episodes'] else "",
                'year': '2026',
                'rating': '⭐ حصري',
                'type': 'series',
                'watch_url': f"https://tomito.xyz/watch-ramadan/{title}",
                'source': 'json'
            }
        all_std_items.append(info['parent'])

    # 2. Add TMDB
    categories = [('movie/popular', 'movie'), ('tv/popular', 'series')]
    for endpoint, item_type in categories:
        results = fetch_tmdb_data(endpoint)
        for item in results:
            title = item.get('title') or item.get('name')
            orig_title = item.get('original_title') or item.get('original_name')
            date = item.get('release_date') or item.get('first_air_date')
            poster_path = item.get('poster_path')
            
            std_item = {
                'title': title,
                'orig_title': orig_title,
                'poster': f"{IMAGE_BASE_URL}{poster_path}" if poster_path else "",
                'desc': item.get('overview', ''),
                'year': date.split('-')[0] if date else "2026",
                'rating': f"⭐ {item.get('vote_average', '0.0')}",
                'type': item_type,
                'watch_url': f"https://tomito.xyz/{'movie' if item_type == 'movie' else 'tv'}/{item.get('id')}",
                'source': 'tmdb'
            }
            all_std_items.append(std_item)

    # Process all to generate pages and cards
    processed_titles = set()
    cards_html = ""
    new_urls = []
    
    os.makedirs('series', exist_ok=True)
    os.makedirs('movies', exist_ok=True)
    os.makedirs('watch', exist_ok=True)
    
    for item in all_std_items:
        if item['title'] in processed_titles: continue
        processed_titles.add(item['title'])
        
        slug = create_slug(item['title'])
        if item['type'] == 'series':
            folder = 'series'
            eps = series_map.get(item['title'], {}).get('episodes', [])
            html = generate_html(item, template_content, episodes=eps)
            # Home page card (only series/movies)
            meta = "حصري" if item['source'] == 'json' else "مسلسل"
            card = f"""
    <a class="card" href="{folder}/{slug}.html">
      <img class="card-poster" src="{item['poster']}" alt="{item['title']}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">{meta}</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item['title']}</div></div></div>
    </a>"""
            cards_html += card
        elif item['type'] == 'movie':
            folder = 'movies'
            html = generate_html(item, template_content)
            card = f"""
    <a class="card" href="{folder}/{slug}.html">
      <img class="card-poster" src="{item['poster']}" alt="{item['title']}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">فيلم</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{item['title']}</div></div></div>
    </a>"""
            cards_html += card
        else: # individual episode or other
            folder = 'watch'
            html = generate_html(item, template_content)
            # Not adding individual episodes to home page grid
            
        file_path = os.path.join(folder, f"{slug}.html")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        loc_url = f"https://nordrama.live/{folder}/{slug}.html"
        new_urls.append(loc_url)

    # 3. Handle generated episodes in watch/
    for title, info in series_map.items():
        for ep in info['episodes']:
            slug = create_slug(ep['title'])
            file_path = os.path.join('watch', f"{slug}.html")
            if not os.path.exists(file_path): # already generated if in all_std_items
                html = generate_html(ep, template_content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                loc_url = f"https://nordrama.live/watch/{slug}.html"
                new_urls.append(loc_url)

    # Update index.html
    index_path = 'index.html'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
        start_marker = '<div class="grid" id="all">'
        pattern = re.compile(re.escape(start_marker) + r'.*?</div>\s*</section>', re.DOTALL)
        replacement = start_marker + cards_html + "\n  </div>\n</section>"
        if pattern.search(index_content):
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(pattern.sub(replacement, index_content))

    # Update sitemap
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
