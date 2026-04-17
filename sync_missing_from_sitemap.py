import os
import re
import xml.etree.ElementTree as ET

BASE_PATH = "/home/tomito/tomito"
SITEMAPS = [
    "sitemap_movie.xml",
    "sitemap_tv.xml",
    "sitemap_actor.xml",
    "sitemap_trend.xml",
    "sitemap_genre.xml"
]

def get_missing_from_sitemaps():
    missing_entries = []
    
    for sitemap in SITEMAPS:
        path = os.path.join(BASE_PATH, sitemap)
        if not os.path.exists(path):
            continue
            
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            
            # Namespace for sitemaps
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url in root.findall('sm:url', ns):
                loc = url.find('sm:loc', ns)
                if loc is not None:
                    full_url = loc.text
                    # Extract relative path (e.g., movie/123-title or movie/123-title.html)
                    # The sitemaps currently don't have .html extension in URLs
                    rel_path = full_url.replace("https://nordrama.live/", "").strip("/")
                    
                    if not rel_path:
                        continue
                        
                    # Check if file exists with .html extension
                    target_file = os.path.join(BASE_PATH, f"{rel_path}.html")
                    
                    if not os.path.exists(target_file):
                        # Format for missing_similar.txt is: type,slug
                        if "/" in rel_path:
                            m_type, slug = rel_path.split("/", 1)
                            # Only handle movie and tv for now as gen_missing.py supports them
                            if m_type in ["movie", "tv"]:
                                missing_entries.append(f"{m_type},{slug}")
        except Exception as e:
            print(f"Error parsing {sitemap}: {e}")
            
    return missing_entries

if __name__ == "__main__":
    missing = get_missing_from_sitemaps()
    print(f"Found {len(missing)} missing pages from sitemaps.")
    
    if missing:
        output_file = os.path.join(BASE_PATH, "missing_similar.txt")
        # Backup old file
        if os.path.exists(output_file):
            os.rename(output_file, output_file + ".bak")
            
        with open(output_file, "w") as f:
            for entry in missing:
                f.write(entry + "\n")
        print(f"Updated {output_file} with {len(missing)} entries.")
    else:
        print("No missing pages detected.")
