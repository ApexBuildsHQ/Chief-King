import pandas as pd
import json

# رابط مباشر لقاعدة بيانات Food.com الضخمة المفتوحة على HuggingFace (تضم +230 ألف وصفة)
DATASET_PARQUET_URL = "https://huggingface.co/datasets/mbien/food-com-recipes/resolve/main/data/train-00000-of-00001.parquet"

def fetch_and_filter_top_recipes():
    print("📥 جلب قاعدة بيانات Food.com العالمية الضخمة من Hugging Face...")
    
    try:
        # قراءة قاعدة البيانات مباشرة إلى Pandas Dataframe
        df = pd.read_parquet(DATASET_PARQUET_URL)
        print(f"📊 تم إيجاد {len(df)} وصفة عالمية حقيقية! جاري الفرز والتصفية...")

        # تنظيف البيانات وفرزها حسب الأعلى تقييماً (Rating / Review Count)
        if 'rating' in df.columns:
            df = df.sort_values(by='rating', ascending=False)
        
        # اختيار أعلى 20,000 وصفة
        top_20k_df = df.head(20000)

        recipes_list = []
        for idx, row in top_20k_df.iterrows():
            recipe = {
                "id": len(recipes_list) + 1,
                "title": str(row.get('name') or row.get('title') or "Recipe"),
                "category": str(row.get('category', 'Main Course')),
                "description": str(row.get('description', '')),
                "prepTime": f"{row.get('minutes', 15)}m",
                "cookTime": "20m",
                "ingredients": list(row.get('ingredients', [])) if isinstance(row.get('ingredients'), (list, tuple)) else [],
                "instructions": list(row.get('steps', [])) if isinstance(row.get('steps'), (list, tuple)) else [],
                "rating": float(row.get('rating', 5.0))
            }
            recipes_list.append(recipe)

        with open('raw_recipes.json', 'w', encoding='utf-8') as f:
            json.dump(recipes_list, f, ensure_ascii=False, indent=2)

        print(f"✅ تم إنشاء raw_recipes.json بنجاح بأعلى {len(recipes_list)} وصفة عالمية حقيقية!")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء معالجة البيانات: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_filter_top_recipes()

