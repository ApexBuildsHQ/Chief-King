import os
import sys
import json
import time
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

sys.stdout.reconfigure(line_buffering=True)

NLLB_LANG_MAP = {
    'ar': 'ara_Arab', 'en': 'eng_Latn', 'fr': 'fra_Latn', 'es': 'spa_Latn', 'de': 'deu_Latn',
    'it': 'ita_Latn', 'pt': 'por_Latn', 'ru': 'rus_Cyrl', 'zh': 'zho_Hans', 'ja': 'jpn_Jpan',
    'ko': 'kor_Hang', 'hi': 'hin_Deva', 'tr': 'tur_Latn', 'nl': 'nld_Latn', 'pl': 'pol_Latn',
    'sv': 'swe_Latn', 'fa': 'fas_Arab', 'ur': 'urd_Arab', 'id': 'ind_Latn', 'vi': 'vie_Latn',
    'th': 'tha_Thai', 'el': 'ell_Grek', 'he': 'heb_Hebr', 'hu': 'hun_Latn', 'cs': 'ces_Latn',
    'ro': 'ron_Latn', 'da': 'dan_Latn', 'fi': 'fin_Latn', 'no': 'nob_Latn', 'uk': 'ukr_Cyrl',
    'bg': 'bul_Cyrl', 'sk': 'slk_Latn', 'hr': 'hrv_Latn', 'sr': 'srp_Cyrl', 'lt': 'lit_Latn',
    'sl': 'slv_Latn', 'et': 'est_Latn', 'lv': 'lav_Latn', 'sw': 'swh_Latn', 'ms': 'zsm_Latn',
    'fil': 'tgl_Latn', 'bn': 'ben_Beng', 'ta': 'tam_Taml', 'te': 'tel_Telu', 'mr': 'mar_Deva',
    'gu': 'guj_Gujr', 'kn': 'kan_Knda', 'ml': 'mal_Mlym', 'pa': 'pan_Guru', 'ne': 'nep_Deva'
}

