import os
import json
import re
import time
import random
import sys
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

# متصفحات متناوبة لتجنب كشف البوتات (Rotating User-Agents)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
]

def clean_recipe_title(title: str) -> str:
    """تنظيف اسم الوصفة من الكلمات الزائدة والأسماء المجازية"""
    clean = title
    for pattern in NOISE_PATTERNS:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip(" -_")
    return clean.title()

def fetch_food_image(query: str) -> str:
    """جلب رابط صورة عالية الجودة مع تأخير زمني متغير وتدوير الطلبات"""
    # تأخير زمني متغير بين 1.2 إلى 3.5 ثانية لتجنب حظر الـ IP
    time.sleep(random.uniform(1.2, 3.5))
    
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} food recipe photo", max_results=3))
            if results and "image" in results[0]:
                return results[0]["image"]
    except Exception as e:
        print(f"⚠️ تعذر جلب صورة للـ ({query}): {e}")
    
    # رابط احتياطي عالي الجودة في حالة حدوث Rate Limit مؤقت
    return "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80"

def process_single_recipe(recipe: dict) -> dict:
    """مراجعة الوصفة وتطبيق شروط SEO و JSON-LD حسب الجدول"""
    original_name = recipe.get("name", "")
    cleaned_name = clean_recipe_title(original_name)
    
    # حساب نسبة التشابه بين الاسم الأصلي والاسم المنظف
    similarity_score = fuzz.token_set_ratio(original_name.lower(), cleaned_name.lower())
    
    # شرط المطابقة: إذا كان الاسم أصلاً خالي من الزوائد ومتداول مباشرة
    is_matched = (similarity_score >= 90 and abs(len(original_name) - len(cleaned_name)) < 5)
    
    search_query = original_name if is_matched else cleaned_name
    image_url = fetch_food_image(search_query)
    
    new_recipe = {}
    
    if is_matched:
        # --- حالة المطابقة (Matched) ---
        for key, value in recipe.items():
            if key == "name":
                new_recipe["name"] = original_name
            else:
                new_recipe[key] = value
                
            # إدراج رابط الصورة مباشرة تحت حقل description
            if key == "description":
                new_recipe["image"] = [image_url]
                
        if "image" not in new_recipe:
            new_recipe["image"] = [image_url]
            
        new_recipe["keywords"] = [search_query.lower(), f"easy {search_query.lower()}", f"best {search_query.lower()}"]
        new_recipe["seo_priority"] = "high"
        new_recipe["sitemap_priority"] = 1.0
        
    else:
        # --- حالة عدم المطابقة (Not Matched) ---
        for key, value in recipe.items():
            if key == "name":
                new_recipe["name"] = cleaned_name  # العنوان المحسن الشائع
                new_recipe["alternateName"] = original_name  # العنوان الأصلي الغريب
            else:
                new_recipe[key] = value
                
            # إدراج رابط الصورة مباشرة تحت حقل description
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

    # قراءة رقم الملف من سطر الأوامر (تحديد العمليات لـ GitHub Actions Matrix)
    if len(sys.argv) > 1:
        try:
            target_chunk = int(sys.argv[1])
            chunks_to_process = [target_chunk]
            print(f"🎯 معالجة موجهة للملف رقم: recipes_chunk_{target_chunk}.json")
        except ValueError:
            print("❌ يرجى إدخال رقم ملف صحيح (مثال: python process_recipes.py 1)")
            return
    else:
        # خيار احتياطي: تشغيل كلي تسلسلي في حال التشغيل المحلي دون تحديد ملف
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
            
        # إعادة حفظ الملف المعدل
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"✅ تم الانتهاء من {file_name} بنجاح.\n")

if __name__ == "__main__":
    main()

