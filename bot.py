import json
import os
import urllib.parse
import requests
import re

TMDB_API_KEY = '882e741f7283dc9ba1654d4692ec30f6'
BASE_URL = 'https://api.themoviedb.org/3'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'

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
            print(f"Error fetching from {url}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception fetching from {url}: {e}")
        return []

def generate_html(item, template_content, item_type):
    if item_type == 'movie':
        title = item.get('title', '')
        original_title = item.get('original_title', '')
        date = item.get('release_date', '')
    else:
        title = item.get('name', '')
        original_title = item.get('original_name', '')
        date = item.get('first_air_date', '')
        
    poster_path = item.get('poster_path', '')
    poster = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else ""
    description = item.get('overview', '')
    if not description:
        description = "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    
    rating = item.get('vote_average', '0.0')
    year = date.split('-')[0] if date else "2026"
    
    # Simple ID-based URL for demonstration
    item_id = item.get('id')
    tmdb_type = 'movie' if item_type == 'movie' else 'tv'
    item_url = f"https://tomito.xyz/{tmdb_type}/{item_id}"
    
    html = template_content
    # Replace the title
    html = html.replace('24 / 24 | TOMITO MOVIES', f'{title} | TOMITO MOVIES')
    html = html.replace('مسلسل 24 (2001)', f'{title} ({year})')
    html = html.replace('Watch 24 (2001)', f'Watch {title} ({year})')
    
    # Replace poster
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster)
    html = html.replace('alt="24"', f'alt="{title}"')
    
    # Replace title texts in the body
    html = html.replace('<span>24</span>', f'<span>{title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{original_title}</span>')
    
    # Replace descriptions
    desc_escaped = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    template_desc = 'Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season.'
    html = html.replace(template_desc, desc_escaped)
    
    # Replace tags
    html = html.replace('<span class="tag">2001</span>', f'<span class="tag">{year}</span>')
    html = html.replace('<span class="tag">⭐ 7.8</span>', f'<span class="tag">⭐ {rating}</span>')
    
    if item_type == 'movie':
        html = html.replace('TV Series | مسلسل', 'Movie | فيلم')
    else:
        html = html.replace('TV Series | مسلسل', 'TV Series | مسلسل')
    
    # Replace Watch/Download links
    html = html.replace('https://tomito.xyz/tv/1973-24', item_url)
    
    return html, title, poster, item_url

def main():
    template_path = 'movies/24.html'
    if not os.path.exists(template_path):
        print(f"Template {template_path} not found.")
        return
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    sitemap_path = 'sitemap.xml'
    sitemap_content = ""
    if os.path.exists(sitemap_path):
        with open(sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
    
    new_urls = []
    all_items = []
    
    categories = [
        ('movie/popular', 'movie'),
        ('tv/popular', 'series')
    ]
    
    for endpoint, item_type in categories:
        print(f"Fetching {item_type} from TMDB...")
        results = fetch_tmdb_data(endpoint)
        for item in results:
            # Generate and write HTML
            html, title, poster, watch_url = generate_html(item, template_content, item_type)
            
            # Simple slug generation
            slug = title.replace(' ', '-').replace('/', '-').lower()
            slug = "".join([c for c in slug if c.isalnum() or c == '-'])
            
            if not slug:
                slug = str(item.get('id'))
                
            folder = 'movies' if item_type == 'movie' else 'series'
            os.makedirs(folder, exist_ok=True)
            
            file_path = os.path.join(folder, f"{slug}.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            # For index.html
            all_items.append({
                'title': title,
                'poster': poster,
                'slug': slug,
                'folder': folder
            })
            
            loc_url = f"https://nordrama.live/{folder}/{slug}"
            if f"<loc>{loc_url}</loc>" not in sitemap_content and loc_url not in new_urls:
                new_urls.append(loc_url)
                
    # Update index.html with cards
    index_path = 'index.html'
    if os.path.exists(index_path) and all_items:
        print(f"Updating {index_path} with {len(all_items)} items...")
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
            
        cards_html = ""
        for s in all_items:
            card = f"""
    <a class="card" href="{s['folder']}/{s['slug']}">
      <img class="card-poster" src="{s['poster']}" alt="{s['title']}" loading="lazy">
      <div class="card-overlay">
        <div class="card-meta">{"فيلم" if s['folder'] == 'movies' else "مسلسل"}</div>
      </div>
      <div class="card-bottom">
        <div class="card-title">
          <div class="card-title-ar">{s['title']}</div>
        </div>
      </div>
    </a>
"""
            cards_html += card
            
        start_marker = '<div class="grid" id="all">'
        # Improved regex to find the grid and replace its content
        pattern = re.compile(re.escape(start_marker) + r'.*?</div>\s*</section>', re.DOTALL)
        
        # We want to keep <div class="grid" id="all"> and </div>\n</section>
        replacement = start_marker + cards_html + "\n  </div>\n</section>"
        
        if pattern.search(index_content):
            new_index_content = pattern.sub(replacement, index_content)
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(new_index_content)
            print("index.html updated successfully with regex.")
        else:
            # Fallback for old way if structure changed
            print("Regex pattern not found, trying manual search...")
            start_idx = index_content.find(start_marker)
            if start_idx != -1:
                content_start = start_idx + len(start_marker)
                # Find the NEXT section or end of file
                next_section_idx = index_content.find('<footer', content_start)
                if next_section_idx == -1:
                    next_section_idx = len(index_content)
                
                # Find the LAST </div> before the next section
                end_idx = index_content.rfind('</div>', content_start, next_section_idx)
                if end_idx != -1:
                    new_index_content = index_content[:content_start] + cards_html + index_content[end_idx:]
                    with open(index_path, 'w', encoding='utf-8') as f:
                        f.write(new_index_content)
                    print("index.html updated successfully with fallback.")

    if new_urls and sitemap_content:
        sitemap_content = sitemap_content.strip()
        if sitemap_content.endswith('</urlset>'):
            sitemap_content = sitemap_content[:-9]
        else:
            sitemap_content = sitemap_content.replace('</urlset>', '')
            
        for url in new_urls:
            sitemap_content += f"  <url><loc>{url}</loc><priority>0.8</priority><changefreq>monthly</changefreq></url>\n"
        sitemap_content += '</urlset>'
        
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
            
    print(f"Generated pages and added {len(new_urls)} new links to sitemap.")

if __name__ == '__main__':
    main()
