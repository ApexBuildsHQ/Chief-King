import os
import json
import argparse
import time
import re
import urllib.parse
import requests

# معالجة التحديث الجديد لاسم مكتبة DuckDuckGo
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

def clean_recipe_name(name):
    """تنظيف اسم الوصفة من العلامات التجارية والكلمات الزائدة لزيادة نسبة الحصول على صورة"""
    cleaned = re.sub(r'(?i)\b(copycat|cheesecake factory|chick fil a|mcdonalds|starbucks|olive garden|applebees)\b', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else name

def get_duckduckgo_image(query):
    """المصدر الأول: DuckDuckGo HD مع معالجة الحظر وإعادة المحاولة"""
    for attempt in range(2):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(f"{query} food photo", max_results=3))
                for res in results:
                    img_url = res.get('image')
                    if img_url and isinstance(img_url, str) and img_url.startswith('http'):
                        return img_url
        except Exception:
            time.sleep(1.5)  # مهلة زمنية قصيرة عند وجود ضغط على السيرفر
    return None

def get_wikimedia_image(query):
    """المصدر الثاني: Wikimedia Commons"""
    try:
        url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&prop=pageimages&pithumbsize=800&format=json&gsrsearch={urllib.parse.quote(query)}"
        headers = {"User-Agent": "ChiefKingApp/1.0 (contact@chiefking.com)"}
        res = requests.get(url, timeout=5, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    except Exception:
        pass
    return None

def process_single_recipe(recipe):
    primary_name = recipe.get("name", "").strip()
    alt_names = recipe.get("alternativeNames", [])
    
    if isinstance(alt_names, str):
        alt_names = [alt_names]

    # إعداد خيارات البحث: الاسم الرئيسي ➜ الاسم المنظف ➜ الأسماء البديلة
    cleaned_name = clean_recipe_name(primary_name)
    search_queries = [primary_name]
    
    if cleaned_name != primary_name:
        search_queries.append(cleaned_name)
        
    search_queries.extend([alt.strip() for alt in alt_names if alt and isinstance(alt, str)])

    for query in search_queries:
        if not query:
            continue

        # 1. التجربة عبر DuckDuckGo
        img_url = get_duckduckgo_image(query)
        if img_url:
            return img_url, f"DuckDuckGo ('{query}')"

        # 2. التجربة عبر Wikimedia
        img_url = get_wikimedia_image(query)
        if img_url:
            return img_url, f"Wikimedia ('{query}')"

    return "", "لا توجد صورة"

def insert_image_below_description(recipe, img_url):
    """إعادة ترتيب الحقول لوضع حقل image أسفل description مباشرة"""
    recipe_clean = {k: v for k, v in recipe.items() if k != "image"}
    new_recipe = {}
    inserted = False

    for key, val in recipe_clean.items():
        new_recipe[key] = val
        if key == "description":
            new_recipe["image"] = img_url
            inserted = True

    if not inserted:
        new_recipe["image"] = img_url

    return new_recipe

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk", type=int, required=True, help="رقم الجزء من 1 إلى 20")
    args = parser.parse_args()

    chunk_id = args.chunk
    target_file = f"output_recipes_seo/recipes_chunk_{chunk_id}.json"

    if not os.path.exists(target_file):
        print(f"❌ [السيرفر #{chunk_id}] الملف غير موجود: {target_file}", flush=True)
        return

    with open(target_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    total_recipes = len(recipes)
    print(f"🚀 [السيرفر #{chunk_id}] بدء المعالجة لـ {total_recipes} وصفة داخل المجلد 'output_recipes_seo'...", flush=True)

    batch_size = 5
    updated_recipes = []

    for i in range(0, total_recipes, batch_size):
        batch = recipes[i:i + batch_size]
        print(f"\n📦 [السيرفر #{chunk_id}] الدفعة {i//batch_size + 1} ({i+1} إلى {min(i+batch_size, total_recipes)}):", flush=True)

        for idx, recipe in enumerate(batch, start=i+1):
            name = recipe.get("name", "غير معروف")
            existing_img = recipe.get("image", "")

            # التخطي في حال وجود صورة صالحة مقدماً
            if existing_img and isinstance(existing_img, str) and existing_img.startswith("http"):
                print(f"  🔹 [{idx}/{total_recipes}] '{name}' تحتوي على صورة صالحة بالفعل.", flush=True)
                updated_recipes.append(insert_image_below_description(recipe, existing_img))
                continue

            img_url, source = process_single_recipe(recipe)

            if img_url:
                print(f"  ✅ [{idx}/{total_recipes}] '{name}' ➜ [{source}] ➜ {img_url[:50]}...", flush=True)
            else:
                print(f"  ⚠️ [{idx}/{total_recipes}] '{name}' ➜ لم تُعثر صورة", flush=True)

            updated_recipe = insert_image_below_description(recipe, img_url)
            updated_recipes.append(updated_recipe)

            time.sleep(0.8)  # فاصل زمني لمنع الحظر

        time.sleep(1.5)  # فاصل زمني بين كل دفعة ودفعة

    # حفظ وتعديل نفس الملف مباشرة داخل المجلد
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 [السيرفر #{chunk_id}] تم تحديث الملف بنجاح: {target_file}", flush=True)

if __name__ == "__main__":
    main()
