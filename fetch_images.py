import os
import json
import argparse
import time
import urllib.parse
import requests
from duckduckgo_search import DDGS

def get_duckduckgo_image(query):
    """المصدر الأول (أعلى دقة): DuckDuckGo HD"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} recipe food photo", max_results=3))
            for res in results:
                img_url = res.get('image')
                if img_url and img_url.startswith('http'):
                    return img_url
    except Exception:
        pass
    return None

def get_wikimedia_image(query):
    """المصدر الثاني (احتياطي): Wikimedia Commons"""
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
    """البحث باستخدام الاسم الأساسي والأسماء البديلة"""
    primary_name = recipe.get("name", "").strip()
    alt_names = recipe.get("alternativeNames", [])
    
    if isinstance(alt_names, str):
        alt_names = [alt_names]

    search_queries = [primary_name] + [alt.strip() for alt in alt_names if alt and isinstance(alt, str)]

    for query in search_queries:
        if not query:
            continue

        img_url = get_duckduckgo_image(query)
        if img_url:
            return img_url, f"DuckDuckGo ('{query}')"

        img_url = get_wikimedia_image(query)
        if img_url:
            return img_url, f"Wikimedia ('{query}')"

    return "", "لا توجد صورة"

def insert_image_below_description(recipe, img_url):
    """إعادة ترتيب عناصر الوصفة لضمان وضع حقل image أسفل description مباشرة"""
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

            # إذا كانت الصورة موجودة وصالحة، يُعاد ترتيب الحقول فقط
            if existing_img and isinstance(existing_img, str) and existing_img.startswith("http"):
                print(f"  🔹 [{idx}/{total_recipes}] '{name}' تحتوي على صورة صالحة بالفعل.", flush=True)
                updated_recipes.append(insert_image_below_description(recipe, existing_img))
                continue

            img_url, source = process_single_recipe(recipe)

            if img_url:
                print(f"  ✅ [{idx}/{total_recipes}] '{name}' ➜ [{source}] ➜ {img_url[:50]}...", flush=True)
            else:
                print(f"  ⚠️ [{idx}/{total_recipes}] '{name}' ➜ لم تُعثر صورة (تم ترك الحقل فارغاً)", flush=True)

            updated_recipe = insert_image_below_description(recipe, img_url)
            updated_recipes.append(updated_recipe)

            time.sleep(0.4)

        time.sleep(1.0)

    # حفظ النتيجة والتحديث مباشرة على نفس الملف داخل output_recipes_seo
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 [السيرفر #{chunk_id}] تم تحديث الملف بنجاح: {target_file}", flush=True)

if __name__ == "__main__":
    main()
