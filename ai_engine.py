import requests
import json
import time
from datetime import datetime

# --- Configuration ---
OPENROUTER_KEY = "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"

MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "arcee-ai/trinity-large-preview:free",
    "z-ai/glm-4.5-air:free",
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "minimax/minimax-m2.5:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-20b:free",
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "google/gemma-3-27b-it:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "google/gemma-3n-e2b-it:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-guard-4-12b:free"
]

# AI Keywords to avoid and their human-like alternatives
FORBIDDEN_PATTERNS = {
    # Transitions
    "Moreover": "Also",
    "Furthermore": "Plus",
    "Nevertheless": "But",
    "In light of this": "So",
    "Consequently": "As a result",
    "علاوة على ذلك": "وزيد عليها",
    "بالإضافة إلى ما سبق": "وحاجة أخرى",
    "ومع ذلك": "ولكن",
    
    # Adjectives
    "Cutting-edge": "New",
    "Unparalleled": "Unique",
    "Robust": "Strong",
    "Seamless": "Easy",
    "Transformative": "Great",
    "متطور للغاية": "جديد",
    "لا مثيل له": "ماكاينش بحالو",
    "قوي ومتين": "صحيحة",
    
    # Openers
    "In today’s fast-paced world": "Nowadays",
    "It is worth noting that": "Just so you know",
    "Look no further": "Check this",
    "The journey begins with": "First",
    "في عالمنا المتسارع اليوم": "فهاد الوقت",
    "وتجدر الإشارة إلى أن": "خاصك تعرف",
    
    # Filler Verbs
    "Delve into": "Look at",
    "Leverage": "Use",
    "Foster": "Help",
    "Unlock the potential": "Show",
    "التعمق في": "نشوفو",
    "الاستفادة من": "خدم بـ",
    
    # Conclusions
    "In summary": "Overall",
    "Ultimately": "Finally",
    "In essence": "Basically",
    "To wrap up": "That's it",
    "باختصار شديد": "المهم",
    "في نهاية المطاف": "فالاخر"
}

def get_current_model():
    """Selects a model based on the current day to ensure 'each bot works on its own day'."""
    day_of_year = datetime.now().timetuple().tm_yday
    index = day_of_year % len(MODELS)
    return MODELS[index]

def clean_ai_text(text):
    """Replaces forbidden AI patterns with human-like alternatives."""
    if not text: return ""
    cleaned = text
    for ai_pattern, human_pattern in FORBIDDEN_PATTERNS.items():
        # Case insensitive replacement for English keys
        if any(c.isalpha() for c in ai_pattern):
            import re
            cleaned = re.sub(re.escape(ai_pattern), human_pattern, cleaned, flags=re.IGNORECASE)
        else:
            cleaned = cleaned.replace(ai_pattern, human_pattern)
    return cleaned

def generate_seo_content(title, overview, media_type):
    """Generates SEO title and description using OpenRouter with model rotation."""
    model = get_current_model()
    ar_type = "فيلم" if media_type == 'movie' else "مسلسل"
    
    # Detailed prompt to enforce all user constraints
    prompt = f"""
أنت خبير SEO عبقري لموقع (nordrama.live). مهمتك هي إنشاء محتوى وصفي طويل واحترافي لـ {ar_type}: '{title}'.
الأصل: {overview}.

القواعد الصارمة:
1. الطول: يجب أن يكون الوصف طويلاً جداً (أكثر من 150 كلمة). لا تقبل بأقل من ذلك.
2. اللغة: استخدم مزيجاً احترافياً من العربية والإنجليزية (Bilingual). ابدأ بالعربية ثم انتقل للإنجليزية بسلاسة.
3. المنهج البشري: اكتب بأسلوب مدون حقيقي، تجنب الأسلوب الآلي والكلمات التقنية الجافة.
4. الممنوعات: ممنوع استخدام الكلمات التالية (Moreover, Furthermore, Nevertheless, Cutting-edge, Seamless, Robust, In summary, Ultimately, علاوة على ذلك، بالإضافة إلى، في عالمنا المتسارع، باختصار).
5. التنسيق: أجب بصيغة JSON فقط. لا تستخدم Bold (**) ولا جداول ولا نقاط. فقط نص خام داخل الـ JSON.

الهيكل المطلوب في الـ JSON:
{{
  "seo_title": "عنوان جذاب جداً مع كلمات دلالية",
  "ai_description": "وصف طويل (150+ كلمة) يجمع بين القصة والجودة وروابط المشاهدة بشكل نصي جذاب",
  "keywords": "15 كلمة مفتاحية مفصولة بفواصل"
}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional SEO expert for a media website. You write in a human-like, non-robotic tone. You return results in JSON format only."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            # Clean possible markdown code blocks
            content = content.replace('```json', '').replace('```', '').strip()
            data = json.loads(content)
            
            # Apply keyword filtering to description
            data['ai_description'] = clean_ai_text(data['ai_description'])
            return data
        else:
            print(f"OpenRouter Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"AI Generation Exception: {e}")
        return None

if __name__ == "__main__":
    # Test
    print(f"Current Model for today: {get_current_model()}")
    test_res = generate_seo_content("The Last of Us", "A survival story in a post-apocalyptic world.", "tv")
    print(json.dumps(test_res, indent=2, ensure_ascii=False))
