import os
import re
import json
import pandas as pd

# ---------------------------------------------------------
# 1. دالة معالجة النصوص والمصفوفات المنفصلة بـ c("...")
# ---------------------------------------------------------
def parse_r_vector(val) -> list:
    """تحويل السلاسل النصية بصيغة R vector c("...") إلى قائمة Python حقيقية"""
    if not isinstance(val, str) or not val or val in ['c()', 'character(0)', 'NA']:
        return []
    items = re.findall(r'"(.*?)"', val)
    if not items:
        items = re.findall(r"'(.*?)'", val)
    return items if items else [val.strip()]

# ---------------------------------------------------------
# 2. استخراج رابط الصورة الحقيقية الأول
# ---------------------------------------------------------
def extract_image_url(images_str) -> str:
    urls = parse_r_vector(images_str)
    valid_urls = [u for u in urls if u.startswith('http')]
    if valid_urls:
        return valid_urls[0]
    return "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=800"

# ---------------------------------------------------------
# 3. دالة تنظيف العناوين لملائمة نية البحث (SEO)
# ---------------------------------------------------------
def clean_title_for_seo(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
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
    cleaned = cleaned.title()
    
    return cleaned if cleaned else title.title()

# ---------------------------------------------------------
# 4. دالة معالجة وجلب المقادير بكمياتها
# ---------------------------------------------------------
def parse_ingredients(row) -> list:
    quantities = parse_r_vector(str(row.get('RecipeIngredientQuantities', '')))
    parts = parse_r_vector(str(row.get('RecipeIngredientParts', '')))
    
    ingredients = []
    if quantities and len(quantities) == len(parts):
        for q, p in zip(quantities, parts):
            ingredients.append(f"{q} {p}".strip())
    elif parts:
        ingredients = parts
    elif quantities:
        ingredients = quantities
        
    return ingredients if ingredients else ["Ingredients available upon request"]

# ---------------------------------------------------------
# 5. بناء هيكل JSON-LD الشامل والمطابق لـ Schema.org
# ---------------------------------------------------------
def build_full_recipe_json_ld(row) -> dict:
    title = clean_title_for_seo(str(row.get('Name', 'Recipe')))
    recipe_id = int(row['RecipeId'])
    
    # 1. الخطوات
    steps = parse_r_vector(str(row.get('RecipeInstructions', '')))
    instructions = [
        {
            "@type": "HowToStep",
            "position": idx + 1,
            "text": str(step).strip().capitalize()
        }
        for idx, step in enumerate(steps) if str(step).strip()
    ]

    # 2. القيم الغذائية الشاملة
    nutrition_obj = {}
    if pd.notna(row.get('Calories')) and row.get('Calories') > 0:
        nutrition_obj = {
            "@type": "NutritionInformation",
            "calories": f"{round(float(row.get('Calories', 0)), 1)} calories",
            "fatContent": f"{round(float(row.get('FatContent', 0)), 1)} g",
            "saturatedFatContent": f"{round(float(row.get('SaturatedFatContent', 0)), 1)} g",
            "cholesterolContent": f"{round(float(row.get('CholesterolContent', 0)), 1)} mg",
            "sodiumContent": f"{round(float(row.get('SodiumContent', 0)), 1)} mg",
            "carbohydrateContent": f"{round(float(row.get('CarbohydrateContent', 0)), 1)} g",
            "fiberContent": f"{round(float(row.get('FiberContent', 0)), 1)} g",
            "sugarContent": f"{round(float(row.get('SugarContent', 0)), 1)} g",
            "proteinContent": f"{round(float(row.get('ProteinContent', 0)), 1)} g"
        }

    # 3. الهيكل العام الشامل للوصفة
    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "id": recipe_id,
        "name": title,
        "description": str(row.get('Description', f"How to make {title} step by step.")).strip(),
        "recipeCategory": str(row.get('RecipeCategory', 'Main Dish')).strip(),
        "image": extract_image_url(str(row.get('Images', ''))),
        "prepTime": str(row.get('PrepTime', 'PT15M')) if pd.notna(row.get('PrepTime')) else "PT15M",
        "cookTime": str(row.get('CookTime', 'PT15M')) if pd.notna(row.get('CookTime')) else "PT15M",
        "totalTime": str(row.get('TotalTime', 'PT30M')) if pd.notna(row.get('TotalTime')) else "PT30M",
        "recipeYield": str(row.get('RecipeServings', '4 servings')) if pd.notna(row.get('RecipeServings')) else "4 servings",
        "recipeIngredient": parse_ingredients(row),
        "recipeInstructions": instructions,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": round(float(row.get('AggregatedRating', 4.5)), 2) if pd.notna(row.get('AggregatedRating')) else 4.5,
            "reviewCount": int(row.get('ReviewCount', 1)) if pd.notna(row.get('ReviewCount')) else 1
        }
    }
    
    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 6. المعالجة الرئيسية والتصدير لـ 20 ملف
# ---------------------------------------------------------
def process_new_dataset():
    print("Loading recipes from the new Kaggle dataset (irkaal)...")
    
    recipes_csv = 'recipes.csv'
    if not os.path.exists(recipes_csv):
        raise FileNotFoundError("ملف recipes.csv الخاص بمكتبة irkaal غير موجود في المسار.")

    # قراءة الملف مع تحديد الأعمدة المطلوبة لتسريع العملية
    df = pd.read_csv(recipes_csv)

    print("Sorting recipes by ReviewCount and AggregatedRating...")
    # ملء القيم الفارغة في التقييمات والمراجعات بالصفر لضمان الترتيب الصحيح
    df['ReviewCount'] = df['ReviewCount'].fillna(0)
    df['AggregatedRating'] = df['AggregatedRating'].fillna(0)

    # الترتيب تنازلياً لاستخراج أعلى 20,000 وصفة طلباً وتقييماً
    top_20k = df.sort_values(by=['ReviewCount', 'AggregatedRating'], ascending=[False, False]).head(20000)

    output_dir = "chunk_recipes_seo"
    os.makedirs(output_dir, exist_ok=True)

    print("Generating complete JSON-LD recipes into chunk_recipes_seo...")
    
    chunk_size = 1000
    total_files = 20

    for i in range(total_files):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        chunk_df = top_20k.iloc[start_idx:end_idx]

        file_recipes = []
        for _, row in chunk_df.iterrows():
            json_ld = build_full_recipe_json_ld(row)
            file_recipes.append(json_ld)

        file_path = os.path.join(output_dir, f"recipes_chunk_{i + 1}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"Saved: {file_path} ({len(file_recipes)} full recipes)")

    print("✅ Done! All 20,000 recipes generated directly from the modern dataset.")

if __name__ == "__main__":
    process_new_dataset()
