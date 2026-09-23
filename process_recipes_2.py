import os
import json
import re
import time
import random
import sys
import requests
from urllib.parse import quote
from rapidfuzz import fuzz
from duckduckgo_search import DDGS

# قائمة المصطلحات والأسماء الزائدة للتنظيف (NLP Cleaning)
NOISE_PATTERNS = [
    r"\bkittencal(?:'s|\s+s)?\b",
    r"\bjo mama(?:'s|\s+s)?\b",
    r"\byes virginia(?:'s|\s+s)?\b",
    r"\bto die for\b",
    r"\bmelt in your mouth\b",
    r"\bworld\s*s\b",
    r"\bthe best\b",
    r"\bbest ever\b",
    r"\bcrock pot\b"
]

# قائمة متصفحات موسعة ومتنوعة للحد من التتبع الحسابي السحابي
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.62 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Android 14; Mobile; rv:123.0) Gecko/123.0 Firefox/123.0",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36"
]

# قائمة صور طعام حقيقية متنوعة وعالية الجودة للطوارئ فقط (تستخدم بالتدوير)
FALLBACK_FOOD_IMAGES = [
    "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?auto=format&fit=crop&w=800&q=80"
]

def clean_recipe_title(title: str) -> str:
    """تنظيف اسم الوصفة من الكلمات الزائدة والأسماء المجازية"""
    clean = title
    for pattern in NOISE_PATTERNS:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip(" -_")
    return clean.title()

def fetch_food_image(query: str) -> str:
    """جلب رابط صورة حقيقية ومطابقة عبر 3 مصادر جلب حقيقية"""
    # زيادة التأخير الزمني (من 2.5 إلى 5.0 ثوانٍ) لمنع الحظر
    time.sleep(random.uniform(2.5, 5.0))
    
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    clean_query = clean_recipe_title(query)
    encoded_query = quote(clean_query)

    # --- المصدر الأول: Wikimedia Commons API ---
    try:
        wiki_url = (
            f"https://commons.wikimedia.org/w/api.php?"
            f"action=query&generator=search&gsrnamespace=6&"
            f"gsrsearch={encoded_query}+food&gsrlimit=1&"
            f"prop=imageinfo&iiprop=url&format=json"
        )
        response = requests.get(wiki_url, headers=headers, timeout=6)
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                image_info = page_info.get("imageinfo", [])
                if image_info and "url" in image_info[0]:
                    img_url = image_info[0]["url"]
                    if img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        return img_url
    except Exception:
        pass

    # --- المصدر الثاني: Bing Image Scraping (مباشر ودقيق) ---
    try:
        bing_url = f"https://www.bing.com/images/async?q={encoded_query}+recipe+photo&first=1&count=1"
        response = requests.get(bing_url, headers=headers, timeout=6)
        if response.status_code == 200:
            murl_match = re.search(r'&quot;murl&quot;:&quot;(.*?)&quot;', response.text)
            if murl_match:
                img_url = murl_match.group(1)
                if img_url.startswith("http"):
                    return img_url
    except Exception:
        pass

    # --- المصدر الثالث: DuckDuckGo Engine ---
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{clean_query} food recipe photo", max_results=1))
            if results and "image" in results[0]:
                return results[0]["image"]
    except Exception:
        pass

    # --- المصدر الرابع (احتياطي الطوارئ بالتدوير): عند تعذر كل محركات البحث ---
    return random.choice(FALLBACK_FOOD_IMAGES)

def process_single_recipe(recipe: dict) -> dict:
    """مراجعة الوصفة وتطبيق شروط SEO و JSON-LD"""
    original_name = recipe.get("name", "")
    cleaned_name = clean_recipe_title(original_name)
    
    similarity_score = fuzz.token_set_ratio(original_name.lower(), cleaned_name.lower())
    is_matched = (similarity_score >= 90 and abs(len(original_name) - len(cleaned_name)) < 5)
    
    search_query = original_name if is_matched else cleaned_name
    image_url = fetch_food_image(search_query)
    
    new_recipe = {}
    
    if is_matched:
        for key, value in recipe.items():
            if key == "name":
                new_recipe["name"] = original_name
            else:
                new_recipe[key] = value
                
            if key == "description":
                new_recipe["image"] = [image_url]
                
        if "image" not in new_recipe:
            new_recipe["image"] = [image_url]
            
        new_recipe["keywords"] = [search_query.lower(), f"easy {search_query.lower()}", f"best {search_query.lower()}"]
        new_recipe["seo_priority"] = "high"
        new_recipe["sitemap_priority"] = 1.0
        
    else:
        for key, value in recipe.items():
            if key == "name":
                new_recipe["name"] = cleaned_name
                new_recipe["alternateName"] = original_name
            else:
                new_recipe[key] = value
                
            if key == "description":
                new_recipe["image"] = [image_url]
                
        if "image" not in new_recipe:
            new_recipe["image"] = [image_url]
            
        new_recipe["keywords"] = [cleaned_name.lower(), f"homemade {cleaned_name.lower()}"]
        new_recipe["seo_priority"] = "optimized"
        new_recipe["sitemap_priority"] = 0.8

    return new_recipe

def main():
    folder_path = "./output_recipes"
    
    if not os.path.exists(folder_path):
        print(f"❌ لم يتم العثور على المجلد: {folder_path}")
        return

    if len(sys.argv) > 1:
        try:
            target_chunk = int(sys.argv[1])
            chunks_to_process = [target_chunk]
            print(f"🎯 معالجة موجهة للملف رقم: recipes_chunk_{target_chunk}.json")
        except ValueError:
            print("❌ يرجى إدخال رقم ملف صحيح (مثال: python process_recipes_2.py 1)")
            return
    else:
        print("⚠️ لم يتم تحديد رقم ملف، سيتم معالجة الملفات (1-20) تسلسلياً...")
        chunks_to_process = list(range(1, 21))

    for chunk_num in chunks_to_process:
        file_name = f"recipes_chunk_{chunk_num}.json"
        file_path = os.path.join(folder_path, file_name)
        
        if not os.path.exists(file_path):
            print(f"⏭️ الملف {file_name} غير موجود، جاري التخطي...")
            continue
            
        print(f"🚀 جاري معالجة الملف: {file_name}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            recipes = json.load(f)
            
        updated_recipes = []
        for idx, recipe in enumerate(recipes):
            print(f"   [{idx+1}/{len(recipes)}] معالجة: {recipe.get('name', '')}")
            processed_item = process_single_recipe(recipe)
            updated_recipes.append(processed_item)
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"✅ تم الانتهاء من {file_name} بنجاح.\n")

if __name__ == "__main__":
    main()

