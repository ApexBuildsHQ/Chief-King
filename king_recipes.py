import os
import re
import json
import sys
import pandas as pd

# تفعيل الطباعة المباشرة لسجلات GitHub Actions بدون تأخير
sys.stdout.reconfigure(line_buffering=True)

# ---------------------------------------------------------
# دالة مساعدة للجلب الآمن من الصف بمرونة دون أخطاء KeyError
# ---------------------------------------------------------
def safe_get(row, possible_keys, default=None):
    """البحث عن القيمة باستخدام عدة مسميات محتملة للعمود دون التأثر بحالة الأحرف"""
    for key in possible_keys:
        if key in row and pd.notna(row[key]):
            val = str(row[key]).strip()
            if val and val.lower() not in ['nan', 'none', 'null', '']:
                return row[key]
    return default

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
    urls = parse_r_vector(str(images_str))
    valid_urls = [u for u in urls if isinstance(u, str) and u.startswith('http')]
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
    quantities_raw = safe_get(row, ['RecipeIngredientQuantities', 'ingredient_quantities', 'quantities'], '')
    parts_raw = safe_get(row, ['RecipeIngredientParts', 'ingredient_parts', 'parts', 'ingredients'], '')
    
    quantities = parse_r_vector(str(quantities_raw))
    parts = parse_r_vector(str(parts_raw))
    
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
# 5. بناء هيكل JSON-LD الشامل لكافة أعمدة البيانات
# ---------------------------------------------------------
def build_full_recipe_json_ld(row) -> dict:
    raw_name = safe_get(row, ['Name', 'name', 'title', 'RecipeName'], 'Recipe')
    title = clean_title_for_seo(str(raw_name))
    
    # 1. الخطوات (Instructions)
    instructions_raw = safe_get(row, ['RecipeInstructions', 'instructions', 'RecipeInstruction'], '')
    steps = parse_r_vector(str(instructions_raw))
    instructions = [
        {
            "@type": "HowToStep",
            "position": idx + 1,
            "text": str(step).strip().capitalize()
        }
        for idx, step in enumerate(steps) if str(step).strip()
    ]

    # 2. الكلمات المفتاحية (Keywords)
    keywords_raw = safe_get(row, ['Keywords', 'keywords', 'tags'], '')
    keywords_list = parse_r_vector(str(keywords_raw))

    # 3. القيم الغذائية الشاملة (Nutrition)
    nutrition_obj = {}
    raw_calories = safe_get(row, ['Calories', 'calories'], None)
    try:
        cal_val = float(raw_calories) if raw_calories is not None else 0.0
    except (ValueError, TypeError):
        cal_val = 0.0

    if cal_val > 0:
        def safe_float(key, default=0.0):
            val = safe_get(row, [key, key.lower()], None)
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                return default

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

    # 4. التقييمات والمراجعات
    raw_rating = safe_get(row, ['AggregatedRating', 'rating', 'AggregatedRatingValue'], 4.5)
    raw_reviews = safe_get(row, ['ReviewCount', 'reviews', 'ReviewCountValue'], 1)
    try:
        rating_val = round(float(raw_rating), 2)
    except (ValueError, TypeError):
        rating_val = 4.5
    try:
        review_val = int(float(raw_reviews))
    except (ValueError, TypeError):
        review_val = 1

    # 5. استخراج البيانات الوصفية (Category, Image, Author, Time...)
    raw_desc = safe_get(row, ['Description', 'description', 'summary'], f"How to make {title} step by step.")
    raw_cat = safe_get(row, ['RecipeCategory', 'category', 'Category'], 'Main Dish')
    raw_author = safe_get(row, ['AuthorName', 'author', 'Author'], 'Chef King')
    raw_images = safe_get(row, ['Images', 'images', 'image', 'Image', 'URL'], '')
    raw_prep = safe_get(row, ['PrepTime', 'prep_time'], 'PT15M')
    raw_cook = safe_get(row, ['CookTime', 'cook_time'], 'PT15M')
    raw_total = safe_get(row, ['TotalTime', 'total_time'], 'PT30M')
    raw_yield = safe_get(row, ['RecipeServings', 'servings', 'yield'], '4 servings')

    # 6. الهيكل الكامل للوصفة المطابق لـ Schema.org
    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": title,
        "description": str(raw_desc).strip(),
        "recipeCategory": str(raw_cat).strip(),
        "author": {
            "@type": "Person",
            "name": str(raw_author).strip()
        },
        "keywords": ", ".join(keywords_list) if keywords_list else title,
        "image": extract_image_url(raw_images),
        "prepTime": str(raw_prep).strip() if raw_prep else "PT15M",
        "cookTime": str(raw_cook).strip() if raw_cook else "PT15M",
        "totalTime": str(raw_total).strip() if raw_total else "PT30M",
        "recipeYield": str(raw_yield).strip() if raw_yield else "4 servings",
        "recipeIngredient": parse_ingredients(row),
        "recipeInstructions": instructions,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": rating_val,
            "reviewCount": review_val
        }
    }

    # 🛠️ إضافة حقل الـ ID اختيارياً فقط عند توفره دون أي فرض
    raw_id = safe_get(row, ['RecipeId', 'recipe_id', 'id', 'RecipeID', 'ID'])
    if raw_id is not None:
        try:
            schema["id"] = int(raw_id)
        except (ValueError, TypeError):
            schema["id"] = str(raw_id).strip()

    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 6. المعالجة الرئيسية والتصدير لـ 20 ملفاً
