import os
import re

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIRS = ['movie', 'tv', 'actor']

GTAG_SNIPPET = """  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-PRCQVS90BX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-PRCQVS90BX');
  </script>"""

# We'll use a cleaner link and ensure no double pipes
GOOGLE_ACTIVITY_LINK = ' | <a href="https://myactivity.google.com/">Google Activity</a> |'

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. Clean up potential mess from first run (double pipes)
    if ' |  | ' in content:
        content = content.replace(' |  | ', ' | ')
        modified = True

    # 2. Inject GTAG if missing
    if 'G-PRCQVS90BX' not in content:
        # Flexible match for viewport meta tag
        pattern = r'(<meta\s+name="viewport"\s+content="[^"]+">)'
        if re.search(pattern, content, flags=re.IGNORECASE):
            content = re.sub(
                pattern,
                r'\1\n' + GTAG_SNIPPET,
                content,
                flags=re.IGNORECASE,
                count=1
            )
            modified = True
        else:
            # Fallback: after <head>
            content = re.sub(
                r'(<head>)',
                r'\1\n' + GTAG_SNIPPET,
                content,
                flags=re.IGNORECASE,
                count=1
            )
            modified = True

    # 3. Inject Google Activity Link if missing
    if 'myactivity.google.com' not in content:
        # Match "جميع الحقوق محفوظة" and append the link
        pattern = r'(جميع الحقوق محفوظة)'
        if re.search(pattern, content):
            # Ensure we don't end up with triple pipes
            content = re.sub(pattern, r'\1' + GOOGLE_ACTIVITY_LINK, content)
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    total_updated = 0
    total_files = 0

    for d in TARGET_DIRS:
        dir_path = os.path.join(BASE_DIR, d)
        if not os.path.exists(dir_path):
            continue
        
        print(f"Processing directory: {d}...")
        for filename in sorted(os.listdir(dir_path)):
            if filename.endswith('.html'):
                total_files += 1
                filepath = os.path.join(dir_path, filename)
                if update_file(filepath):
                    total_updated += 1
                    if total_updated % 500 == 0:
                        print(f"Updated {total_updated} files...")

    print(f"Done! Updated {total_updated} out of {total_files} files.")

if __name__ == "__main__":
    main()
