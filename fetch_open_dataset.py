import urllib.request
import json

# روابط بديلة عبر شبكات CDN عالية السرعة لمنع أخطاء 404
SOURCES = [
    "https://cdn.jsdelivr.net/gh/joshpan/recipe-box@master/recipes.json",
    "https://cdn.jsdelivr.net/gh/joshpan/recipe-box@main/recipes.json",
    "https://fastly.jsdelivr.net/gh/joshpan/recipe-box@master/recipes.json",
    "https://raw.githubusercontent.com/joshpan/recipe-box/master/recipes.json"
]

def clean_text_list(data_field):
    """تنظيف المكونات والتعليمات سواء كانت نصوصاً أو مصفوفة أسطر أو كائنات"""
    if isinstance(data_field, list):
        res = []
        for item in data_field:
            if isinstance(item, dict):
                qty = str(item.get('quantity', '')).strip()
                name = str(item.get('name', '')).strip()
                combined = f"{qty} {name}".strip()
                if combined:
                    res.append(combined)
            elif isinstance(item, str) and item.strip():
                res.append(item.strip())
        return res
    if isinstance(data_field, str):
        return [line.strip() for line in data_field.split('\n') if line.strip()]
    return []

def main():
    print("📥 جلب قاعدة البيانات مع التبديل التلقائي بين السيرفرات...")
    
    data = None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for url in SOURCES:
        try:
            print(f"🔄 جاري المحاولة عبر: {url}")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and len(data) > 0:
                    print(f"✅ تم الاتصال بنجاح! إجمالي الوصفات خام: {len(data)}")
                    break
        except Exception as e:
            print(f"⚠️ تعثر المصدر ({e})، جاري التبديل للمصدر التالي...")

    recipes_list = []
    
    if data:
        for item in data:
            title = item.get('title') or item.get('name') or item.get('recipe_name')
            if not title:
                continue

            ingredients = clean_text_list(item.get('ingredients') or item.get('ingredient_list'))
            instructions = clean_text_list(item.get('instructions') or item.get('directions') or item.get('steps'))

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

