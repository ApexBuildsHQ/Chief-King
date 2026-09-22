import json
import re
import urllib.request
from datasets import load_dataset

def clean_title_for_seo(title: str) -> str:
    """تحويل اسم الوصفة لعنوان مطابق لنية البحث المباشرة في جوجل"""
    if not title:
        return "Classic Recipe"
    
    stop_words = r'\b(my|grandma\'s|mom\'s|secret|famous|world\'s best|easy|quick|delish|ultimate|best ever|delicious|authentic|yummy|how to make)\b'
    cleaned = re.sub(stop_words, '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = ' '.join(cleaned.split()).title()
    
    if not cleaned.lower().endswith('recipe'):
        cleaned = f"{cleaned} Recipe"
        
    return cleaned

def generate_seo_raw_recipes():
    print("⏳ جاري سحب قاعدة البيانات العالمية لأشهر الوصفات...")
    
    raw_recipes_list = []
    
    # 1. التجربة من Hugging Face باستخدام قاعدة بيانات نشطة ومضمونة
    try:
        print("🔹 جاري الجلب من Hugging Face (epfl-dlab/structured-recipe-data)...")
        ds = load_dataset("epfl-dlab/structured-recipe-data", split="train")
        for item in ds:
            raw_recipes_list.append({
                "title": item.get("title") or item.get("name") or "",
                "ingredients": item.get("ingredients") or [],
                "instructions": item.get("instructions") or item.get("directions") or [],
                "category": item.get("category", "Main Course"),
                "image_url": item.get("image") or item.get("image_url") or "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=500"
            })
    except Exception as e:
        print(f"⚠️ تعذر الوصول للمصدر الأول ({e})، جاري الانتقال للمصدر المباشر الاحتياطي...")
        # 2. رابط مباشر احتياطي لملف JSON موثوق
        url = "https://raw.githubusercontent.com/openrecipes/recipes-data/master/allrecipes.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            lines = response.read().decode('utf-8').splitlines()
            for line in lines:
                if line.strip():
                    raw_recipes_list.append(json.loads(line))

    print(f"✅ تم سحب البيانات بنجاح. جاري تنظيف وتشكيل الوصفات لـ SEO...")

    formatted_recipes = []
    for item in raw_recipes_list:
        if len(formatted_recipes) >= 20000:
            break

        raw_title = item.get("title") or item.get("name") or ""
        ingredients = item.get("ingredients") or []
        instructions = item.get("instructions") or item.get("directions") or item.get("recipeInstructions") or []

        if isinstance(instructions, str):
            instructions = [ins.strip() for ins in instructions.split('\n') if ins.strip()]
        if isinstance(ingredients, str):
            ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]

        if not raw_title or not ingredients or not instructions:
            continue

        seo_title = clean_title_for_seo(raw_title)

        recipe_entry = {
            "title": seo_title,
            "category": item.get("category", "Main Course"),
            "image_url": item.get("image_url") or item.get("image") or "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=500",
            "prep_time": "15 mins",
            "cook_time": "30 mins",
            "servings": "4",
            "ingredients": ingredients,
            "instructions": instructions
        }

        formatted_recipes.append(recipe_entry)

    # حفظ الملف الناتج
    output_filename = "raw_recipes.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(formatted_recipes, f, ensure_ascii=False, indent=2)

    print(f"🎉 تم إنشاء الملف بنجاح: {output_filename} بعدد {len(formatted_recipes)} وصفة.")

if __name__ == "__main__":
    generate_seo_raw_recipes()

