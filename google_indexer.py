import os
import json
import xml.etree.ElementTree as ET
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
import time

# ==========================================
# الإعدادات (Settings)
# ==========================================
# مسار ملف Service Account
SERVICE_ACCOUNT_FILE = 'reference-fact-488823-b6-710a3997d9de.json'
SCOPES = ['https://www.googleapis.com/auth/indexing']
ENDPOINT = 'https://indexing.googleapis.com/v3/urlNotifications:publish'

# مسار الـ sitemap ديالك (مثلاً sitemap_movie.xml)
SITEMAP_FILE = 'sitemap_movie.xml' 
# ==========================================

def get_access_token():
    """كتحصل على التوكن (Access Token) باش نقدرو نصيفطو الطلب لجوجل"""
    if 'GCP_INDEXING_KEY' in os.environ:
        creds_json = json.loads(os.environ['GCP_INDEXING_KEY'])
        credentials = service_account.Credentials.from_service_account_info(
            creds_json, scopes=SCOPES)
    else:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

def notify_google_index(url, type="URL_UPDATED"):
    """
    كتصيفط URL لجوجل باش يدير ليه أرشفة بالزربة
    type="URL_UPDATED" : يلا كان رابط جديد ولا درتي فيه تعديل
    type="URL_DELETED" : يلا بغيتي تمسحو من جوجل
    """
    try:
        access_token = get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        data = {"url": url, "type": type}
        
        response = requests.post(ENDPOINT, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Success (تمت الأرشفة بنجاح): {url}")
            return True
        else:
            print(f"❌ Error (خطأ في {url}): {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def index_urls_from_sitemap(sitemap_path, limit=100):
    """كتقرا الروابط من فايل sitemap وكتصيفطهم لجوجل (Google Indexing API limit هو 200 في النهار عادة)"""
    if not os.path.exists(sitemap_path):
        print(f"Sitemap file {sitemap_path} not found.")
        return

    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    
    # حيت الـ sitemap كيكون فيه namespace
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    urls = []
    for loc in root.findall('.//ns:loc', namespace):
        urls.append(loc.text)
        
    print(f"طوطال الروابط اللي لقينا: {len(urls)}")
    print(f"غادي نصيفطو {limit} رابط دابا...\n")
    
    count = 0
    for url in urls[:limit]:
        success = notify_google_index(url, "URL_UPDATED")
        if success:
            count += 1
        # باش ما نبلوكيوش السيرفر ديال جوجل كديرو pause صغير
        time.sleep(1)
        
    print(f"\nسالينا! تم إرسال {count} رابط لجوجل باش يطّلع في محرك البحث بالزربة.")

if __name__ == "__main__":
    # هنا تقدر تختار واش تصيفط سيت ماب كامل أو رابط واحد
    # باش نجربو، غدي نصيفطو روابط من sitemap_movie.xml (بدل limit يلا بغيتي أكثر)
    index_urls_from_sitemap(SITEMAP_FILE, limit=10)
    
    # يلا بغيتي تصيفط رابط واحد ديراكت:
    # notify_google_index("https://yourdomain.com/movie/test-movie.html", "URL_UPDATED")
