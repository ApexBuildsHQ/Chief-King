import os
import re
import json
import sys
import pandas as pd

# تفعيل الطباعة المباشرة لسجلات GitHub Actions بدون تأخير
sys.stdout.reconfigure(line_buffering=True)

# ---------------------------------------------------------
# 1. دالة تفكيك نصوص R Vector مثل c("val1", "val2")
# ---------------------------------------------------------
def parse_r_vector(val) -> list:
    """تحويل السلاسل النصية بصيغة R vector c(...) إلى قائمة Python حقيقية"""
    if not isinstance(val, str) or not val or val in ['c()', 'character(0)', 'NA', 'nan', 'None']:
        return []
    
    cleaned_val = val.replace('\\"', '"').replace('\\', '')
    items = re.findall(r'"(.*?)"', cleaned_val)
    if not items:
        items = re.findall(r"'(.*?)'", cleaned_val)
    return [item.strip() for item in items if item.strip()]

# ---------------------------------------------------------
# 2. استخراج وتصحيح رابط الصورة الحقيقي من حقل Images
# ---------------------------------------------------------
def extract_image_url(images_str) -> str:
    urls = parse_r_vector(str(images_str))
    valid_urls = [u for u in urls if isinstance(u, str) and u.startswith('http')]
    
    if valid_urls:
        url = valid_urls[0]
        # تحويل نطاق الصور القديم sndimg إلى نطاق food.com الحقيقي
        url = url.replace("img.sndimg.com", "img.food.com")
        return url
        
    return "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=800"

# ---------------------------------------------------------
# 3. تنظيف العنوان لتحسين محركات البحث SEO
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
    
    return cleaned.title() if cleaned else title.title()

# ---------------------------------------------------------
# 4. دمج حقول المقادير والكميات المطابقة كلياً للحروف
# ---------------------------------------------------------
def parse_ingredients(row) -> list:
    # المطابقة الحرفية لـ RecipeIngredientQuantities و RecipeIngredientParts
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
# 5. بناء هيكل JSON-LD بالأعمدة المحددة حصراً
# ---------------------------------------------------------
def build_full_recipe_json_ld(row) -> dict:
    # 1. الاسم والمكونات والخطوات
    raw_name = row.get('Name', 'Delicious Recipe')
    title = clean_title_for_seo(str(raw_name))
    
    steps = parse_r_vector(str(row.get('RecipeInstructions', '')))
    instructions = [
        {
            "@type": "HowToStep",
            "position": idx + 1,
            "text": str(step).strip().capitalize()
        }
        for idx, step in enumerate(steps) if str(step).strip()
    ]

    keywords_list = parse_r_vector(str(row.get('Keywords', '')))

    # 2. القيم الغذائية بالأسماء الحرفية المباشرة
    nutrition_obj = {}
    try:
        cal_val = float(row.get('Calories', 0))
    except (ValueError, TypeError):
        cal_val = 0.0

    if cal_val > 0:
        def safe_float(key):
            try:
                val = row.get(key, 0)
                return float(val) if pd.notna(val) else 0.0
            except (ValueError, TypeError):
                return 0.0

        nutrition_obj = {
            "@type": "NutritionInformation",
            "calories": f"{round(cal_val, 1)} calories",
            "fatContent": f"{round(safe_float('FatContent'), 1)} g",
            "saturatedFatContent": f"{round(safe_float('SaturatedFatContent'), 1)} g",
            "cholesterolContent": f"{round(safe_float('CholesterolContent'), 1)} mg",
            "sodiumContent": f"{round(safe_float('SodiumContent'), 1)} mg",
            "carbohydrateContent": f"{round(safe_float('CarbohydrateContent'), 1)} g",
            "fiberContent": f"{round(safe_float('FiberContent'), 1)} g",
            "sugarContent": f"{round(safe_float('SugarContent'), 1)} g",
            "proteinContent": f"{round(safe_float('ProteinContent'), 1)} g"
        }

    # 3. التقييمات والمراجعات (AggregatedRating و ReviewCount)
    try:
        rating_val = round(float(row.get('AggregatedRating', 4.5)), 2)
    except (ValueError, TypeError):
        rating_val = 4.5
    try:
        review_val = int(float(row.get('ReviewCount', 1)))
    except (ValueError, TypeError):
        review_val = 1

    # 4. باقي الحقول المقبولة (مع استبعاد AuthorId, AuthorName, DatePublished)
    raw_desc = row.get('Description', f"How to make {title} step by step.")
    raw_cat = row.get('RecipeCategory', 'Main Dish')
    raw_prep = row.get('PrepTime', 'PT15M')
    raw_cook = row.get('CookTime', 'PT15M')
    raw_total = row.get('TotalTime', 'PT30M')
    
    # تفضيل RecipeYield ثم RecipeServings
    yield_val = row.get('RecipeYield')
    servings_val = row.get('RecipeServings')
    raw_yield = yield_val if pd.notna(yield_val) and str(yield_val).strip() != '' else servings_val
    if not pd.notna(raw_yield) or str(raw_yield).strip() == '':
        raw_yield = '4 servings'

    recipe_id = row.get('RecipeId')
    try:
        recipe_id_val = int(recipe_id) if pd.notna(recipe_id) else None
    except (ValueError, TypeError):
        recipe_id_val = str(recipe_id) if pd.notna(recipe_id) else None

    # بناء Schema.org
    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "id": recipe_id_val,
        "name": title,
        "description": str(raw_desc).strip() if pd.notna(raw_desc) else f"How to make {title}.",
        "recipeCategory": str(raw_cat).strip() if pd.notna(raw_cat) else "Main Dish",
        "author": {
            "@type": "Person",
            "name": "Chef King"  # قيمة ثابتة دون الاعتماد على حقول المطور الملتغاة
        },
        "keywords": ", ".join(keywords_list) if keywords_list else title,
        "image": extract_image_url(row.get('Images', '')),
        "prepTime": str(raw_prep).strip() if pd.notna(raw_prep) else "PT15M",
        "cookTime": str(raw_cook).strip() if pd.notna(raw_cook) else "PT15M",
        "totalTime": str(raw_total).strip() if pd.notna(raw_total) else "PT30M",
        "recipeYield": str(raw_yield).strip(),
        "recipeIngredient": parse_ingredients(row),
        "recipeInstructions": instructions,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": rating_val if pd.notna(rating_val) else 4.5,
            "reviewCount": review_val if pd.notna(review_val) else 1
        }
    }

    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 6. المعالجة الأساسية والتصدير
