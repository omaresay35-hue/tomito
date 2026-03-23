import json
import os
import urllib.parse
import requests
import re
import time

TMDB_API_KEY = '882e741f7283dc9ba1654d4692ec30f6'
BASE_URL = 'https://api.themoviedb.org/3'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'

def clean_slug(text):
    if not text: return ""
    # Remove Arabic prefixes
    res = text.replace('مسلسل ', '').replace('برنامج ', '').replace('انمي ', '').replace('فيلم ', '').replace('كامل ', '').replace('مترجم ', '').strip()
    # Normalize spaces and characters
    res = res.replace(' ', '-').lower()
    res = re.sub(r'[^a-z0-9\-]', '', res)
    res = re.sub(r'-+', '-', res).strip('-')
    return res

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

def search_tmdb_info(title):
    # Trust the title from extract_series_parent, but do minimal cleanup
    search_query = title.strip()
    if not search_query or search_query.isdigit(): return None
    
    params = {'api_key': TMDB_API_KEY, 'language': 'ar', 'query': search_query}
    url = f"{BASE_URL}/search/multi"
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                # Filter results that have a poster and prefer them
                for res in results:
                    if res.get('poster_path'):
                         # If we found a result with a poster for our specific query, trust it
                         return {
                             'poster': f"{IMAGE_BASE_URL}{res.get('poster_path')}",
                             'id': res.get('id'),
                             'type': res.get('media_type', 'tv')
                         }
        return None
    except Exception as e:
        print(f"Error searching TMDB for {search_query}: {e}")
        return None

def extract_series_parent(title):
    # Remove common prefixes/suffixes
    cleaned = title.replace('مسلسل', '').replace('برنامج', '').replace('انمي', '').replace('فيلم', '').strip()
    
    # Special case: if there's bracketed content, it often IS the title (like [Oshi no Ko])
    bracket_match = re.search(r'\[(.*?)\]', cleaned)
    if bracket_match:
        cand = bracket_match.group(1).strip()
        if len(cand) > 2:
            return cand

    # Remove Season/Part/Episode markers (English & Arabic)
    cleaned = re.sub(r'(?i)\d+(st|nd|rd|th)?\s+Season', '', cleaned)
    cleaned = re.sub(r'(?i)Season\s+\d+', '', cleaned)
    cleaned = re.sub(r'الموسم\s+\d+.*', '', cleaned)
    cleaned = re.sub(r'الجزء\s+\d+.*', '', cleaned)
    cleaned = re.sub(r'الحلقة\s+\d+.*', '', cleaned)
    cleaned = re.sub(r'ep\s+\d+.*', '', cleaned, flags=re.I)
    
    # Remove specific trailer tags
    cleaned = cleaned.replace('فاصل إعلاني', '').replace('إعلان', '').strip()
    
    # Remove bracketed content (Round and Square) if we haven't already used it
    cleaned = re.sub(r'[\(\[].*?[\)\]]', '', cleaned).strip()
    
    # Final cleanup of common symbols
    cleaned = cleaned.replace('-', '').replace('—', '').replace(':', '').strip()
    
    # Strip trailing numbers or single chars
    cleaned = re.sub(r'\s+\d+\s*$', '', cleaned).strip()
        
    return cleaned

def extract_episode_number(title):
    match = re.search(r'الحلقة\s+(\d+)', title)
    return match.group(1) if match else "1"

