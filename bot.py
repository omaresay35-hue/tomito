import json
import os
import urllib.parse

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_html(item, template_content):
    title = item.get('title', '')
    poster = item.get('poster', '')
    description = item.get('description', '')
    if not description:
        description = "شاهد واستمتع بأفضل الحلقات والمسلسلات والأفلام على موقعنا."
    item_url = item.get('url', '')
    
    html = template_content
    # Replace the title
    html = html.replace('24 / 24 | TOMITO MOVIES', f'{title} | TOMITO MOVIES')
    html = html.replace('مسلسل 24 (2001)', title)
    html = html.replace('Watch 24 (2001)', f'Watch {title}')
    
    # Replace poster
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster)
    html = html.replace('alt="24"', f'alt="{title}"')
    
    # Replace title texts in the body
    html = html.replace('<span>24</span>', f'<span>{title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{title}</span>')
    
    # Replace descriptions
    desc_escaped = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    html = html.replace('Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season.', desc_escaped)
    
    # Replace tags
    html = html.replace('<span class="tag">2001</span>', '<span class="tag">2026</span>')
    if item.get('type') == 'movie':
        html = html.replace('TV Series | مسلسل', 'Movie | فيلم')
    elif item.get('type') == 'episode':
        html = html.replace('TV Series | مسلسل', 'Episode | حلقة')
    
    # Replace Watch/Download links
    html = html.replace('https://tomito.xyz/tv/1973-24', item_url)
    
    return html

def main():
    json_files = ['ramadan_2026_results_1.json', 'ramadan_2026_results_2.json', 'ramadan_2026_results_3.json']
    
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
    all_series = []
    seen_series = set()
    
    for jf in json_files:
        if not os.path.exists(jf):
            print(f"Warning: {jf} not found.")
            continue
        print(f"Processing {jf}...")
        data = load_json(jf)
        for item in data:
            item_type = item.get('type')
            item_url = item.get('url', '')
            
            if not item_url:
                continue
            
            # Collect series for index.html
            if item_type == 'series':
                item_title = item.get('title', '')
                if item_title not in seen_series:
                    all_series.append(item)
                    seen_series.add(item_title)
                
            parts = item_url.strip('/').split('/')
            slug = parts[-1].split('?')[0]
            slug = urllib.parse.unquote(slug)
            
            folder = 'watch'
            if item_type == 'series':
                folder = 'series'
            elif item_type == 'movie':
                folder = 'movies'
            elif item_type == 'episode':
                folder = 'watch'
                
            os.makedirs(folder, exist_ok=True)
            
            file_path = os.path.join(folder, f"{slug}.html")
            
            # Generate and write HTML
            html = generate_html(item, template_content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            loc_url = f"https://nordrama.live/{folder}/{slug}"
            
            if f"<loc>{loc_url}</loc>" not in sitemap_content and loc_url not in new_urls:
                new_urls.append(loc_url)
                
    # Update index.html with series cards
    index_path = 'index.html'
    if os.path.exists(index_path) and all_series:
        print(f"Updating {index_path} with {len(all_series)} series...")
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
            
        cards_html = ""
        for s in all_series:
            s_title = s.get('title', '')
            s_poster = s.get('poster', '')
            s_url = s.get('url', '')
            s_parts = s_url.strip('/').split('/')
            s_slug = urllib.parse.unquote(s_parts[-1].split('?')[0])
            
            card = f"""
    <a class="card" href="series/{s_slug}">
      <img class="card-poster" src="{s_poster}" alt="{s_title}" loading="lazy">
      <div class="card-overlay">
        <div class="card-meta">حصري</div>
      </div>
      <div class="card-bottom">
        <div class="card-title">
          <div class="card-title-ar">{s_title}</div>
        </div>
      </div>
    </a>
"""
            cards_html += card
            
        # Replace content between <div class="grid" id="all"> and </div>
        start_marker = '<div class="grid" id="all">'
        end_marker = '</div>'
        
        start_idx = index_content.find(start_marker)
        if start_idx != -1:
            content_start = start_idx + len(start_marker)
            # Find the closing tag of the grid div
            # This is tricky if there are nested divs, but our structure looks flat.
            # We'll look for the first </div> after the start.
            end_idx = index_content.find(end_marker, content_start)
            if end_idx != -1:
                new_index_content = index_content[:content_start] + cards_html + index_content[end_idx:]
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(new_index_content)
                print("index.html updated successfully.")

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
