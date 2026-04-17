import os
import glob

def fix_css_and_favicon_links(root_dir):
    html_files = glob.glob(os.path.join(root_dir, '**', '*.html'), recursive=True)
    count = 0
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('href="style.css"', 'href="/style.css"') \
                                 .replace('href="../style.css"', 'href="/style.css"') \
                                 .replace('href="favicon.ico"', 'href="/favicon.ico"') \
                                 .replace('href="../favicon.ico"', 'href="/favicon.ico"')
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    print(f"Fixed links in {count} HTML files.")

if __name__ == '__main__':
    fix_css_and_favicon_links('/home/tomito/tomito')
