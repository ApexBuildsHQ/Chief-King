import urllib.request
import json
import os

# رابط مباشر ومفتوح لقاعدة بيانات وصفات عالمية شاملة دون قيود صلاحيات
DATASET_URL = "https://raw.githubusercontent.com/dfm/recipes/master/recipes.json"

def fetch_and_filter_top_recipes():
    print("📥 جلب قاعدة البيانات المفتوحة تلقائياً داخل السيرفر...")
    
    try:
        # إرسال الطلب مع ترويسة User-Agent لتجنب أي حظر من السيرفر
        req = urllib.request.Request(
            DATASET_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        print(f"📊 تم إيجاد {len(data)} وصفة خام! جاري التصفية واستخراج الأفضل...")

        recipes_list = []
        for idx, item in enumerate(data):
            # استخراج وتنظيف الحقول الأساسية لكل وصفة
            title = item.get('title') or item.get('name') or "Delicious Recipe"
            ingredients = item.get('ingredients') or []
            instructions = item.get('instructions') or item.get('directions') or item.get('steps') or []
            
            # تجاهل الوصفات الناقصة
            if not ingredients or not instructions:
                continue

            recipe = {
                "id": len(recipes_list) + 1,
                "title": str(title).strip(),
                "category": str(item.get('category', 'Main Course')),
                "description": str(item.get('description', '')),
                "prepTime": str(item.get('prep_time', '15m')),
                "cookTime": str(item.get('cook_time', '20m')),
                "ingredients": ingredients if isinstance(ingredients, list) else [str(ingredients)],
                "instructions": instructions if isinstance(instructions, list) else [str(instructions)],
                "rating": float(item.get('rating', 5.0))
            }
            recipes_list.append(recipe)
            
            # التوقف عند الوصول للعدد المطلوب
            if len(recipes_list) >= 20000:
                break

        with open('raw_recipes.json', 'w', encoding='utf-8') as f:
            json.dump(recipes_list, f, ensure_ascii=False, indent=2)

        print(f"✅ تم إنشاء raw_recipes.json بنجاح وبداخله {len(recipes_list)} وصفة جاهزة!")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء جلب البيانات: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_filter_top_recipes()

