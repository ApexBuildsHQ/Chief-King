import json
from datasets import load_dataset

def fetch_and_filter_top_recipes():
    print("📥 جلب قاعدة بيانات الوصفات العالمية عبر Hugging Face Datasets...")
    
    try:
        # تحميل قاعدة البيانات عبر المكتبة الرسمية لمنع أخطاء الروابط والـ HTTP
        dataset = load_dataset("mbien/food-com-recipes", split="train")
        print(f"📊 تم إيجاد {len(dataset)} وصفة! جاري التصفية والتنسيق...")

        recipes_list = []
        for item in dataset:
            title = item.get('name') or item.get('title')
            ingredients = item.get('ingredients')
            instructions = item.get('steps') or item.get('instructions')
            
            # استبعاد أي وصفة غير مكتملة
            if not title or not ingredients or not instructions:
                continue

            recipe = {
                "id": len(recipes_list) + 1,
                "title": str(title).strip(),
                "category": str(item.get('category', 'Main Course')),
                "description": str(item.get('description', '')),
                "prepTime": f"{item.get('minutes', 15)}m",
                "cookTime": "20m",
                "ingredients": list(ingredients) if isinstance(ingredients, (list, tuple)) else [str(ingredients)],
                "instructions": list(instructions) if isinstance(instructions, (list, tuple)) else [str(instructions)],
                "rating": float(item.get('rating', 5.0))
            }
            recipes_list.append(recipe)
            
            # التوقف فور الوصول للعدد المطلوب
            if len(recipes_list) >= 20000:
                break

        with open('raw_recipes.json', 'w', encoding='utf-8') as f:
            json.dump(recipes_list, f, ensure_ascii=False, indent=2)

        print(f"✅ تم إنشاء raw_recipes.json بنجاح وبداخله {len(recipes_list)} وصفة حقيقية!")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء جلب البيانات: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_filter_top_recipes()

