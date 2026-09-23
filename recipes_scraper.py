import os
import re
import json
import ast
import requests
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# 1. جلب الصورة الرسمية للوصفة مباشرة من Food.com عبر الـ ID
# ---------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def fetch_official_image(recipe_id: int) -> str:
    """جلب رابط الصورة الأصلية والدقيقة مباشرة من صفحة الوصفة الرسمية"""
    url = f"https://www.food.com/recipe/-{recipe_id}"
    headers = {"User-Agent": USER_AGENTS[recipe_id % len(USER_AGENTS)]}
    
    try:
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # استخراج الصورة الرسمية من wsum meta الخاص بالصفحة
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img_url = og_image["content"]
                # استبعاد الصور الافتراضية وشعارات الموقع
                if "fd-placeholder" not in img_url and "default" not in img_url:
                    return img_url
    except Exception:
        pass
    return ""

# ---------------------------------------------------------
# 2. تنظيف وتنسيق عناوين الوصفات لتطابق نية البحث (SEO)
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
# 3. تحويل الدقائق إلى صيغة ISO 8601 المعيارية لـ Schema.org
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
# 4. تحويل بيانات الوصفة إلى صيغة Schema.org JSON-LD
# ---------------------------------------------------------
def build_recipe_json_ld(row, image_url: str = "") -> dict:
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
    
    # إضافة رابط الصورة الرسمية إذا تم العثور عليه
    if image_url:
        schema["image"] = [image_url]
        
    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 5. المعالجة الرئيسية وتصدير الـ 20 ألف وصفة مع الصور
# ---------------------------------------------------------
def process_dataset():
    print("🚀 Loading Food.com datasets...")
    
    recipes_csv = 'RAW_recipes.csv'
    interactions_csv = 'RAW_interactions.csv'
    
    if not os.path.exists(recipes_csv) or not os.path.exists(interactions_csv):
        raise FileNotFoundError("بيانات RAW_recipes.csv أو RAW_interactions.csv غير موجودة في المسار الحالي.")

    recipes_df = pd.read_csv(recipes_csv)
    interactions_df = pd.read_csv(interactions_csv)

    print("📊 Calculating review counts and average ratings...")
    stats = interactions_df.groupby('recipe_id').agg(
        review_count=('rating', 'count'),
        avg_rating=('rating', 'mean')
    ).reset_index()

    merged = pd.merge(recipes_df, stats, left_on='id', right_on='recipe_id', how='inner')

    print("🏆 Sorting and selecting top 20,000 recipes...")
    top_20k = merged.sort_values(by=['review_count', 'avg_rating'], ascending=[False, False]).head(20000)

    output_dir = "output_recipes"
    os.makedirs(output_dir, exist_ok=True)

    chunk_size = 1000
    total_files = 20

    for i in range(total_files):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        chunk_df = top_20k.iloc[start_idx:end_idx]

        print(f"\n🖼️ [Chunk {i+1}/{total_files}] Fetching official images in parallel...")
        
        # استخدام التوازي (15 Threads) لسحب الصور بسرعة عالية دون حظر
        image_map = {}
        recipe_ids = chunk_df['id'].tolist()
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_id = {executor.submit(fetch_official_image, r_id): r_id for r_id in recipe_ids}
            for future in as_completed(future_to_id):
                r_id = future_to_id[future]
                try:
                    img_url = future.result()
                    if img_url:
                        image_map[r_id] = img_url
                except Exception:
                    pass

        file_recipes = []
        for _, row in chunk_df.iterrows():
            r_id = row['id']
            image_url = image_map.get(r_id, "")
            json_ld = build_recipe_json_ld(row, image_url)
            file_recipes.append(json_ld)

        file_path = os.path.join(output_dir, f"recipes_chunk_{i + 1}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Saved: {file_path} ({len(file_recipes)} recipes processed)")

    print("\n🎉 Processing complete! All 20,000 SEO recipes generated with official images.")

if __name__ == "__main__":
    process_dataset()

