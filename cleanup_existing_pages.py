import os
import json
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor
import re

# --- Configuration ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_PATH, 'data', 'content_index.json')
TARGET_DIRS = ['movie', 'tv', 'actor']

def load_valid_paths():
    valid = set()
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                folder = item.get('folder')
                slug = item.get('slug')
                if folder and slug:
                    # Store as "folder/slug" for fast comparison
                    valid.add(f"{folder}/{slug}")
    return valid

def cleanup_file(file_path, valid_paths):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        modified = False
        
        # Determine if this is a content page or actor page
        is_actor = 'actor/' in file_path
        
        # Find all card links
        cards = soup.find_all('a', class_='card')
        for card in cards:
            href = card.get('href', '')
            # Clean href: remove leading / and .html
            clean_href = href.strip('/')
            if clean_href.endswith('.html'):
                clean_href = clean_href[:-5]
            
            # If it's a content link (movie/ or tv/), check if it's valid
            if clean_href.startswith(('movie/', 'tv/')):
                if clean_href not in valid_paths:
                    card.decompose()
                    modified = True
        
        # After removing dead cards, check if grids are empty
        grids = soup.find_all('div', class_='grid')
        for grid in grids:
            # Check if grid has any .card children left
            remaining_cards = grid.find_all('a', class_='card')
            if not remaining_cards:
                # Section is now empty
                section = grid.find_parent('section')
                if section:
                    if is_actor:
                        # For actors, just remove the empty section
                        section.decompose()
                        modified = True
                    else:
                        # For movie/tv, replace with SEO fallback
                        # Try to get some info for the fallback
                        title_tag = soup.find('h1', class_='series-title')
                        title = title_tag.get_text(separator=" ").strip() if title_tag else "هذا المحتوى"
                        
                        fallback_html = f'''
<div style="color:#ccc;font-size:0.95rem;line-height:1.9;text-align:justify;padding:20px;">
    <p>تابع استكشاف أحدث الأفلام والمسلسلات على موقعنا. نحن نحرص دائماً على توفير أفضل جودة مشاهدة وأسرع روابط تحميل لكافة الأعمال الفنية الحصرية. شاهد الآن أقوى إنتاجات السينما العالمية والدراما العربية بجودة HD وبدون إعلانات مزعجة.</p>
    <p>كلمات مفتاحية: مشاهدة مباشرة، تحميل سريع، أفلام 2026، مسلسلات رمضان، حصريات توميتو، أفضل جودة HD، سينما اون لاين.</p>
</div>'''
                        grid.replace_with(BeautifulSoup(fallback_html, 'html.parser'))
                        # Also remove the section title since it's now just general SEO
                        section_title = section.find('h2', class_='section-title')
                        if section_title:
                            section_title.decompose()
                        modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False

def main():
    print("Loading valid paths...")
    valid_paths = load_valid_paths()
    print(f"Loaded {len(valid_paths)} valid paths.")
    
    files_to_process = []
    for d in TARGET_DIRS:
        dir_path = os.path.join(BASE_PATH, d)
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.endswith('.html'):
                    files_to_process.append(os.path.join(dir_path, f))
    
    total = len(files_to_process)
    print(f"Found {total} files to process.")
    
    count = 0
    modified_count = 0
    
    # Using ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor() as executor:
        # We need to pass valid_paths to each process. 
        # Since it's a large set, we use a wrapper or just submit
        from functools import partial
        func = partial(cleanup_file, valid_paths=valid_paths)
        
        for result in executor.map(func, files_to_process):
            count += 1
            if result:
                modified_count += 1
            if count % 1000 == 0:
                print(f"Processed {count}/{total} files... (Modified: {modified_count})")

    print(f"\nCleanup finished!")
    print(f"Total files processed: {count}")
    print(f"Total files modified: {modified_count}")

if __name__ == "__main__":
    main()
