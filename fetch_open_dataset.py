import urllib.request
import json
import os

# رابط مباشر لقاعدة بيانات مفتوحة موثوقة
DATASET_URL = "https://raw.githubusercontent.com/raywenderlich/recipes/master/Recipes.json"

def fetch_and_filter_top_recipes():
    print("📥 جلب قاعدة البيانات المفتوحة تلقائياً داخل السيرفر...")
    
    try:
        req = urllib.request.Request(DATASET_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        print(f"📊 تم إيجاد {len(data)} وصفة خام، جاري التصفية واستخراج الأفضل...")
        
        filtered_recipes = []
        for idx, item in enumerate(data):
            recipe = {
                "id": idx + 1,
                "title": item.get("name") or item.get("title") or "Delicious Recipe",
                "category": item.get("category", "Main Course"),
                "description": item.get("description", ""),
                "prepTime": str(item.get("prepTime", "15m")),
                "cookTime": str(item.get("cookTime", "20m")),
                "ingredients": item.get("ingredients", []),
                "instructions": item.get("instructions", item.get("steps", [])),
                "rating": item.get("rating", 5.0)
            }
            filtered_recipes.append(recipe)
            
        # ترتبيها حسب التقييم الأفضل واختيار حتى 20,000 وصفة
        filtered_recipes.sort(key=lambda x: x.get('rating', 0), reverse=True)
        top_20k = filtered_recipes[:20000]

        with open('raw_recipes.json', 'w', encoding='utf-8') as f:
            json.dump(top_20k, f, ensure_ascii=False, indent=2)

        print(f"✅ تم إنشاء raw_recipes.json بنجاح وبداخله {len(top_20k)} وصفة جاهزة!")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء جلب البيانات: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_filter_top_recipes()

