import json
import re
import os
from datasets import load_dataset

def clean_title_for_seo(title: str) -> str:
    """
    تحويل اسم الوصفة لعنوان مطابق تماماً لما يبحث عنه الناس يومياً في جوجل
    مثال: "Grandma's Best Secret Chocolate Cake!" -> "Chocolate Cake Recipe"
    """
    if not title:
        return "Classic Recipe"
    
    # الكلمات الوصفية الزائدة التي يتركها الناس عند البحث
    stop_words = r'\b(my|grandma\'s|mom\'s|secret|famous|world\'s best|easy|quick|delish|ultimate|best ever|delicious|authentic|yummy|how to make)\b'
    
    # حذف الرموز والكلمات الزائدة
    cleaned = re.sub(stop_words, '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = ' '.join(cleaned.split()).title()
    
    # إلحاق كلمة Recipe لتكون عبارة بحث قياسية (Exact Search Term)
    if not cleaned.lower().endswith('recipe'):
        cleaned = f"{cleaned} Recipe"
        
    return cleaned

def generate_seo_raw_recipes():
    print("⏳ جاري سحب قاعدة البيانات العالمية لأشهر الوصفات من Hugging Face...")
    
    # جلب مجموعة بيانات الوصفات العالمية (تحتوي على أكثر من 100 ألف وصفة)
    try:
        ds = load_dataset("Ster3o/recipes_dataset", split="train")
    except Exception:
        # مصدر بديل في حال تعذر المصدر الأول
        ds = load_dataset("FoodBase/recipes", split="train")

    print(f"✅ تم جلب البيانات. جاري فلترة وتنظيف أعلى 20,000 وصفة...")

    formatted_recipes = []
    
    for idx, item in enumerate(ds):
        if len(formatted_recipes) >= 20000:
            break

        # استخراج البيانات والتأكد من جودتها
        raw_title = item.get("title") or item.get("name") or ""
        ingredients = item.get("ingredients") or []
        instructions = item.get("instructions") or item.get("directions") or []
        
        # تحويل Instructions إلى القائمة إذا كانت نصاً موحداً
        if isinstance(instructions, str):
            instructions = [ins.strip() for ins in instructions.split('\n') if ins.strip()]
            
        if isinstance(ingredients, str):
            ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]

        # استبعاد الوصفات غير المكتملة
        if not raw_title or not ingredients or not instructions:
            continue

        seo_title = clean_title_for_seo(raw_title)

        recipe_entry = {
            "title": seo_title,
            "category": item.get("category", "Main Course"),
            "image_url": item.get("image_url") or item.get("image") or "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=500",
            "prep_time": item.get("prep_time", "15 mins"),
            "cook_time": item.get("cook_time", "30 mins"),
            "servings": str(item.get("servings", "4")),
            "ingredients": ingredients,
            "instructions": instructions
        }

        formatted_recipes.append(recipe_entry)

    # حفظ الملف الناتج مباشرة باسم raw_recipes.json
    output_filename = "raw_recipes.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(formatted_recipes, f, ensure_ascii=False, indent=2)

    print(f"🎉 تم إنشاء الملف بنجاح: {output_filename}")
    print(f"📊 إجمالي الوصفات المحفوظة: {len(formatted_recipes)} وصفة جاهزة للمعالجة والترجمة.")

if __name__ == "__main__":
    generate_seo_raw_recipes()

