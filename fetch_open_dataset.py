import urllib.request
import json
import os
import sys

# روابط مصادر عالمية مفتوحة ودائمة لإنشاء قاعدة البيانات
PRIMARY_URL = "https://raw.githubusercontent.com/joshpan/recipe-box/master/recipes.json"
FALLBACK_URL = "https://raw.githubusercontent.com/bodiguel/recipes-dataset/master/recipes.json"

def fetch_data(url):
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    print("📥 جلب قاعدة بيانات الوصفات المفتوحة والمستقرة...")
    
    data = None
    try:
        data = fetch_data(PRIMARY_URL)
        print("✅ تم الاتصال بالمصدر الرئيسي بنجاح!")
    except Exception as e:
        print(f"⚠️ تعثر المصدر الرئيسي ({e})، جاري التحويل للمصدر الاحتياطي...")
        try:
            data = fetch_data(FALLBACK_URL)
            print("✅ تم الاتصال بالمصدر الاحتياطي بنجاح!")
        except Exception as err:
            print(f"❌ فشل الاتصال بجميع المصادر: {err}")
            sys.exit(1)

    recipes_list = []
    for item in data:
        title = item.get('title') or item.get('name')
        ingredients = item.get('ingredients')
        instructions = item.get('instructions') or item.get('directions')

        if not title or not ingredients or not instructions:
            continue

        # تنظيف وتحويل البيانات لسطور منظمة
        if isinstance(ingredients, str):
            ingredients = [i.strip() for i in ingredients.split('\n') if i.strip()]
        if isinstance(instructions, str):
            instructions = [i.strip() for i in instructions.split('\n') if i.strip()]

        recipes_list.append({
            "id": len(recipes_list) + 1,
            "title": str(title).strip(),
            "category": str(item.get('category', 'Main Course')),
            "description": str(item.get('description', '')),
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

    print(f"🎉 تم استخراج وحفظ {len(recipes_list)} وصفة عالمية حقيقية داخل raw_recipes.json!")

if __name__ == "__main__":
    main()

