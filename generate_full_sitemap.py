#!/usr/bin/env python3
"""Generate sitemap index and individual category sitemaps from actual HTML files on disk."""

import os
from datetime import datetime

def generate_sitemaps():
    base_url = "https://nordrama.live"
    root_dir = os.path.dirname(os.path.abspath(__file__))
    content_dirs = ['movie', 'tv', 'actor']
    today = datetime.now().strftime('%Y-%m-%d')
    
    sitemap_index_urls = []
    
    # 1. Main Root Sitemap (Homepage & Root Pages)
    root_urls = []
    root_urls.append((f"{base_url}/", 1.0, 'daily'))
    for f in os.listdir(root_dir):
        if f.endswith('.html') and f not in ['index.html', 'test.html']:
            slug = f[:-5]
            root_urls.append((f"{base_url}/{slug}", 0.9, 'weekly'))
    
    write_sitemap_file(os.path.join(root_dir, 'sitemap_root.xml'), root_urls, today)
    sitemap_index_urls.append(f"{base_url}/sitemap_root.xml")

    # 2. Category specific sitemaps
    priority_map = {
        'movie': 0.8,
        'tv': 0.8,
        'actor': 0.6,
    }
    
    for directory in content_dirs:
        dir_path = os.path.join(root_dir, directory)
        if not os.path.exists(dir_path):
            continue
        
        dir_urls = []
        priority = priority_map.get(directory, 0.7)
        freq = 'weekly' if directory in ['movie', 'tv'] else 'monthly'
        
        for entry in os.listdir(dir_path):
            full_path = os.path.join(dir_path, entry)
            
            if entry.endswith('.html'):
                slug = entry[:-5]
                url = f"{base_url}/{directory}/{slug}"
                dir_urls.append((url, priority, freq))
            elif os.path.isdir(full_path):
                # Subdirectories (like ramadan-trailer/slug/)
                url = f"{base_url}/{directory}/{entry}"
                dir_urls.append((url, priority, freq))
                # Also check for nested HTML files
                for sub_f in os.listdir(full_path):
                    if sub_f.endswith('.html') and sub_f != 'index.html':
                        sub_slug = sub_f[:-5]
                        sub_url = f"{base_url}/{directory}/{entry}/{sub_slug}"
                        dir_urls.append((sub_url, priority - 0.1, freq))
        
        if dir_urls:
            filename = f"sitemap_{directory}.xml"
            write_sitemap_file(os.path.join(root_dir, filename), dir_urls, today)
            sitemap_index_urls.append(f"{base_url}/{filename}")
            print(f"  {directory}: {len(dir_urls)} URLs -> {filename}")

    # 3. Generate Main Sitemap Index
    index_path = os.path.join(root_dir, 'sitemap.xml')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for loc in sitemap_index_urls:
            f.write(f'  <sitemap>\n')
            f.write(f'    <loc>{loc}</loc>\n')
            f.write(f'    <lastmod>{today}</lastmod>\n')
            f.write(f'  </sitemap>\n')
        f.write('</sitemapindex>')
    
    print(f"\nGenerated sitemap index: {index_path}")

def write_sitemap_file(filepath, urls, date):
    # Deduplicate — keep highest priority
    url_map = {}
    for url, prio, freq in urls:
        if url not in url_map or prio > url_map[url][0]:
            url_map[url] = (prio, freq)
    
    sorted_urls = sorted(url_map.items())
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url, (priority, freq) in sorted_urls:
            f.write(f'  <url>\n')
            f.write(f'    <loc>{url}</loc>\n')
            f.write(f'    <lastmod>{date}</lastmod>\n')
            f.write(f'    <changefreq>{freq}</changefreq>\n')
            f.write(f'    <priority>{priority:.1f}</priority>\n')
            f.write(f'  </url>\n')
        f.write('</urlset>')

if __name__ == '__main__':
    generate_sitemaps()
