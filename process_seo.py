import os
import json
import argparse
import requests

# إعدادات Ollama ونموذج الذكاء الاصطناعي الخفيف والسريع للـ CPU
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

def optimize_title_with_ai(original_name, category):
    """
    تحليل اسم الوصفة واستبداله بالاسم الأشهر والأكثر بحثاً في محركات البحث العالمية (SEO)
    مع ضمان صياغة بشرية طبيعية وسلسة وبدون تكرار أو أخطاء تركيبية.
    """
    prompt = f"""
You are a World-Class Food & Recipe SEO Expert and Professional English Copywriter.
Task: Convert the given recipe title into the most searched, popular, and high-volume title on Google globally, while ensuring it sounds 100% natural to native English speakers.

Original Title: "{original_name}"
Category: "{category}"

STRICT RULES FOR SEO & WRITING:
1. 'name': High-volume search title that sounds completely natural and grammatically perfect.
   - Fix possessives and orphan letters (e.g., "Jansson S" -> "Jansson's", "Tgi Friday S" -> "TGI Friday's").
   - NEVER awkwardly tack words onto the end (e.g., DO NOT output "Pork Chops with Pears Grilled", write "Grilled Pork Chops with Pears").
   - NEVER repeat redundant words (e.g., DO NOT output "Ice Coffee Cubes Iced Coffee", write "Iced Coffee with Coffee Cubes").
   - Preserve important cooking terms and details (e.g., keep "Ground Chicken", "Fried Rice for 2").
2. 'alternateName': An array of 2 to 3 natural alternative search terms/keywords for this exact dish.
3. Return ONLY valid JSON format:
{{
  "name": "Natural SEO Title",
  "alternateName": ["Alternative Search Term 1", "Alternative Search Term 2"]
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "num_predict": 128,  # تسريع الإجابة
            "temperature": 0.2   # تخفيض الحرارة لضمان الالتزام الصارم بالقواعد والقواعد النحوية
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=20)
        if response.status_code == 200:
            result_text = response.json().get("response", "{}")
            data = json.loads(result_text)
            
            seo_name = data.get("name", original_name)
            alt_names = data.get("alternateName", [])
            
            if isinstance(alt_names, str):
                alt_names = [alt_names]
                
            return seo_name, alt_names
    except Exception as e:
        pass
    
    return original_name, []

def main():
    parser = argparse.ArgumentParser(description="SEO Optimization for a specific chunk.")
    parser.add_argument("--chunk", type=int, required=True, help="Chunk ID (1 to 20)")
    args = parser.parse_args()

    chunk_id = args.chunk
    
    input_file = f"output_recipes_2/recipes_chunk_{chunk_id}.json"
    output_dir = "output_recipes_seo"
    output_file = os.path.join(output_dir, f"recipes_chunk_{chunk_id}.json")

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}", flush=True)
        return

    print(f"🚀 [Server #{chunk_id}] Starting SEO AI process for: {input_file}", flush=True)

    with open(input_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    total_recipes = len(recipes)
    print(f"📋 Loaded {total_recipes} recipes from {input_file}", flush=True)

    for idx, recipe in enumerate(recipes):
        orig_name = recipe.get("name", "")
        category = recipe.get("recipeCategory", "")

        # معالجة الاسم والـ SEO بالذكاء الاصطناعي
        seo_name, alt_names = optimize_title_with_ai(orig_name, category)
        
        recipe["name"] = seo_name
        if alt_names:
            recipe["alternateName"] = alt_names

        # طباعة فورية ومباشرة لكل وصفة يتم تعديلها تظهر فوراً في سجل السيرفر
        print(f"[{idx + 1}/{total_recipes}] Processed: '{orig_name}' ➜ '{seo_name}'", flush=True)

    # حفظ الملف الناتج
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"✅ [Server #{chunk_id}] Finished & Saved to: {output_file}", flush=True)

if __name__ == "__main__":
    main()

