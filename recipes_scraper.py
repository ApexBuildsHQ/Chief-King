import os
import re
import json
import ast
import time
import random
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# 1. قائمة User-Agents متنوعة للتنقل بين الطلبات لتفادي الحظر
# ---------------------------------------------------------
USER_AGENTS = [
    "ChiefKingRecipeApp/1.0 (https://chefking.app; contact@chefking.app)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "FoodRecipeBot/2.0 (OpenSource Recipe Aggregator)"
]

# ---------------------------------------------------------
# 2. تنظيف وتنسيق عناوين الوصفات لـ SEO
# ---------------------------------------------------------
def clean_title_for_seo(title: str) -> str:
    if not isinstance(title, str):
        return "Delicious Recipe"
    
    stop_patterns = [
        r"\bmy\b", r"\bmom'?s\b", r"\bmother'?s\b", r"\bgrandma'?s\b", 
        r"\baunt\b", r"\bauntie'?s\b", r"\buncle'?s\b", r"\bby\s+\w+\b",
        r"\bsecret\b", r"\bfamous\b", r"\bworld'?s\b\s*\bbest\b"
    ]
    
    cleaned = title.lower()
    for pattern in stop_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() if cleaned else title.title()

# ---------------------------------------------------------
# 3. جلب الصور الحقيقية فقط من Wikimedia API
# ---------------------------------------------------------
def fetch_wikimedia_image(recipe_name: str) -> tuple:
    """جلب صورة دقيقة للوجبة من Wikimedia Commons API بدون أي روابط افتراضية"""
    clean_name = clean_title_for_seo(recipe_name)
    
    # تأخير زمني عشوائي تفادياً للـ Rate Limit
    sleep_time = random.uniform(0.15, 0.40)
    time.sleep(sleep_time)
    
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"file:{clean_name} food dish",
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }

    proxies = None
    if os.getenv("ROTATING_PROXY"):
        proxy_url = os.getenv("ROTATING_PROXY")
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=3.5)
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                image_info = page_info.get("imageinfo", [])
                if image_info:
                    img_url = image_info[0].get("url", "")
                    if img_url and any(img_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        return recipe_name, img_url
    except Exception as e:
        pass
    
    # في حال عدم وجود صورة، يتم إرجاع قيمة فارغة دون استخدام أي صورة افتراضية
    return recipe_name, ""

# ---------------------------------------------------------
# 4. تحويل الدقائق إلى صيغة ISO 8601
# ---------------------------------------------------------
def minutes_to_iso8601(minutes: float) -> str:
    try:
        mins = int(float(minutes))
        if mins <= 0:
            return "PT15M"
        hours = mins // 60
        remaining_mins = mins % 60
        if hours > 0 and remaining_mins > 0:
            return f"PT{hours}H{remaining_mins}M"
        elif hours > 0:
            return f"PT{hours}H"
        else:
            return f"PT{remaining_mins}M"
    except (ValueError, TypeError):
        return "PT15M"

# ---------------------------------------------------------
# 5. تحويل البيانات إلى Schema.org JSON-LD
# ---------------------------------------------------------
def build_recipe_json_ld(row, image_url: str) -> dict:
    ingredients = ast.literal_eval(row['ingredients']) if isinstance(row['ingredients'], str) else row['ingredients']
    steps = ast.literal_eval(row['steps']) if isinstance(row['steps'], str) else row['steps']
    
    nutrition_obj = {}
    if 'nutrition' in row and isinstance(row['nutrition'], str):
        try:
            nut_list = ast.literal_eval(row['nutrition'])
            if len(nut_list) >= 5:
                nutrition_obj = {
                    "@type": "NutritionInformation",
                    "calories": f"{nut_list[0]} calories",
                    "fatContent": f"{nut_list[1]} g",
                    "sugarContent": f"{nut_list[2]} g",
                    "sodiumContent": f"{nut_list[3]} mg",
                    "proteinContent": f"{nut_list[4]} g"
                }
        except Exception:
            pass

    instructions = [
        {
            "@type": "HowToStep",
            "position": idx + 1,
            "text": str(step).strip().capitalize()
        }
        for idx, step in enumerate(steps)
    ]

    title = clean_title_for_seo(str(row['name']))
    
    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": title,
        "description": str(row.get('description', f"How to make {title} step by step.")).strip(),
        "totalTime": minutes_to_iso8601(row.get('minutes', 30)),
        "recipeIngredient": [str(ing).strip() for ing in ingredients],
        "recipeInstructions": instructions,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": round(float(row.get('avg_rating', 4.5)), 2),
            "reviewCount": int(row.get('review_count', 1))
        }
    }
    
    # إضافة حقل الصورة فقط إذا تم العثور على صورة حقيقية من ويكيميديا
    if image_url:
        schema["image"] = [image_url]
        
    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 6. المعالجة الرئيسية مع طباعة تفصيلية لجميع الخطوات
