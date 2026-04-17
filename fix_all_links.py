import os
import glob
import re

def main():
    root_dir = '/home/tomito/tomito'
    count = 0
    folders = ['genre', 'movie', 'tv', 'actor', 'movie-trend', 'tv-trend']
    
    # regex compilation
    patterns = []
    for folder in folders:
        # Match href="/folder/slug" not ending in .html
        pattern = re.compile(r'href="\/' + folder + r'\/([^"]+)"')
        patterns.append((folder, pattern))

    for root, dirs, files in os.walk(root_dir):
        # Exclude hidden directories explicitly, and specific paths
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.endswith('.html'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                rel_path = os.path.relpath(file_path, root_dir)
                depth = len(rel_path.split(os.sep)) - 1
                
                prefix = "./" if depth == 0 else "../" * depth

                new_content = content \
                    .replace('href="/style.css"', f'href="{prefix}style.css"') \
                    .replace('href="style.css"', f'href="{prefix}style.css"') \
                    .replace('href="/favicon.ico"', f'href="{prefix}favicon.ico"') \
                    .replace('href="favicon.ico"', f'href="{prefix}favicon.ico"') \
                    .replace("src='/favicon.ico'", f"src='{prefix}favicon.ico'") \
                    .replace('src="/favicon.ico"', f'src="{prefix}favicon.ico"') \
                    .replace('src="/logo.png"', f'src="{prefix}logo.png"') \
                    .replace('href="index.html"', f'href="{prefix}index.html"') \
                    .replace('href="/index.html"', f'href="{prefix}index.html"')
                
                # Replace links
                for folder, pattern in patterns:
                    def repl(match):
                        slug = match.group(1)
                        if slug.endswith('.html'):
                            return f'href="{prefix}{folder}/{slug}"'
                        return f'href="{prefix}{folder}/{slug}.html"'
                    
                    new_content = pattern.sub(repl, new_content)

                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count += 1
            except Exception as e:
                print(f"Error on {file_path}: {e}")

    print(f"Fixed links in {count} HTML files.")

if __name__ == '__main__':
    main()