def generate_html(std_item, template_content, episodes=None):
    title = std_item.get('title', '')
    original_title = std_item.get('orig_title', '')
    poster = std_item.get('poster', '')
    description = std_item.get('desc', '') or "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    year = std_item.get('year', '2026')
    rating = std_item.get('rating', '⭐ 7.8')
    item_type = std_item.get('type', 'series')
    watch_url = std_item.get('watch_url', 'https://www.tomito.xyz')
    
    seo_title = f"{title} — مشاهدة 2026 فابور مجاناً على تومتو"
    html = template_content
    html = html.replace('24 / 24 | TOMITO MOVIES', seo_title)
    html = html.replace('<title>24 (2001) | Watch online on TOMITO</title>', f'<title>{seo_title}</title>')
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
        
    json_files = {
        'ramadan': ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json'],
        'movies': ['all_movies1.json'],
        'anime': ['anime.json'],
        'series': ['series.json']
    }
    series_map = {}
    tmdb_cache = {}
    all_std_items = []

    categories_data = {
        'ramadan': {'title': 'مسلسلات رمضان 2026', 'items': []},
        'movies': {'title': 'أفلام حصرية 2026', 'items': []},
        'anime': {'title': 'أنمي وكرتون 2026', 'items': []},
        'series': {'title': 'مسلسلات عربية وأجنبية 2026', 'items': []}
    }

    for cat_name, files in json_files.items():
        for jf in files:
            data = load_json(jf)
            for item in data:
                title = item.get('title', '')
                if not title: continue
                
                # Cleanup title for searching/slug
                base_title = extract_series_parent(title)
                
                if base_title not in tmdb_cache:
                    info = search_tmdb_info(base_title)
                    if not info:
                        # Fallback: check if JSON already has a TMDB poster link or useful title
                        info = {'poster': item.get('poster', ''), 'id': None, 'type': 'tv'}
                    tmdb_cache[base_title] = info
                    time.sleep(0.05) if info.get('id') else None
                
                info = tmdb_cache[base_title]
                tmdb_id = info.get('id')
                tmdb_type = info.get('type', 'tv') # 'movie' or 'tv'
                poster = info.get('poster')
                
                item_type = item.get('type', 'series')
                if item_type == 'episode':
                    if base_title not in series_map:
                        series_map[base_title] = {'parent': None, 'episodes_dict': {}, 'tmdb_id': tmdb_id, 'tmdb_type': tmdb_type}
                    t_key = title.strip()
                    if t_key not in series_map[base_title]['episodes_dict']:
                        series_map[base_title]['episodes_dict'][t_key] = item
                elif item_type == 'series':
                    if base_title not in series_map:
                        series_map[base_title] = {'parent': None, 'episodes_dict': {}, 'tmdb_id': tmdb_id, 'tmdb_type': tmdb_type}
                    series_map[base_title]['parent'] = item
                    categories_data[cat_name]['items'].append(('series', title)) # Use original title
                elif item_type == 'movie':
                    base_slug = clean_slug(title)
                    # For movies, ensure media_type is 'movie'
                    m_type = tmdb_type if tmdb_type == 'movie' else 'movie'
                    
                    if tmdb_id:
                        watch_url = f"https://tomito.xyz/{m_type}/{tmdb_id}-{base_slug}"
                    else:
                        watch_url = f"https://tomito.xyz/movies/{base_slug}"

                    std_item = {
                        'title': title, 'orig_title': title, 'poster': poster,
                        'desc': item.get('description', ''), 'year': '2026', 'rating': '⭐ حصري',
                        'type': 'movie', 'watch_url': watch_url, 'source': 'json'
                    }
                    if std_item['poster']: 
                        all_std_items.append(std_item)
                        categories_data[cat_name]['items'].append(('movie', title))

    processed_titles = set()
    cards_html = ""
    new_urls = ["https://tomito.xyz/", "https://tomito.xyz/movies"]
    
    os.makedirs('ramadan-trailer', exist_ok=True)
    os.makedirs('movies', exist_ok=True)
    os.makedirs('watch', exist_ok=True)
    
    # Process Series (Trailer Landing Pages)
    for title, info in series_map.items():
        episodes_list = list(info['episodes_dict'].values())
        if not info['parent'] and episodes_list:
            info['parent'] = {
                'title': title, 'orig_title': title, 'poster': tmdb_cache.get(title, {}).get('poster', ''),
                'desc': episodes_list[0].get('description', ""), 'year': '2026', 'rating': '⭐ حصري',
                'type': 'series', 'source': 'json'
            }
        
        parent = info['parent']
        if not parent or not parent.get('poster'): continue
        
        series_slug = clean_slug(title)
        
        # Determine canonical URL using TMDB info
        tmdb_info = tmdb_cache.get(title, {})
        tmdb_id = tmdb_info.get('id')
        tmdb_type = tmdb_info.get('type', 'tv')
        
        if tmdb_id:
            parent['watch_url'] = f"https://tomito.xyz/{tmdb_type}/{tmdb_id}-{series_slug}"
        else:
            parent['watch_url'] = f"https://tomito.xyz/ramadan-trailer/{series_slug}"
        
        # Prepare episode links for the series trailer page
        eps_for_rendering = []
        for ep in episodes_list:
            ep_num = extract_episode_number(ep['title'])
            ep_slug = f"{series_slug}-ep-{ep_num}"
            
            # Use the canonical series URL as base for episodes
            ep_watch_url = parent['watch_url']
            if '?' in ep_watch_url: ep_watch_url += f"&episode={ep_num}"
            else: ep_watch_url += f"?episode={ep_num}"

            eps_for_rendering.append({
                'title': ep['title'],
                'watch_url': ep_watch_url
            })
            
            # Generate Individual Episode (Trailer) Page in /watch/
            ep_std = {
                'title': ep['title'], 'orig_title': ep['title'], 'poster': parent['poster'],
                'desc': ep.get('description', parent.get('desc', parent.get('description', ''))), 'year': '2026', 'rating': '⭐ حصري',
                'type': 'episode', 'watch_url': ep_watch_url,
                'source': 'json'
            }
            html = generate_html(ep_std, template_content)
            with open(os.path.join('watch', f"{ep_slug}.html"), 'w', encoding='utf-8') as f:
                f.write(html)
            
            new_urls.append(f"https://tomito.xyz/watch/{ep_slug}")
            
        # Generate Series (Trailer) Landing Page
        html = generate_html(parent, template_content, episodes=eps_for_rendering)
        with open(os.path.join('ramadan-trailer', f"{series_slug}.html"), 'w', encoding='utf-8') as f:
            f.write(html)
        
        new_urls.append(parent['watch_url'])
        
    # Write HTML pages for movies/anime/series and add to sitemap
    for cat_id, cat_info in categories_data.items():
        if cat_id == 'ramadan':
            continue  # ramadan series already handled above
        for item_type, title in cat_info['items']:
            base_slug = clean_slug(title)
            
            # Lookup TMDB info for this item
            parent_title = title if item_type == 'movie' else extract_series_parent(title)
            info = tmdb_cache.get(parent_title, {})
            tmdb_id = info.get('id')
            tmdb_type = info.get('type', 'tv') if item_type != 'movie' else 'movie'
            
            # Use a cleaner slug for TMDB URLs if possible
            tmdb_slug = clean_slug(parent_title)
            base_slug = title.strip().replace(' ', '-').lower() 
            
            if item_type == 'movie':
                std_item = next((x for x in all_std_items if x['title'] == title), None)
                if std_item and std_item.get('poster'):
                    os.makedirs('movies', exist_ok=True)
                    
                    # Update watch_url for movies using cleaner slug
                    if tmdb_id:
                        std_item['watch_url'] = f"https://tomito.xyz/{tmdb_type}/{tmdb_id}-{tmdb_slug}"
                    else:
                        std_item['watch_url'] = f'https://tomito.xyz/movies/{base_slug}'
                        
                    page_html = generate_html(std_item, template_content)
                    with open(os.path.join('movies', f'{base_slug}.html'), 'w', encoding='utf-8') as mf:
                        mf.write(page_html)
                    
                    new_urls.append(std_item['watch_url'])
            elif item_type == 'series':
                s_info = series_map.get(parent_title)
                if not s_info:
                    continue
                s_parent = s_info.get('parent')
                if not s_parent or not s_parent.get('poster'):
                    continue
                folder = 'anime-trailer' if cat_id == 'anime' else 'series'
                os.makedirs(folder, exist_ok=True)
                
                # Ensure the watch_url in the landing page is correct
                if tmdb_id:
                    s_parent['watch_url'] = f"https://tomito.xyz/{tmdb_type}/{tmdb_id}-{tmdb_slug}"
                else:
                    s_parent['watch_url'] = f'https://tomito.xyz/{folder}/{base_slug}'

                page_html = generate_html(s_parent, template_content)
                with open(os.path.join(folder, f'{base_slug}.html'), 'w', encoding='utf-8') as sf:
                    sf.write(page_html)
                
                new_urls.append(s_parent['watch_url'])

    # Generate categorized sections for index.html
    sections_html = ""
    for cat_id, cat_info in categories_data.items():
        if not cat_info['items']: continue
        
        sections_html += f'\n<section class="section" id="{cat_id}">\n'
        sections_html += f'  <h2 class="section-title">{cat_info["title"]}</h2>\n'
        sections_html += f'  <div class="grid">\n'
        
        for item_type, title in cat_info['items']:
            base_slug = clean_slug(title)
            
            # Get TMDB info from cache if available
            parent_title = title if item_type == 'movie' else extract_series_parent(title)
            info = tmdb_cache.get(parent_title, {})
            poster = info.get('poster')
            tmdb_id = info.get('id')
            media_type = info.get('type', 'tv') if item_type != 'movie' else 'movie'
            
            if tmdb_id:
                href = f"https://tomito.xyz/{media_type}/{tmdb_id}-{base_slug}"
            else:
                href = f"ramadan-trailer/{base_slug}" if item_type == 'series' else f"movies/{base_slug}"
            
            label = "حصري" if cat_id == 'ramadan' else ("فيلم" if item_type == 'movie' else "مسلسل")
            
            sections_html += f"""
    <a class="card" href="{href}">
      <img class="card-poster" src="{poster}" alt="{title}" loading="lazy">
      <div class="card-overlay"><div class="card-meta">{label}</div></div>
      <div class="card-bottom"><div class="card-title"><div class="card-title-ar">{title}</div></div></div>
    </a>"""
        sections_html += "\n  </div>\n</section>"

    # Update index.html
    index_path = 'index.html'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
        
        # Replace the entire dynamic component
        start_tag = '<!-- DYNAMIC_CONTENT_START -->'
        end_tag = '<!-- DYNAMIC_CONTENT_END -->'
        pattern = re.compile(re.escape(start_tag) + r'.*?' + re.escape(end_tag), re.DOTALL)
        
        if pattern.search(index_content):
            new_index_content = pattern.sub(f"{start_tag}\n{sections_html}\n{end_tag}", index_content)
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(new_index_content)
        else:
            # Fallback if tags not found (for the first time)
            pattern = re.compile(re.escape('<section class="section" id="ramadan">') + r'.*?</section>', re.DOTALL)
            if pattern.search(index_content):
                with open(index_path, 'w', encoding='utf-8') as f:
                    # Inject tags for future runs
                    replacement = f"{start_tag}\n{sections_html}\n{end_tag}"
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
                if loc is not None and loc.text:
                    url_text = loc.text.replace('.html', '').strip()
                    if url_text and 'tomito.xyz' in url_text: 
                        existing_urls.add(url_text)
        except Exception: pass
    
    for url in new_urls:
        existing_urls.add(url.replace('.html', '').strip())
    
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in sorted(list(existing_urls)):
            if url: f.write(f'  <url><loc>{url}</loc><priority>0.8</priority></url>\n')
        f.write('</urlset>')

if __name__ == '__main__':
    main()