# ---------------------------------------------------------
def process_dataset():
    print("==================================================")
    print("🚀 [STEP 1/5] Starting Recipe Scraper Pipeline...")
    print("==================================================")
    
    recipes_csv = 'RAW_recipes.csv'
    interactions_csv = 'RAW_interactions.csv'
    
    if not os.path.exists(recipes_csv) or not os.path.exists(interactions_csv):
        print("❌ [ERROR] Dataset CSV files not found!")
        raise FileNotFoundError("بيانات RAW_recipes.csv أو RAW_interactions.csv غير موجودة.")

    print("📖 [STEP 2/5] Reading RAW CSV datasets into Pandas DataFrames...")
    start_time = time.time()
    recipes_df = pd.read_csv(recipes_csv)
    interactions_df = pd.read_csv(interactions_csv)
    print(f"✔️ Loaded {len(recipes_df):,} recipes and {len(interactions_df):,} interactions in {time.time() - start_time:.2f}s")

    print("\n📊 [STEP 3/5] Aggregating ratings and review counts per recipe...")
    stats = interactions_df.groupby('recipe_id').agg(
        review_count=('rating', 'count'),
        avg_rating=('rating', 'mean')
    ).reset_index()

    print("🔗 Merging recipe data with review statistics...")
    merged = pd.merge(recipes_df, stats, left_on='id', right_on='recipe_id', how='inner')

    print("\n🏆 [STEP 4/5] Sorting recipes by popularity and picking top 20,000...")
    top_20k = merged.sort_values(by=['review_count', 'avg_rating'], ascending=[False, False]).head(20000)
    print(f"✔️ Successfully selected top {len(top_20k):,} recipes.")

    output_dir = "output_recipes"
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory verified: '{output_dir}/'")

    chunk_size = 1000
    total_files = 20
    batch_workers = 5  # 5 طلبات توازٍ لمعالجة الدفعات

    print("\n📸 [STEP 5/5] Processing 20,000 recipes into 20 JSON files (1,000 recipes/file)...")
    print("==================================================")

    for i in range(total_files):
        chunk_start_time = time.time()
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        chunk_df = top_20k.iloc[start_idx:end_idx]

        print(f"\n📦 [CHUNK {i+1}/{total_files}] Processing items {start_idx+1:,} to {end_idx:,}...")
        
        recipe_titles = chunk_df['name'].tolist()
        images_map = {}
        found_images_count = 0

        print(f"   🔍 Fetching Wikimedia images using {batch_workers} parallel workers...")
        with ThreadPoolExecutor(max_workers=batch_workers) as executor:
            future_to_title = {executor.submit(fetch_wikimedia_image, title): title for title in recipe_titles}
            for future in as_completed(future_to_title):
                title, img_url = future.result()
                images_map[title] = img_url
                if img_url:
                    found_images_count += 1

        print(f"   🖼️ Images found: {found_images_count}/{len(recipe_titles)} recipes")
        print("   ⚙️ Converting rows to Schema.org JSON-LD structures...")

        file_recipes = []
        for _, row in chunk_df.iterrows():
            recipe_title = row['name']
            image_url = images_map.get(recipe_title, "")
            json_ld = build_recipe_json_ld(row, image_url)
            file_recipes.append(json_ld)

        file_path = os.path.join(output_dir, f"recipes_chunk_{i + 1}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_recipes, f, ensure_ascii=False, indent=2)
            
        chunk_elapsed = time.time() - chunk_start_time
        print(f"   ✅ [SAVED] {file_path} ({len(file_recipes)} recipes) in {chunk_elapsed:.2f}s")

    print("\n==================================================")
    print("🎉 [SUCCESS] All 20,000 recipes processed and saved into 20 JSON-LD files!")
    print("==================================================")

if __name__ == "__main__":
    process_dataset()

