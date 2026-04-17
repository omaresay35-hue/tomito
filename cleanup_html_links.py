import os
import re

def main():
    root_dir = '/home/tomito/tomito'
    count = 0
    html_link_pattern = re.compile(r'href="((?!\s*http|\s*https|\s*//)[^"]+)\.html(#?[^"]*)"')

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.endswith('.html'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                new_content = re.sub(r'href="([^"]*)index\.html(#?[^"]*)"', r'href="\1\2"', content)
                new_content = html_link_pattern.sub(r'href="\1\2"', new_content)

                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count += 1
                    if count % 1000 == 0:
                        print(f"Processed {count} files...")
            except Exception as e:
                print(f"Error on {file_path}: {e}")

    print(f"Successfully cleaned up links in {count} HTML files.")

if __name__ == '__main__':
    main()
