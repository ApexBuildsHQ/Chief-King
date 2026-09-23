import os
import json
import re
import time
import random
import sys
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
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

# قائمة متصفحات موسعة للحد من التتبع
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

def clean_recipe_title(title: str) -> str:
    """تنظيف اسم الوصفة من الكلمات الزائدة والأسماء المجازية"""
    clean = title
    for pattern in NOISE_PATTERNS:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip(" -_")
    return clean.title()

def fetch_food_image(query: str) -> str:
    """جلب رابط صورة حقيقية ومطابقة عبر المصادر الثلاثة فقط دون أي صور جاهزة"""
    time.sleep(random.uniform(1.0, 2.2))
    
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
                        print(f"   ✅ [Wikimedia] تم جلب صورة لـ: ({clean_query})")
                        return img_url
    except Exception:
        pass

    # --- المصدر الثاني: Bing Image Engine ---
    try:
        bing_url = f"https://www.bing.com/images/async?q={encoded_query}+recipe+photo&first=1&count=1"
        response = requests.get(bing_url, headers=headers, timeout=6)
        if response.status_code == 200:
            murl_match = re.search(r'&quot;murl&quot;:&quot;(.*?)&quot;', response.text)
            if murl_match:
                img_url = murl_match.group(1)
                if img_url.startswith("http"):
                    print(f"   ✅ [Bing] تم جلب صورة لـ: ({clean_query})")
                    return img_url
    except Exception:
        pass

    # --- المصدر الثالث: DuckDuckGo Engine ---
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{clean_query} food recipe photo", max_results=1))
            if results and "image" in results[0]:
                print(f"   ✅ [DuckDuckGo] تم جلب صورة لـ: ({clean_query})")
                return results[0]["image"]
    except Exception:
        pass

    # عند فشل جميع المصادر: لا يتم استخدام أي صور جاهزة أو وهمية
    print(f"   ⚠️ [لم يتم العثور] تعذر جلب صورة لـ: ({clean_query}) من المصادر الثلاثة.")
    return ""

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
                
            if key == "description" and image_url:
                new_recipe["image"] = [image_url]
                
        if "image" not in new_recipe and image_url:
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
                
            if key == "description" and image_url:
                new_recipe["image"] = [image_url]
                
        if "image" not in new_recipe and image_url:
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
            
        updated_recipes = [None] * len(recipes)
        BATCH_SIZE = 5  # معالجة 5 وصفات بالتوازي لتسريع العملية ومنع التعارض

        for i in range(0, len(recipes), BATCH_SIZE):
            batch = recipes[i:i + BATCH_SIZE]
            print(f"\n⚡ جاري معالجة الدفعة [{i+1} إلى {min(i+BATCH_SIZE, len(recipes))}] من أصل {len(recipes)} وصفة...")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # ربط كل وظيفة بالفهرس الخاص بها لمنع التداخل والدمج الخاطئ
                future_to_idx = {
                    executor.submit(process_single_recipe, recipe): i + idx 
                    for idx, recipe in enumerate(batch)
                }
                
                for future in future_to_idx:
                    original_idx = future_to_idx[future]
                    try:
                        processed_item = future.result()
                        updated_recipes[original_idx] = processed_item
                    except Exception as e:
                        print(f"❌ خطأ أثناء معالجة الوصفة رقم {original_idx + 1}: {e}")
                        updated_recipes[original_idx] = recipes[original_idx]

        # تصفية أي عناصر فارغة إن وجدت
        final_recipes = [r for r in updated_recipes if r is not None]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ تم الانتهاء من حفظ {file_name} بنجاح.\n")

if __name__ == "__main__":
    main()

