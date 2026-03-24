import os

def generate_sitemap():
    base_url = "https://tomito.xyz"
    root_dir = "/home/tomito/tomito"
    content_dirs = ['movies', 'series', 'anime', 'actors', 'watch', 'ramadan-trailer']
    
    urls = []
    
    # Add homepage
    urls.append((f"{base_url}/", 1.0))
    
    # Scan root for other potential pages (like movies.html)
    for f in os.listdir(root_dir):
        if f.endswith(".html") and f not in ['index.html', 'index-backup.html', 'test.html']:
            # Avoid files with -backup or test in name if any
            if '-' in f and f.split('-')[-1] in ['backup', 'test']: continue
            slug = f[:-5]
            urls.append((f"{base_url}/{slug}", 0.9))
    
    # Scan directories
    for directory in content_dirs:
        dir_path = os.path.join(root_dir, directory)
        if not os.path.exists(dir_path):
            continue
            
        print(f"Scanning {directory}...")
        for filename in os.listdir(dir_path):
            if filename.endswith(".html"):
                slug = filename[:-5] # remove .html
                url = f"{base_url}/{directory}/{slug}"
                # Standard priority for content, lower for watch/episodes
                priority = 0.8
                if directory == 'watch': priority = 0.6
                urls.append((url, priority))
    
    # Sort and remove duplicates correctly
    # Group by URL and keep max priority
    url_map = {}
    for url, prio in urls:
        if url not in url_map or prio > url_map[url]:
            url_map[url] = prio
            
    sorted_urls = sorted(url_map.items())
    
    # Write to sitemap.xml
    sitemap_path = os.path.join(root_dir, "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url, priority in sorted_urls:
            f.write(f'  <url><loc>{url}</loc><priority>{priority:.1f}</priority></url>\n')
        f.write('</urlset>')
    
    print(f"Successfully generated {sitemap_path} with {len(sorted_urls)} URLs.")

if __name__ == "__main__":
    generate_sitemap()
