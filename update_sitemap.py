import json
import os

SITEMAP_PATH = "/home/tomito/tomito/sitemap.xml"
MOVIES_JSON = "/home/tomito/tomito/data/movies_2026.json"

def update_sitemap():
    if not os.path.exists(MOVIES_JSON):
        print("Movies JSON not found.")
        return
        
    with open(MOVIES_JSON, 'r', encoding='utf-8') as f:
        movies = json.load(f)
        
    with open(SITEMAP_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Find the closing tag
    closing_tag_index = -1
    for i, line in enumerate(reversed(lines)):
        if '</urlset>' in line:
            closing_tag_index = len(lines) - 1 - i
            break
            
    if closing_tag_index == -1:
        print("Closing </urlset> tag not found.")
        return
        
    new_urls = []
    # Use a set to avoid adding duplicates if the script is run multiple times
    # Actually, the user just wants them added. I'll assume they aren't there yet.
    # But I'll do a quick check against existing locs.
    existing_locs = set()
    for line in lines:
        if '<loc>' in line:
            loc = line.split('<loc>')[1].split('</loc>')[0]
            existing_locs.add(loc)
    
    for movie in movies:
        url = f"https://tomito.xyz/{movie['url']}"
        if url not in existing_locs:
            new_urls.append(f'  <url><loc>{url}</loc><priority>0.8</priority></url>\n')
            
    if not new_urls:
        print("No new URLs to add.")
        return
        
    # Insert before the closing tag
    updated_lines = lines[:closing_tag_index] + new_urls + lines[closing_tag_index:]
    
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
        
    print(f"Added {len(new_urls)} new URLs to sitemap.xml")

if __name__ == "__main__":
    update_sitemap()
