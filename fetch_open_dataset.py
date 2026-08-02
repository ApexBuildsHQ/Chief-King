import urllib.request
import json
import sys

# المصدر المفتوح الذي يحتوي على أكثر من 120,000 وصفة
URL = "https://cdn.jsdelivr.net/gh/joshpan/recipe-box@master/recipes.json"

def infer_category(title):
    t = title.lower()
    if any(w in t for w in ["cookie", "cake", "pie", "pudding", "sweet", "dessert", "muffin"]):
        return "Dessert"
    if any(w in t for w in ["salad", "soup", "stew", "broth"]):
        return "Salad & Soup"
    if any(w in t for w in ["drink", "smoothie", "cocktail", "juice", "tea"]):
        return "Beverages"
    if any(w in t for w in ["breakfast", "pancake", "waffle", "oatmeal", "egg"]):
        return "Breakfast"
    return "Main Course"

def clean_ingredients(raw_ingredients):
    clean_list = []
    if isinstance(raw_ingredients, list):
        for ing in raw_ingredients:
            if isinstance(ing, dict):
                qty = str(ing.get('quantity', '')).strip()
                name = str(ing.get('name', '')).strip()
                item_str = f"{qty} {name}".strip()
                if item_str:
                    clean_list.append(item_str)
            elif isinstance(ing, str) and ing.strip():
                clean_list.append(ing.strip())
    elif isinstance(raw_ingredients, str):
        clean_list = [i.strip() for i in raw_ingredients.split('\n') if i.strip()]
    return clean_list

def main():
    print("📥 جلب وتنظيف 20,000 وصفة عالمية...")
    
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ خطأ أثناء الجلب: {e}")
        sys.exit(1)

    recipes_list = []
    for item in data:
        title = item.get('title') or item.get('name')
        if not title:
            continue

        ingredients = clean_ingredients(item.get('ingredients'))
        
        raw_instructions = item.get('instructions') or item.get('directions') or []
        if isinstance(raw_instructions, str):
            instructions = [i.strip() for i in raw_instructions.split('\n') if i.strip()]
        else:
            instructions = [str(i).strip() for i in raw_instructions if str(i).strip()]

        if not ingredients or not instructions:
            continue

        title_clean = str(title).strip()
        recipes_list.append({
            "id": len(recipes_list) + 1,
            "title": title_clean,
            "category": infer_category(title_clean),
            "description": f"Classic {title_clean} recipe.",
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

    print(f"✅ تم الحفظ بنجاح! إجمالي الوصفات المنظمة: {len(recipes_list)}")

if __name__ == "__main__":
    main()

