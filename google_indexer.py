import os
import json
import xml.etree.ElementTree as ET
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
import time
import sys

# ==========================================
# الإعدادات (Settings)
# ==========================================
# مسار ملف Service Account
SERVICE_ACCOUNT_FILE = 'reference-fact-488823-b6-710a3997d9de.json'
SCOPES = ['https://www.googleapis.com/auth/indexing']
ENDPOINT = 'https://indexing.googleapis.com/v3/urlNotifications:publish'

# الموقع ديالنا
SITE_URL = 'https://nordrama.live'

# مسارات الـ sitemaps ديالنا
SITEMAPS = ['sitemap_root.xml', 'sitemap_tv.xml', 'sitemap_actor.xml', 'sitemap_movie.xml']
PROGRESS_FILE = 'indexer_progress.json'
LINKS_PER_RUN = 200
# ==========================================

def get_access_token():
    """كتحصل على التوكن (Access Token) باش نقدرو نصيفطو الطلب لجوجل"""
    if 'GCP_INDEXING_KEY' in os.environ:
        creds_json = json.loads(os.environ['GCP_INDEXING_KEY'])
        credentials = service_account.Credentials.from_service_account_info(
            creds_json, scopes=SCOPES)
    else:
        # التأكد من وجود ملف المفاتيح فالمكان الصحيح
        creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SERVICE_ACCOUNT_FILE)
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"❌ ملف المفاتيح غير موجود: {creds_path}")
            
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

def notify_google_index(url, type="URL_UPDATED"):
    """
    كتصيفط URL لجوجل باش يدير ليه أرشفة بالزربة
    """
    try:
        access_token = get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # التأكد باللي URL كيبدا بـ SITE_URL إيلا كان نسبي
        if url.startswith('/'):
            url = f"{SITE_URL}{url}"
        elif not url.startswith('http'):
            url = f"{SITE_URL}/{url}"
            
        data = {"url": url, "type": type}
        
        response = requests.post(ENDPOINT, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Success: {url}")
            return "SUCCESS"
        else:
            try:
                resp_json = response.json()
                error_obj = resp_json.get("error", {})
                is_rate_limit = (
                    response.status_code == 429 or 
                    error_obj.get("code") == 429 or 
                    error_obj.get("status") == "RESOURCE_EXHAUSTED"
                )
                if is_rate_limit:
                    print(f"⚠️ Rate Limit: {resp_json}")
                    return "RATE_LIMIT"
                else:
                    print(f"❌ Error | {url} | Response: {resp_json}")
                    return "ERROR"
            except Exception:
                print(f"❌ Error | {url} | HTTP {response.status_code}")
                return "ERROR"
    except Exception as e:
        print(f"❌ Exception: {e}")
        return "ERROR"

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=4)

def index_sitemaps():
    progress = load_progress()
    rate_limit_hit = False
    total_indexed_this_run = 0
    
    for sitemap_path in SITEMAPS:
        if rate_limit_hit or total_indexed_this_run >= LINKS_PER_RUN:
            break
            
        print(f"\n==========================================")
        print(f"🚀 كنقراو دابا من: {sitemap_path}")
        print(f"==========================================")
        
        if not os.path.exists(sitemap_path):
            print(f"❌ Sitemap file {sitemap_path} not found.")
            continue

        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
        except ET.ParseError:
            print(f"❌ Error parsing {sitemap_path}")
            continue
        
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls: list[str] = []
        for loc in root.findall('.//ns:loc', namespace):
            loc_text = loc.text
            if loc_text is not None:
                urls.append(loc_text)
            
        total_urls = len(urls)
        print(f"📊 طوطال الروابط اللي لقينا هنا: {total_urls}")
        
        start_index = int(progress.get(sitemap_path, 0))
        
        if start_index >= total_urls:
            print(f"✅ سالينا هاد الـ sitemap كامل! (الروابط كاملين {total_urls} صيفطناهم)")
            continue
            
        remaining_in_quota = LINKS_PER_RUN - total_indexed_this_run
        end_index = min(start_index + remaining_in_quota, total_urls)
        urls_to_index = [urls[i] for i in range(start_index, end_index)]
        
        print(f"▶️ غادي نصيفطو {len(urls_to_index)} رابط دابا (من {start_index + 1} حتى لـ {min(end_index, total_urls)})...\n")
        
        count = 0
        for url in urls_to_index:
            status = notify_google_index(url, "URL_UPDATED")
            if status == "SUCCESS":
                count += 1
                total_indexed_this_run += 1
            elif status == "RATE_LIMIT":
                rate_limit_hit = True
                break
            else:
                count += 1 # نزيدوه باش ماندوروش عليه مرة أخرى فالحالة ديال error عادي
                total_indexed_this_run += 1
            time.sleep(1)
            
        progress[sitemap_path] = start_index + count
        save_progress(progress)
        
        print(f"✅ تم الإرسال/المعالجة د {count} رابط من {sitemap_path}.")
        
    if rate_limit_hit:
         print("\n🚨 وصلنا للـ Limit ديال Google، السكريبت وقف باش مانتجاوزوش الحد.")
    elif total_indexed_this_run >= LINKS_PER_RUN:
         print(f"\n✅ وصلنا للحد اللي حددنا ({LINKS_PER_RUN} رابط). غادي نحبسو هنا باش نحتارمو الكوطا.")
    else:
         print("\n🎉 سالينا الران ديال دابا! المرة الجاية غادي يكمل اوتوماتيك منين حبسنا.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # إيلا عطينا رابط فـ command line، نصيفطوه هو بوحدو
        input_url = sys.argv[1]
        print(f"🚀 غادي نصيفطو هاد الرابط بوحدو: {input_url}")
        notify_google_index(input_url)
    else:
        # إيلا ما عطينا والو، نخدمو بالـ sitemaps العاديين
        index_sitemaps()
