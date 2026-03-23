import os
import re
import requests
import json
import time

TMDB_API_KEY = '882e741f7283dc9ba1654d4692ec30f6'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'

def extract_series_parent(title):
    cleaned = title
    
    # Split by standard dashes to isolate the main title
    parts = re.split(r'\s+[-–]\s+', cleaned)
    if len(parts) > 1 and not parts[0].isdigit():
         cleaned = parts[0]
    else:
         # Try removing everything after "الحلقة" or "الاوفا"
         cleaned = re.sub(r'\s+(الحلقة|الاوفا|ep).*$', '', cleaned, flags=re.I)
         
    # Remove common prefixes
    cleaned = re.sub(r'^(مسلسل|برنامج|انمي|أنمي|فيلم)\s+', '', cleaned).strip()
    cleaned = re.sub(r'(مسلسل|برنامج|انمي|أنمي|فيلم)', '', cleaned).strip()
    
    # Catch any fasel HD leftovers
    cleaned = re.sub(r'فاصل[- ]إعلاني', '', cleaned)
    cleaned = re.sub(r'إعلان', '', cleaned)
    
    # Seasons
    cleaned = cleaned.replace('الموسم الأول', '').replace('الموسم الثاني', '').replace('الموسم الثالث', '')
    cleaned = cleaned.replace('الموسم الرابع', '').replace('الموسم الخامس', '').replace('الموسم السادس', '')
    cleaned = re.sub(r'الموسم\s+\w+', '', cleaned)
    cleaned = re.sub(r'الموسم\s+\d+', '', cleaned)
    
    # Symbols
    cleaned = cleaned.replace('-', ' ').replace('—', ' ').strip()
    cleaned = re.sub(r'[\(\[].*?[\)\]]', '', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def search_tmdb_info(title):
    search_query = title.strip()
    if not search_query or search_query.isdigit(): return None
    params = {'api_key': TMDB_API_KEY, 'language': 'ar', 'query': search_query}
    try:
        response = requests.get("https://api.themoviedb.org/3/search/multi", params=params, timeout=10)
        if response.status_code == 200:
            results = response.json().get('results', [])
            for res in results:
                if res.get('poster_path'):
                    return f"{IMAGE_BASE_URL}{res.get('poster_path')}"
    except Exception as e:
        print(f"Error fetching {title}: {e}")
    return None

def update_html_posters(d, filename, poster):
    filepath = os.path.join(d, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    # Replace og:image
    new_content = re.sub(r'<meta property="og:image"[^>]*>', f'<meta property="og:image" content="{poster}">', new_content)
    
    # Replace hero image correctly.
    # It might be Fasel-HD, or TMDB generic. So we match ANY image inside series-hero.
    new_content = re.sub(r'(<div class="series-hero">\s*)<img\s+src="[^"]+"\s+alt="([^"]+)"\s+loading="eager">', r'\1<img src="' + poster + '" alt="\\2" loading="eager">', new_content)
    
    # Also catch cases without alt or different order
    new_content = re.sub(r'(<div class="series-hero">\s*)<img\s+src="[^"]+"', r'\1<img src="' + poster + '"', new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    dirs = ['/home/tomito/tomito/ramadan-trailer', '/home/tomito/tomito/series', '/home/tomito/tomito/watch']
    cache_file = '/home/tomito/tomito/poster_cache.json'
    
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            
    # Clean out nulls from previous bad runs
    cache = {k: v for k, v in cache.items() if v is not None}

    updated_count = 0
    for d in dirs:
        if not os.path.exists(d): continue
        print(f"Processing {d}...")
        for filename in os.listdir(d):
            if filename.endswith('.html'):
                base = filename.replace('.html', '')
                query = extract_series_parent(base)
                
                # Further specific cleanups
                if "بالمية" in query: query = "11 بالمية"
                elif "reacher" in query.lower(): query = "Reacher"
                elif "the sopranos" in query.lower(): query = "The Sopranos"
                elif "conan" in query.lower(): query = "Detective Conan"
                
                poster = None
                if query in cache:
                    poster = cache[query]
                else:
                    poster = search_tmdb_info(query)
                    if poster:
                        cache[query] = poster
                    time.sleep(0.1) # Be nice to TMDB API
                    
                if not poster: 
                    # Try falling back to English query if arabic fails occasionally
                    if re.match(r'^[a-zA-Z\s]+$', query):
                         poster = search_tmdb_info(query)
                         if poster: cache[query] = poster
                         
                if not poster:
                    continue
                
                if update_html_posters(d, filename, poster):
                    updated_count += 1

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)
        
    print(f"Complete! Updated images for {updated_count} files.")

if __name__ == "__main__":
    main()