# ---------------------------------------------------------
def process_new_dataset():
    recipes_csv = 'recipes.csv'
    if not os.path.exists(recipes_csv):
        raise FileNotFoundError("❌ خطأ: ملف recipes.csv غير موجود.")

    print("📖 قراءة ملف البيانات عبر Pandas...", flush=True)
    df = pd.read_csv(
        recipes_csv, 
        engine='python',
        on_bad_lines='skip',
        encoding='utf-8', 
        encoding_errors='replace'
    )

    # تنظيف المسافات المخفية حول أسماء الأعمدة مع الحفاظ على التكبير والتصغير الحرفي
    df.columns = df.columns.str.strip()
    print(f"📊 إجمالي الوصفات الحقيقية في الملف: {len(df):,}", flush=True)

    # ترتيب أعلى 20,000 وصفة باستخدام الأسماء الحرفية المباشرة
    df['ReviewCount'] = pd.to_numeric(df['ReviewCount'], errors='coerce').fillna(0)
    df['AggregatedRating'] = pd.to_numeric(df['AggregatedRating'], errors='coerce').fillna(0)

    top_20k = df.sort_values(by=['ReviewCount', 'AggregatedRating'], ascending=[False, False]).head(20000)

    output_dir = "output_recipes_seo_2"
    os.makedirs(output_dir, exist_ok=True)

    print("⚙️ بدء توليد الـ 20 ملف JSON-LD...", flush=True)
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

        file_name = f"chunk_recipes_{i + 1}.json"
        file_path = os.path.join(output_dir, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"  🟢 [ملف {i + 1}/20] تم إنشاؤه: '{file_name}' ({len(file_recipes)} وصفة)", flush=True)

    print(f"🎉 تم الانتهاء بنجاح! تم حفظ الملفات داخل '{output_dir}'.", flush=True)

if __name__ == "__main__":
    process_new_dataset()
