import urllib.request
import json
import sys

# رابط مباشر لقاعدة البيانات المفتوحة (تضم أكثر من 125,000 وصفة)
DATASET_URL = "https://raw.githubusercontent.com/joshpan/recipe-box/master/recipes.json"

def clean_text_list(data_field):
    if isinstance(data_field, list):
        return [str(item).strip() for item in data_field if str(item).strip()]
    if isinstance(data_field, str):
        return [line.strip() for line in data_field.split('\n') if line.strip()]
    return []

def main():
    print("📥 جلب قاعدة البيانات الكاملة بدون استبعاد...")
    
    req = urllib.request.Request(DATASET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw_bytes = response.read()
            data = json.loads(raw_bytes.decode('utf-8'))
            print(f"📊 تم تحميل قاعدة البيانات بنجاح! تحتوي على {len(data)} وصفة خام.")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء التحميل: {e}")
        sys.exit(1)

    recipes_list = []
    
    for item in data:
        title = item.get('title') or item.get('name') or item.get('recipe_name')
        if not title:
            continue

        # استخراج المكونات بمرونة كاملة
        raw_ing = item.get('ingredients') or item.get('ingredient_list') or []
        ingredients = []
        if isinstance(raw_ing, list):
            for ing in raw_ing:
                if isinstance(ing, dict):
                    qty = str(ing.get('quantity', '')).strip()
                    name = str(ing.get('name', '')).strip()
                    item_str = f"{qty} {name}".strip()
                    if item_str:
                        ingredients.append(item_str)
                elif isinstance(ing, str) and ing.strip():
                    ingredients.append(ing.strip())
        elif isinstance(raw_ing, str):
            ingredients = clean_text_list(raw_ing)

        # استخراج الخطوات بدعم جميع المسميات المحتملة (instructions, directions, steps, method)
        raw_inst = item.get('instructions') or item.get('directions') or item.get('steps') or item.get('method') or []
        instructions = clean_text_list(raw_inst)

        # عدم استبعاد الوصفة وإضافة قيم افتراضية عند النقص
        if not ingredients:
            ingredients = ["1 portion main ingredients"]
        if not instructions:
            instructions = ["Mix ingredients together and cook as preferred."]

        title_clean = str(title).strip()
        recipes_list.append({
            "id": len(recipes_list) + 1,
            "title": title_clean,
            "category": "Main Course",
            "description": f"A delicious recipe for {title_clean}.",
            "prepTime": "15m",
            "cookTime": "20m",
            "ingredients": ingredients,
            "instructions": instructions,
            "rating": 5.0
        })

        if len(recipes_list) >= 20000:
            break

    with open('raw_recipes.json', 'w', encoding='utf-8') as f:
        json.dump(recipes_list, f, ensure_ascii=False, indent=2)

    print(f"🎉 تم استخراج وحفظ {len(recipes_list)} وصفة بنجاح داخل raw_recipes.json!")

if __name__ == "__main__":
    main()

