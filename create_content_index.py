#!/usr/bin/env python3
import os
import json
import re
from html import unescape

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def extract_meta(html_content):
    meta = {}
    
    # Extract Title (from og:title or title tag)
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
    if title_match:
        meta['title'] = unescape(title_match.group(1).split(' — ')[0])
    else:
        title_tag = re.search(r'<title>([^<]+)</title>', html_content)
        if title_tag:
            meta['title'] = unescape(title_tag.group(1).split(' — ')[0])
            
    # Extract Poster
    poster_match = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
    if poster_match:
        meta['poster'] = poster_match.group(1)
        
    # Extract Year and Rating from JSON-LD if possible
    json_ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL)
    if json_ld_match:
        try:
            data = json.loads(json_ld_match.group(1))
            meta['rating'] = data.get('aggregateRating', {}).get('ratingValue', '')
            meta['year'] = data.get('datePublished', '')
        except:
            pass
            
    # Extract Genres from keywords
    keywords_match = re.search(r'<meta name="keywords" content="([^"]+)"', html_content)
    if keywords_match:
        # Usually keywords are: title, title, watch title, download title, ..., genre1, genre2
        keywords = [k.strip() for k in keywords_match.group(1).split(',')]
        # Heuristic: last few keywords are genres
        meta['genres'] = keywords[-3:]
        
    return meta

def main():
    data_dir = os.path.join(BASE_PATH, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    index = []
    
    for folder in ['movie', 'tv']:
        folder_path = os.path.join(BASE_PATH, folder)
        if not os.path.exists(folder_path):
            continue
            
        print(f"Scanning {folder}...")
        count = 0
        for filename in os.listdir(folder_path):
            if filename.endswith('.html'):
                slug = filename[:-5]
                with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                    content = f.read()
                    meta = extract_meta(content)
                    meta['folder'] = folder
                    meta['slug'] = slug
                    index.append(meta)
                    count += 1
        print(f"Found {count} items in {folder}")

    with open(os.path.join(data_dir, 'content_index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(index)} items to data/content_index.json")

if __name__ == '__main__':
    main()
