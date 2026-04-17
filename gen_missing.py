import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from mega_bot import fetch_details, clean_slug, build_keywords, MASTER_TEMPLATE, IMAGE_BASE_URL, SITE_URL, BUTTON_DOMAIN

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(BASE_PATH, 'data', 'content_index.json')
all_index = []
if os.path.exists(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        all_index = json.load(f)

def create_long_page(item_data, media_type, custom_slug=None):
    ar, en, credits = item_data['ar'], item_data['en'], item_data['credits']
    if not ar and not en:
        return None, None

    data = ar or en
    title_ar = (ar.get('title') or ar.get('name') or '') if ar else ''
    title_en = (en.get('title') or en.get('name') or '') if en else ''
    if not title_ar: title_ar = title_en
    if not title_en: title_en = title_ar
    tmdb_id = data.get('id')
    
    slug = custom_slug
    if not slug:
        s = clean_slug(title_en) or f"{media_type}-{tmdb_id}"
        if media_type == 'movie' or 'tv' in media_type:
            slug = f"{tmdb_id}-{s}"

    poster_path = data.get('poster_path') or (en.get('poster_path') if en else None) or (ar.get('poster_path') if ar else None)
    if not poster_path:
        return None, None
    poster_url = f"{IMAGE_BASE_URL}{poster_path}"
    year = (data.get('release_date') or data.get('first_air_date') or '2026')[:4]
    rating = round(data.get('vote_average', 0), 1)
    rating_count = data.get('vote_count', 1)
    if not rating_count or rating_count == 0: rating_count = 1

    genres_ar = [g.get('name', '') for g in (ar.get('genres', []) if ar else [])]
    genres_en = [g.get('name', '') for g in (en.get('genres', []) if en else [])]

    ar_overview = (ar.get('overview', '') if ar else '')
    en_overview = (en.get('overview', '') if en else '')
    
    seo_ar_text = f"مشاهدة وتحميل {title_ar} ({year}) اون لاين بجودة عالية HD مترجم حصرياً بدون اعلانات."
    seo_en_text = f"Watch and download online in HD quality. Free streaming with English subtitles {year}."
    
    desc_ar = f"{ar_overview}\n\n{seo_ar_text}".strip()
    desc_en = f"{en_overview}\n\n{seo_en_text}".strip()
    if len(desc_ar) < 100:
        desc_ar = f"قصة {title_ar}: تابعوا أحداث هذه القصة الممتعة والمثيرة للاهتمام. {seo_ar_text} متوفر الآن للمشاهدة المباشرة والتحميل السريع بجودة فائقة الدقة."
    if len(desc_en) < 100:
        desc_en = f"Story of {title_en}: Follow this captivating and exciting journey. {seo_en_text} Available now for fast direct download and high definition stream without any interruptions."

    if media_type == 'movie':
        watch_url = "#player"
        folder = 'movie'
        schema_type = 'Movie'
        type_label = "Movie | فيلم"
    elif 'anime' in media_type:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv'
        schema_type = 'TVSeries'
        type_label = "Anime | أنمي"
    else:
        watch_url = f"{SITE_URL}/tv/{tmdb_id}/watch?season=1&episode=1"
        folder = 'tv'
        schema_type = 'TVSeries'
        type_label = "TV Series | مسلسل"

    page_url = f"{SITE_URL}/{folder}/{slug}"
    keywords = build_keywords(title_ar, title_en, media_type, year, genres_ar)

    similar_html = ''
    similar_data = item_data.get('similar', {})
    if similar_data and similar_data.get('results'):
        section_title = "أفلام مشابهة — Similar Movies" if media_type == 'movie' else "مسلسلات مشابهة — Similar Series"
        similar_html = f'<section class="section"><h2 class="section-title">{section_title}</h2><div class="grid">'
        for sim in similar_data['results'][:12]:
            s_id = sim.get('id', '')
            s_title = sim.get('title') or sim.get('name') or ''
            s_poster = sim.get('poster_path', '')
            if not s_poster: continue
            poster_src = f"{IMAGE_BASE_URL}{s_poster}"
            s_slug_part = clean_slug(s_title)
            s_slug = f"{s_id}-{s_slug_part}" if s_slug_part else str(s_id)
            s_year = (sim.get('release_date') or sim.get('first_air_date') or '')[:4]
            s_rating = round(sim.get('vote_average', 0), 1)
            s_badge = f"{s_rating}⭐" if s_rating else s_year
            
            similar_html += f'    <a class="card" href="/{folder}/{s_slug}">\n      <img class="card-poster" src="{poster_src}" alt="{s_title} — مشاهدة وتحميل اون لاين" loading="lazy" onerror="this.src=\'favicon.ico\'">\n      <div class="card-overlay"><div class="card-meta">{s_badge}</div></div>\n      <div class="card-bottom"><div class="card-title">{s_title}</div></div>\n    </a>'
        similar_html += '</div></section>'

    tags = [type_label, f"⭐ {rating}", year] + genres_en[:3]
    tags_html = '<div class="series-tags">' + ''.join(f'<span class="tag">{t}</span>' for t in tags) + '</div>'

    html = MASTER_TEMPLATE
    replacements = {
        '{{TITLE_PAGE}}': f'{title_ar} — مشاهدة وتحميل {year} | TOMITO',
        '{{META_DESC}}': f'مشاهدة وتحميل {title_ar} ({title_en}) {year} اون لاين بجودة HD. {desc_ar[:150]}',
        '{{KEYWORDS}}': keywords,
        '{{TITLE_OG}}': f'{title_ar} / {title_en} — TOMITO',
        '{{OG_TYPE}}': 'video.movie' if media_type == 'movie' else 'video.tv_show',
        '{{POSTER_URL}}': poster_url,
        '{{PAGE_URL}}': page_url,
        '{{BUTTON_URL}}': f"{BUTTON_DOMAIN}/{folder}/{slug}",
        '{{WATCH_URL}}': watch_url,
        '{{TITLE_AR}}': title_ar,
        '{{TITLE_EN}}': title_en,
        '{{DESC_AR}}': desc_ar.replace("\\n", "<br>"),
        '{{DESC_EN}}': desc_en.replace("\\n", "<br>"),
        '{{TAGS_SECTION}}': tags_html,
        '{{EXTRA_CONTENT}}': similar_html,
        '{{JSON_LD}}': '<script>{}</script>',
        '{{FOLDER}}': folder,
        '{{TYPE_AR}}': type_label.split('|')[-1].strip(),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    path = os.path.join(BASE_PATH, folder, f"{slug}.html")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    index_entry = {
        'title': f"{title_ar} / {title_en}" if title_ar != title_en else title_ar,
        'title_ar': title_ar,
        'title_en': title_en,
        'slug': slug,
        'folder': folder,
        'poster': poster_url,
        'rating': rating,
        'year': year,
        'type': media_type,
        'tmdb_id': tmdb_id,
        'genres': genres_en,
    }
    return f"{folder}/{slug}", index_entry

def process_item(m_type, slug, all_index, lock):
    try:
        tmdb_id = slug.split('-')[0]
        if not tmdb_id.isdigit(): return None
        
        details = fetch_details(tmdb_id, 'movie' if m_type == 'movie' else 'tv')
        if not details or (not details['ar'] and not details['en']):
            return None
        
        url, index_entry = create_long_page(details, m_type, custom_slug=slug)
        if url and index_entry:
            with lock:
                all_index.append(index_entry)
            return url
    except Exception:
        return None
    return None

import threading
def main():
    with open("missing_similar.txt", "r") as f:
        lines = f.read().splitlines()
    
    generated = 0
    errors = 0
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = []
        for line in lines:
            if ',' not in line: continue
            m_type, slug = line.split(',', 1)
            # check if it was processed already in previous interrupted run
            if os.path.exists(os.path.join(BASE_PATH, m_type, f"{slug}.html")):
                continue
            futures.append(ex.submit(process_item, m_type, slug, all_index, lock))
            
        print(f"Submitted {len(futures)} tasks to executor...")
        for future in as_completed(futures):
            res = future.result()
            if res:
                generated += 1
                if generated % 50 == 0:
                    print(f"Generated {generated} pages...")
            else:
                errors += 1
    
    print(f"Successfully generated {generated} missing pages. Errors: {errors}")
    if generated > 0:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(all_index, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