# ---------------------------------------------------------
def process_new_dataset():
    print("🚀 [خطوة 1/5] بدء التشغيل: التحقق من وجود ملف البيانات recipes.csv...", flush=True)
    
    recipes_csv = 'recipes.csv'
    if not os.path.exists(recipes_csv):
        raise FileNotFoundError("❌ خطأ: ملف recipes.csv غير موجود في المسار الحالي.")

    print("📖 [خطوة 2/5] قراءة ملف البيانات الضخم عبر Pandas...", flush=True)
    df = pd.read_csv(
        recipes_csv, 
        engine='python',
        on_bad_lines='skip',
        encoding='utf-8', 
        encoding_errors='replace'
    )

    # 🛠️ 1. تنظيف أغطية الأعمدة وإزالة أي مسافات أو رموز غير مرئية
    df.columns = df.columns.str.strip()

    # 🔍 === طباعة التقرير التشخيصي للبيانات الخام في السجلات ===
    print("\n" + "="*60, flush=True)
    print(f"📋 [تشخيص] إجمالي عدد الأعمدة المفحوصة: {len(df.columns)}", flush=True)
    print("📋 [تشخيص] عناوين الأعمدة الحقيقية بالكامل في الملف:", flush=True)
    for idx, col in enumerate(df.columns, 1):
        print(f"   {idx}. '{col}'", flush=True)
    
    print("\n🔍 [تشخيص] عينة السطر الأول الخام من الملف (Raw First Row):", flush=True)
    try:
        first_row_dict = df.iloc[0].to_dict()
        print(json.dumps(first_row_dict, indent=2, ensure_ascii=False, default=str), flush=True)
    except Exception as e:
        print(f"⚠️ تعذر تحويل السطر الأول كـ JSON: {e}", flush=True)
    print("="*60 + "\n", flush=True)
    # =========================================================

    print(f"📊 تم تحميل البيانات بنجاح! إجمالي الوصفات في الملف: {len(df):,}", flush=True)

    print("⭐ [خطوة 3/5] فرز وترتيب أعلى 20,000 وصفة تقييماً ومراجعة...", flush=True)

    # 🛠️ 2. البحث عن أعمدة التقييم والمراجعات بمرونة (حتى لو اختلفت حالات الأحرف)
    review_col = next((col for col in df.columns if 'review' in col.lower()), None)
    rating_col = next((col for col in df.columns if 'rating' in col.lower()), None)

    sort_cols = []
    if review_col:
        df[review_col] = pd.to_numeric(df[review_col], errors='coerce').fillna(0)
        sort_cols.append(review_col)
    if rating_col:
        df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce').fillna(0)
        sort_cols.append(rating_col)

    if sort_cols:
        top_20k = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).head(20000)
    else:
        top_20k = df.head(20000)

    print("✅ تم تحديد قائمة أعلى 20,000 وصفة شعبية بنجاح.", flush=True)

    output_dir = "output_recipes_seo_2"
    print(f"📁 [خطوة 4/5] إنشاء مجلد المخرجات: '{output_dir}'...", flush=True)
    os.makedirs(output_dir, exist_ok=True)

    print("⚙️ [خطوة 5/5] بدء توليد ملفات JSON-LD الـ 20 (كل ملف 1000 وصفة)...", flush=True)
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
            
        print(f"  🟢 [ملف {i + 1}/20] تم إنشاؤه بنجاح: '{file_name}' ({len(file_recipes)} وصفة)", flush=True)

    print(f"🎉 تم الانتهاء بنجاح! جميع الملفات الـ 20 محفوظة داخل مجلد '{output_dir}'.", flush=True)

# ---------------------------------------------------------
# سطر الاستدعاء التلقائي المباشر (مهم جداً للتشغيل على السيرفر)
# ---------------------------------------------------------
if __name__ == "__main__":
    process_new_dataset()
