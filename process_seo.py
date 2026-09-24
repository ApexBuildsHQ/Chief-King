import os
import json
import argparse
import requests

# إعدادات Ollama ونموذج الذكاء الاصطناعي
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def optimize_title_with_ai(original_name, category):
    """
    تحليل اسم الوصفة واستبداله بالاسم الأشهر والأكثر بحثاً في محركات البحث العالمية (SEO)
    وإرجاع أسماء بديلة شائعة أيضاً.
    """
    prompt = f"""
You are a World-Class Food & Recipe SEO Expert.
Task: Convert the given recipe title into the most searched, popular, high-volume search term used on Google globally.

Original Title: "{original_name}"
Category: "{category}"

Rules:
1. 'name': The single most popular, highly searched standard English title (e.g. "Jo Mama Spaghetti" -> "Classic Spaghetti with Meat Sauce").
2. 'alternateName': An array of 2 to 3 other widely searched titles/keywords for this exact dish.
3. Return ONLY valid JSON format with no additional conversation:
{{
  "name": "Most Popular SEO Title",
  "alternateName": ["Alternative Search Term 1", "Alternative Search Term 2"]
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"  # إجبار النموذج على إرجاع JSON نظيف
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=40)
        if response.status_code == 200:
            result_text = response.json().get("response", "{}")
            data = json.loads(result_text)
            
            seo_name = data.get("name", original_name)
            alt_names = data.get("alternateName", [])
            
            if isinstance(alt_names, str):
                alt_names = [alt_names]
                
            return seo_name, alt_names
    except Exception as e:
        print(f"  ⚠️ [AI Warning] Failed for '{original_name}': {e}")
    
    return original_name, []

def main():
    parser = argparse.ArgumentParser(description="SEO Optimization for a specific chunk.")
    parser.add_argument("--chunk", type=int, required=True, help="Chunk ID (1 to 20)")
    args = parser.parse_args()

    chunk_id = args.chunk
    
    # المسارات بناءً على المجلد المعروض في مشروعك
    input_file = f"output_recipes_2/recipes_chunk_{chunk_id}.json"
    output_dir = "output_recipes_seo"
    output_file = os.path.join(output_dir, f"recipes_chunk_{chunk_id}.json")

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    print(f"🚀 [Server #{chunk_id}] Starting SEO AI process for: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    total_recipes = len(recipes)
    print(f"📋 Loaded {total_recipes} recipes.")

    for idx, recipe in enumerate(recipes):
        orig_name = recipe.get("name", "")
        category = recipe.get("recipeCategory", "")

        # معالجة الاسم والـ SEO بالذكاء الاصطناعي
        seo_name, alt_names = optimize_title_with_ai(orig_name, category)
        
        recipe["name"] = seo_name
        if alt_names:
            recipe["alternateName"] = alt_names

        # طباعة تقدم العمل كل 50 وصفة
        if (idx + 1) % 50 == 0 or (idx + 1) == total_recipes:
            print(f"  ➜ [Server #{chunk_id}]: Processed {idx + 1}/{total_recipes} recipes...")

    # حفظ الملف الناتج المنظم
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"✅ [Server #{chunk_id}] Saved optimized file to: {output_file}")

if __name__ == "__main__":
    main()

