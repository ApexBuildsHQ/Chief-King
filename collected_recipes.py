import os
import re
import json
import ast
import pandas as pd

# ---------------------------------------------------------
# 1. تنظيف العناوين العامة وإصلاحها لـ SEO محركات البحث
# ---------------------------------------------------------
def clean_title_for_seo(title: str) -> str:
    if not isinstance(title, str):
        return "Delicious Recipe"
    
    # قائمة العبارات العامية والأسماء الفردية التي تضر بالـ SEO
    stop_patterns = [
        r"\bjo\s+mama'?s?\b",
        r"\byes\s+virginia\s+there\s+is\s+a\b",
        r"\bto\s+die\s+for\b",
        r"\bout\s+of\s+this\s+world\b",
        r"\bknock\s+your\s+socks\s+off\b",
        r"\bworld'?s?\s+best\b",
        r"\bthe\s+best\s+ever\b",
        r"\bbest\s+ever\b",
        r"\bmom'?s?\b", r"\bmother'?s?\b", r"\bgrandma'?s?\b", 
        r"\bauntie'?s?\b", r"\buncle'?s?\b", r"\bby\s+\w+\b",
        r"\bsecret\b", r"\bfamous\b", r"\baward\s+winning\b",
        r"\bmy\b", r"\bquick\s+and\s+easy\b", r"\beasy\s+and\s+delicious\b"
    ]
    
    cleaned = title.lower()
    for pattern in stop_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # تنظيف الرموز والمسافات
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # تحويل أول حرف من كل كلمة لـ Capital
    cleaned = cleaned.title()
    
    # إذا أصبح الاسم قصيراً جداً أو فارغاً بعد الحذف نرجع الاسم الأساسي بنظافة
    return cleaned if len(cleaned) > 3 else title.title()

# ---------------------------------------------------------
# 2. استخراج التصنيف بدقة مع تعديل أولوية المعكرونة والحلويات
# ---------------------------------------------------------
def extract_category(row) -> str:
    tags = []
    if 'tags' in row and isinstance(row['tags'], str):
        try:
            tags = ast.literal_eval(row['tags'])
        except Exception:
            tags = []
            
    tags_str = ' '.join([str(t).lower() for t in tags])
    name_str = str(row.get('name', '')).lower()
    combined_context = f"{tags_str} {name_str}"

    # أولوية 1: المعكرونة والبيتزا (تمنع تصنيف المكرونة باللحم كـ المشويات)
    if any(k in combined_context for k in ['pasta', 'spaghetti', 'macaroni', 'noodle', 'lasagna', 'pizza', 'fettuccine', 'penne', 'linguine', 'ravioli']):
        return "Main Course - Pasta & Pizza"
    
    # أولوية 2: الحلويات والمخبوزات
    elif any(k in combined_context for k in ['dessert', 'desserts', 'baking', 'cake', 'cookie', 'pie', 'sweet', 'pudding', 'brownie']):
        return "Dessert"
    
    # أولوية 3: الشوربة والمرق
    elif any(k in combined_context for k in ['soup', 'soups', 'stew', 'stews', 'chowder', 'broth']):
        return "Soup & Stew"

    # أولوية 4: المأكولات البحرية
    elif any(k in combined_context for k in ['seafood', 'fish', 'shrimp', 'salmon', 'crab', 'lobster', 'tuna']):
        return "Main Course - Seafood"

    # أولوية 5: الدواجن والطيور
    elif any(k in combined_context for k in ['chicken', 'poultry', 'turkey', 'duck']):
        return "Main Course - Poultry"

    # أولوية 6: المشويات واللحوم الحمراء
    elif any(k in combined_context for k in ['barbecue', 'bbq', 'grill', 'grilling', 'steak', 'beef', 'pork', 'lamb', 'meatloaf', 'roast', 'ribs', 'meat']):
        return "Main Course - Grills & Meats"

    # أولوية 7: السلطات والمقبلات
    elif any(k in combined_context for k in ['salad', 'salads', 'appetizer', 'starter', 'dip', 'fingerfood', 'snack']):
        return "Appetizer & Salad"

    # أولوية 8: المشروبات
    elif any(k in combined_context for k in ['beverage', 'beverages', 'drink', 'drinks', 'cocktail', 'smoothie', 'juice']):
        return "Beverage"

    # أولوية 9: الإفطار
    elif any(k in combined_context for k in ['breakfast', 'brunch', 'pancake', 'waffle', 'omelet', 'egg']):
        return "Breakfast"

    # أولوية 10: المخبوزات
    elif any(k in combined_context for k in ['bread', 'muffin', 'dough', 'roll']):
        return "Baking & Bread"

    else:
        return "Main Course"

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
# 4. تحويل بيانات الوصفة إلى صيغة Schema.org JSON-LD المعيارية
# ---------------------------------------------------------
def build_recipe_json_ld(row) -> dict:
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
    category = extract_category(row)
    
    schema = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": title,
        "recipeCategory": category,
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
    
    if nutrition_obj:
        schema["nutrition"] = nutrition_obj

    return schema

# ---------------------------------------------------------
# 5. المعالجة الرئيسية وتصدير الـ 20 ألف وصفة إلى مجلد output_recipes_2
# ---------------------------------------------------------
def process_dataset():
    print("Loading Food.com datasets...")
    
    recipes_csv = 'RAW_recipes.csv'
    interactions_csv = 'RAW_interactions.csv'
    
    if not os.path.exists(recipes_csv) or not os.path.exists(interactions_csv):
        raise FileNotFoundError("بيانات RAW_recipes.csv أو RAW_interactions.csv غير موجودة في المسار الحالي.")

    recipes_df = pd.read_csv(recipes_csv)
    interactions_df = pd.read_csv(interactions_csv)

    print("Calculating review counts and average ratings...")
    stats = interactions_df.groupby('recipe_id').agg(
        review_count=('rating', 'count'),
        avg_rating=('rating', 'mean')
    ).reset_index()

    merged = pd.merge(recipes_df, stats, left_on='id', right_on='recipe_id', how='inner')

    print("Sorting and selecting top 20,000 recipes...")
    top_20k = merged.sort_values(by=['review_count', 'avg_rating'], ascending=[False, False]).head(20000)

    # إنشاء المجلد المطلوب output_recipes_2
    output_dir = "output_recipes_2"
    os.makedirs(output_dir, exist_ok=True)

    print("Generating JSON-LD structures with refined categories and SEO titles...")
    
    chunk_size = 1000
    total_files = 20

    for i in range(total_files):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        chunk_df = top_20k.iloc[start_idx:end_idx]

        file_recipes = []
        for _, row in chunk_df.iterrows():
            json_ld = build_recipe_json_ld(row)
            file_recipes.append(json_ld)

        file_path = os.path.join(output_dir, f"recipes_chunk_{i + 1}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"Saved: {file_path} ({len(file_recipes)} recipes processed)")

    print("Processing complete! All 20,000 SEO recipes saved successfully to output_recipes_2.")

if __name__ == "__main__":
    process_dataset()

