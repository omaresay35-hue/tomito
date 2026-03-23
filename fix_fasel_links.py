import os
import re

RAMADAN_DIR = '/home/tomito/tomito/ramadan-trailer'
SERIES_DIR = '/home/tomito/tomito/series'
WATCH_DIR = '/home/tomito/tomito/watch'
SITEMAP_PATH = '/home/tomito/tomito/sitemap.xml'

print("Parsing new sitemap...")
series_urls = []
watch_urls = []
if os.path.exists(SITEMAP_PATH):
    with open(SITEMAP_PATH, 'r', encoding='utf-8') as f:
        sitemap_content = f.read()
        series_urls = re.findall(r'<loc>(https://nordrama\.live/series/[^<]+)</loc>', sitemap_content)
        watch_urls = re.findall(r'<loc>(https://nordrama\.live/watch/[^<]+)</loc>', sitemap_content)
else:
    print("Sitemap not found!")
    exit(1)

def get_best_series_match(slug_or_filename):
    slug = slug_or_filename.replace('.html', '').replace('https://tomito.xyz/ramadan-trailer/', '').strip('/')
    slug = slug.replace('انمي-', '').replace('أنمي-', '').replace('مسلسل-', '').replace('برنامج-', '')
    slug = slug.replace('-فاصل-إعلاني', '').replace('---', '-').replace('--', '-')
    slug = re.sub(r'[:!()\[\]"“”]', '', slug)
    slug = slug.strip('-')
    
    if not slug: return None

    # Exact match in series_urls
    for url in series_urls:
        if slug in url:
            return url
    return None

def get_episode_url(base_slug, ep_num):
    clean_slug = base_slug.replace('.html', '').replace('https://tomito.xyz/ramadan-trailer/', '').strip('/')
    clean_slug = clean_slug.replace('انمي-', '').replace('أنمي-', '').replace('مسلسل-', '').replace('برنامج-', '')
    clean_slug = clean_slug.replace('-فاصل-إعلاني', '').replace('---', '-').replace('--', '-')
    clean_slug = re.sub(r'[:!()\[\]"“”]', '', clean_slug)
    clean_slug = clean_slug.strip('-')
    
    target_pattern = f"{clean_slug}-ep-{ep_num}.html"
    for url in watch_urls:
        if target_pattern in url:
            return url
            
    return f"https://nordrama.live/watch/{clean_slug}-ep-{ep_num}.html"

# Fix links ONLY inside files matching 'فاصل-إعلاني'
for target_dir in [RAMADAN_DIR, SERIES_DIR, WATCH_DIR]:
    if os.path.exists(target_dir):
        print(f"Updating files in {target_dir}...")
        count = 0
        for filename in os.listdir(target_dir):
            if filename.endswith('.html') and 'فاصل-إعلاني' in filename:
                file_path = os.path.join(target_dir, filename)
                base_series_url = get_best_series_match(filename)
                
                if not base_series_url:
                    base_series_url = "https://nordrama.live/"
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 1. Update main buttons (hrefs)
                new_content = re.sub(r'href="(?:https://(?:tomito\.xyz|nordrama\.live)/)?(?:ramadan-trailer/|tv/|movie/|watch/|series/)[^"]*"', f'href="{base_series_url}"', content, count=0)
                
                # 2. Update episode grid links
                def replace_ep_link(match):
                    url = match.group(1)
                    full_tag = match.group(0)
                    ep_match = re.search(r'episode=(\d+)', url) or re.search(r'-ep-(\d+)', url)
                    if ep_match:
                        ep_num = ep_match.group(1)
                        new_ep_url = get_episode_url(filename, ep_num)
                        return full_tag.replace(url, new_ep_url)
                    return full_tag
                    
                new_content = re.compile(r'href="([^"]*\?episode=\d+|[^"]*-ep-\d+\.html)"').sub(replace_ep_link, new_content)

                # 3. Update JavaScript episodes map
                def replace_js_map(match):
                    ep_num = match.group(1)
                    new_ep_url = get_episode_url(filename, ep_num)
                    return f'"{ep_num}": "{new_ep_url}"'

                new_content = re.compile(r'"(\d+)":\s*"([^"]*)"').sub(replace_js_map, new_content)

                if content != new_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count += 1
        print(f"Done! Updated {count} files in {target_dir}.")
