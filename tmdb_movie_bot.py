import requests
import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

TMDB_API_KEY = "882e741f7283dc9ba1654d4692ec30f6"
BASE_URL = "https://api.themoviedb.org/3"
MOVIES_DIR = "/home/tomito/tomito/movies"
DATA_DIR = "/home/tomito/tomito/data"
TEMPLATE_PATH = "/home/tomito/tomito/movies/24.html"

def clean_title_junk(title):
    """Remove common junk from titles."""
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r' - .*', '', title)
    title = re.sub(r' \d{4}', '', title)
    return title.strip()

def clean_slug(title):
    """Create a URL-friendly slug."""
    # Remove non-alphanumeric characters (keep Arabic)
    slug = re.sub(r'[^\w\s-]', '', title).strip().lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[-\s_]+', '-', slug)
    return slug

def get_movies_for_year(year, target_count=3000):
    movies = []
    page = 1
    
    print(f"Fetching movies for year {year}...")
    
    while len(movies) < target_count:
        url = f"{BASE_URL}/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_year": year,
            "page": page,
            "sort_by": "popularity.desc",
            "language": "ar" # Try to get Arabic metadata if available
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'results' not in data or not data['results']:
                print(f"No more results found at page {page}.")
                break
                
            movies.extend(data['results'])
            print(f"Fetched page {page} ({len(movies)} movies so far)...")
            
            if data['total_pages'] <= page:
                break
                
            page += 1
            if page > 500: # TMDB limit
                break
                
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
            
    return movies[:target_count]

def generate_movie_page(movie, template_content):
    title = movie.get('title', 'Unknown')
    original_title = movie.get('original_title', title)
    overview = movie.get('overview', 'No description available.')
    # Escape some common HTML entities in overview
    overview = overview.replace('"', '&quot;').replace("'", "&#x27;")
    
    poster_path = movie.get('poster_path', '')
    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Poster"
    release_date = movie.get('release_date', '2026')
    release_year = release_date.split('-')[0] if release_date else '2026'
    rating = movie.get('vote_average', 0)
    tmdb_id = movie.get('id')
    
    slug = clean_slug(original_title)
    if not slug:
        slug = f"movie-{tmdb_id}"
        
    html = template_content
    # Basic Metadata
    html = html.replace('<title>24 / 24 | TOMITO MOVIES</title>', f'<title>{title} / {original_title} | TOMITO MOVIES</title>')
    html = html.replace('content="24 / 24"', f'content="{title} / {original_title}"')
    html = html.replace('alt="24"', f'alt="{title}"')
    
    # Descriptions in meta
    meta_desc_target = 'مشاهدة وتحميل مسلسل 24 (2001) أون لاين بجودة عالية HD. Watch 24 (2001) online exclusively on TOMITO.'
    meta_desc_replacement = f'مشاهدة وتحميل فيلم {title} ({release_year}) أون لاين بجودة عالية HD. Watch {original_title} ({release_year}) online exclusively on TOMITO.'
    html = html.replace(meta_desc_target, meta_desc_replacement)
    
    # Posters
    html = html.replace('https://image.tmdb.org/t/p/original/iq6yrZ5LEDXf1ArCOYLq8PIUBpV.jpg', poster_url)
    
    # Hero Section Titles
    html = html.replace('<span>24</span>', f'<span>{title}</span>')
    html = html.replace('<span style="font-size: 0.6em; color: #aaa;">24</span>', f'<span style="font-size: 0.6em; color: #aaa;">{original_title}</span>')
    
    # Overview - Handling the specific multiline structure in the template
    # Target 1 (English/Top)
    target_desc_1 = """Counterterrorism agent Jack Bauer fights the bad guys
          of the world, a day at a time. With each week&#x27;s episode unfolding in real-time, &quot;24&quot; covers a
          single day in the life of Bauer each season."""
    html = html.replace(target_desc_1, overview)
    
    # Target 2 (Arabic/Bottom - note it's slightly different in template)
    target_desc_2 = """Counterterrorism agent Jack Bauer fights the bad guys of the world, a day at a time. With each week&#x27;s
          episode unfolding in real-time, &quot;24&quot; covers a single day in the life of Bauer each season."""
    html = html.replace(target_desc_2, overview)
    
    # Tags
    html = html.replace('<span class="tag">TV Series | مسلسل</span>', '<span class="tag">Movie | فيلم</span>')
    html = html.replace('<span class="tag">⭐ 7.8</span>', f'<span class="tag">⭐ {rating}</span>')
    html = html.replace('<span class="tag">2001</span>', f'<span class="tag">{release_year}</span>')
    
    # Buttons
    html = html.replace('https://tomito.xyz/tv/1973-24', f'https://tomito.xyz/movie/{tmdb_id}/watch')
    # Backup replacement for other common patterns
    html = html.replace('https://www.tomito.xyz/watch/movie/', f'https://tomito.xyz/movie/')
    if 'https://tomito.xyz/movie/' in html and '/watch' not in html:
        # This is a bit risky but we want to ensure /watch at the end
        pass 
    
    file_path = os.path.join(MOVIES_DIR, f"{slug}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    return {
        "id": tmdb_id,
        "title": title,
        "original_title": original_title,
        "slug": slug,
        "poster": poster_url,
        "year": release_year,
        "rating": rating,
        "url": f"movies/{slug}.html"
    }

def main():
    if not os.path.exists(MOVIES_DIR):
        os.makedirs(MOVIES_DIR)
    
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    movies_data = get_movies_for_year(2026, 3000)
    
    final_data = []
    print(f"Generating pages for {len(movies_data)} movies...")
    
    # Use ThreadPoolExecutor for faster file writing (though I/O bound)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_movie_page, movie, template_content) for movie in movies_data]
        for future in futures:
            final_data.append(future.result())
            
    # Save metadata to JSON
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    with open(os.path.join(DATA_DIR, 'movies_2026.json'), 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully generated {len(final_data)} movie pages.")

if __name__ == "__main__":
    main()
