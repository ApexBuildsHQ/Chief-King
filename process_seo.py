import os
import json
import argparse
import requests
import re

# إعدادات Ollama ونموذج الذكاء الاصطناعي الخفيف والسريع للـ CPU
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

def clean_title(title, original_name):
    """
    تنظيف آلي صارم للعنوان لمنع تسريب نصوص التعليمات أو العلامات المقتبسة الزائدة.
    """
    if not title or not isinstance(title, str):
        return original_name

    # إزالة أي عبارات تسريب من الـ Prompt مثل "Natural SEO Title:" أو "SEO Title:"
    cleaned = re.sub(r'^(natural\s+)?seo\s+title\s*:?\s*', '', title, flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip('"' + "'").strip()

    # إذا تم تفريغ الاسم أو بقى كلمة توضيحية فقط، نرجع إلى الاسم الأصلي
    if not cleaned or cleaned.lower() in ["natural seo title", "seo title", "title", "recipe title", "null"]:
        return original_name

    return cleaned

def optimize_title_with_ai(original_name, category):
    """
    تحليل اسم الوصفة واستبداله بالاسم الأشهر والأكثر بحثاً في محركات البحث العالمية (SEO)
    مع ضمان صياغة بشرية طبيعية، منع الهلوسة، وتنظيف آلي صريح للمخرجات.
    """
    prompt = f"""You are a World-Class Food & Recipe SEO Expert and Professional English Copywriter.
Task: Rephrase the given recipe title into a high-volume, natural, grammatically correct Google search term.

Original Title: "{original_name}"
Category: "{category}"

STRICT RULES:
1. 'name': Most searched, natural English recipe title.
   - Remove orphan usernames/noise (e.g., "Kittencal S", "Camie S", "Marilyn S").
   - Fix possessives (e.g., "Houlihan S" -> "Houlihan's", "Jansson S" -> "Jansson's").
   - NEVER add new main ingredients that are not in the original title (e.g., DO NOT add chicken to a dessert/caramel corn).
   - NEVER output placeholder text like "Natural SEO Title" or "SEO Title".
   - Maintain natural English word order (e.g., "Grilled Pork Chops" NOT "Pork Chops Grilled").
2. 'alternateName': Array of 2 to 3 natural alternative search terms for this exact dish.
3. Return ONLY valid JSON matching this exact structure:
{{
  "name": "Classic Homemade Lasagna",
  "alternateName": ["Easy Beef Lasagna", "Best Italian Lasagna"]
}}"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "num_predict": 128,  # تسريع الإجابة
            "temperature": 0.1   # درجة حرارة منخفضة جداً لمنع الهلوسة والالتزام الصارم
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=20)
        if response.status_code == 200:
            result_text = response.json().get("response", "{}")
            data = json.loads(result_text)
            
            raw_seo_name = data.get("name", original_name)
            alt_names = data.get("alternateName", [])
            
            # تنظيف آلي صارم للعنوان الناتج
            seo_name = clean_title(raw_seo_name, original_name)
            
            cleaned_alt_names = []
            if isinstance(alt_names, list):
                for alt in alt_names:
                    cleaned_alt = clean_title(alt, "")
                    if cleaned_alt and cleaned_alt.lower() != seo_name.lower():
                        cleaned_alt_names.append(cleaned_alt)
            elif isinstance(alt_names, str):
                cleaned_alt = clean_title(alt_names, "")
                if cleaned_alt and cleaned_alt.lower() != seo_name.lower():
                    cleaned_alt_names.append(cleaned_alt)
                
            return seo_name, cleaned_alt_names
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