def translate_batch(texts_list, model, tokenizer, target_lang_code, batch_size=32):
    """ترجمة قائمة من النصوص دفعة واحدة (Batching) لتسريع الأداء 5 أضعاف دون المساس بالدقة"""
    if not texts_list:
        return []
    
    translated_results = []
    target_lang_id = tokenizer.convert_tokens_to_ids(target_lang_code)

    for i in range(0, len(texts_list), batch_size):
        batch = texts_list[i:i + batch_size]
        # معالجة النصوص الفارغة تجنباً لأخطاء التوكنايزر
        safe_batch = [str(t) if t else "" for t in batch]
        
        try:
            inputs = tokenizer(safe_batch, return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                tokens = model.generate(
                    **inputs,
                    forced_bos_token_id=target_lang_id,
                    max_length=512
                )
            decoded = tokenizer.batch_decode(tokens, skip_special_tokens=True)
            translated_results.extend(decoded)
        except Exception as e:
            print(f"      [!] Batch Translation Error: {e}. Falling back to original texts.", flush=True)
            translated_results.extend(safe_batch)

    return translated_results

def extract_instructions(recipe_data):
    raw_instructions = recipe_data.get("recipeInstructions", [])
    instructions = []
    
    if isinstance(raw_instructions, list):
        for item in raw_instructions:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    instructions.append(text)
            elif isinstance(item, str) and item.strip():
                instructions.append(item.strip())
    elif isinstance(raw_instructions, str):
        instructions.append(raw_instructions)
        
    return instructions

def process_translation_chunk(chunk_id):
    start_time = time.time()
    print(f"\n==================================================", flush=True)
    print(f"[Server #{chunk_id}] STARTING OPTIMIZED TRANSLATION & CHUNKING", flush=True)
    print(f"==================================================\n", flush=True)

    input_file = f"output_recipes_seo_2/chunk_recipes_{chunk_id}.json"
    if not os.path.exists(input_file):
        print(f"[CRITICAL ERROR] File not found: {input_file}", flush=True)
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    total_recipes = len(recipes)
    base_chunk_num = (chunk_id - 1) * 10 + 1

    print(f"[Server #{chunk_id}] Loading Meta NLLB-200 Model...", flush=True)
    model_name = "facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.src_lang = "eng_Latn"
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model.eval()

    total_languages = len(NLLB_LANG_MAP)
    
    for lang_idx, (lang_key, nllb_code) in enumerate(NLLB_LANG_MAP.items(), 1):
        output_dir = f"public/data/recipes/{lang_key}"
        os.makedirs(output_dir, exist_ok=True)
        
        # ميزة حفظ التقدم: التحقق هل تم ترجمة كافة الكتل لهذه اللغة مسبقاً لتخطيها
        expected_chunks = [(base_chunk_num + (i // 100)) for i in range(0, total_recipes, 100)]
        all_exist = all(os.path.exists(f"{output_dir}/chunk_{c_num}.json") for c_num in expected_chunks)
        
        if all_exist:
            print(f"---> [{lang_idx}/{total_languages}] Skipping '{lang_key.upper()}': All chunk files already exist.", flush=True)
            continue

        lang_start_time = time.time()
        print(f"---> [{lang_idx}/{total_languages}] Processing Language: '{lang_key.upper()}' ({nllb_code})", flush=True)

        is_english = (lang_key == 'en')
        translated_recipes = []

        if is_english:
            for idx, recipe in enumerate(recipes, 1):
                sub_chunk_offset = (idx - 1) // 100
                current_chunk_num = base_chunk_num + sub_chunk_offset
                translated_recipes.append({
                    "id": str(recipe.get("id")),
                    "name": recipe.get("name", ""),
                    "category": recipe.get("recipeCategory", "General"),
                    "description": recipe.get("description", ""),
                    "image": recipe.get("image", ""),
                    "prepTime": recipe.get("prepTime", ""),
                    "cookTime": recipe.get("cookTime", ""),
                    "totalTime": recipe.get("totalTime", ""),
                    "yield": recipe.get("recipeYield", ""),
                    "ingredients": recipe.get("recipeIngredient", []),
                    "instructions": extract_instructions(recipe),
                    "nutrition": recipe.get("nutrition", {}),
                    "c": current_chunk_num
                })
        else:
            # معالجة وترجمة النصوص بتجميع ذكي (Batching)
            names = [r.get("name", "") for r in recipes]
            categories = [r.get("recipeCategory", "General") for r in recipes]
            descriptions = [r.get("description", "") for r in recipes]

            trans_names = translate_batch(names, model, tokenizer, nllb_code)
            trans_categories = translate_batch(categories, model, tokenizer, nllb_code)
            trans_descriptions = translate_batch(descriptions, model, tokenizer, nllb_code)

            for idx, recipe in enumerate(recipes):
                sub_chunk_offset = idx // 100
                current_chunk_num = base_chunk_num + sub_chunk_offset

                raw_ingredients = recipe.get("recipeIngredient", [])
                raw_instructions = extract_instructions(recipe)

                # ترجمة قوائم المكونات والخطوات لكل وصفة كـ Batch سريع
                trans_ing = translate_batch(raw_ingredients, model, tokenizer, nllb_code) if raw_ingredients else []
                trans_inst = translate_batch(raw_instructions, model, tokenizer, nllb_code) if raw_instructions else []

                translated_recipes.append({
                    "id": str(recipe.get("id")),
                    "name": trans_names[idx],
                    "category": trans_categories[idx],
                    "description": trans_descriptions[idx],
                    "image": recipe.get("image", ""),
                    "prepTime": recipe.get("prepTime", ""),
                    "cookTime": recipe.get("cookTime", ""),
                    "totalTime": recipe.get("totalTime", ""),
                    "yield": recipe.get("recipeYield", ""),
                    "ingredients": trans_ing,
                    "instructions": trans_inst,
                    "nutrition": recipe.get("nutrition", {}),
                    "c": current_chunk_num
                })

        # حفظ الملفات فور الانتهاء من اللغة
        for i in range(0, len(translated_recipes), 100):
            sub_list = translated_recipes[i:i+100]
            current_chunk_num = base_chunk_num + (i // 100)
            output_path = f"{output_dir}/chunk_{current_chunk_num}.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sub_list, f, ensure_ascii=False, indent=2)

        elapsed_lang = time.time() - lang_start_time
        print(f"     [✓ Done] '{lang_key.upper()}' finished in {elapsed_lang:.2f}s", flush=True)

    total_time = time.time() - start_time
    print(f"\n[Server #{chunk_id}] PROCESS COMPLETED IN {total_time/60:.2f} MINUTES!\n", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-id", type=int, required=True)
    args = parser.parse_args()
    process_translation_chunk(args.chunk_id)
