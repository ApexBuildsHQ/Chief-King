import os
import sys
import json
import time
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# استغلال أنواة المعالج المتاحة بكفاءة
torch.set_num_threads(2)
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

def translate_flat_list(texts_list, model, tokenizer, target_lang_code, batch_size=16, label="Texts"):
    """ترجمة قائمة مفرودة كاملة من النصوص مع إظهار نسبة التقدم الحية في السجلات"""
    if not texts_list:
        return []
    
    translated_results = []
    target_lang_id = tokenizer.convert_tokens_to_ids(target_lang_code)
    total = len(texts_list)
    last_printed_pct = -1

    for i in range(0, total, batch_size):
        batch = texts_list[i:i + batch_size]
        safe_batch = [str(t) if (t is not None and str(t).strip()) else " " for t in batch]
        
        try:
            inputs = tokenizer(safe_batch, return_tensors="pt", padding=True, truncation=True, max_length=256)
            with torch.no_grad():
                tokens = model.generate(
                    **inputs,
                    forced_bos_token_id=target_lang_id,
                    max_length=256
                )
            decoded = tokenizer.batch_decode(tokens, skip_special_tokens=True)
            translated_results.extend(decoded)
        except Exception as e:
            translated_results.extend(safe_batch)

        # طباعة نسبة التقدم المباشرة في السجلات
        current_pct = int(((i + len(batch)) / total) * 100)
        if current_pct % 20 == 0 and current_pct != last_printed_pct:
            print(f"      [Progress] {label}: {current_pct}% ({i + len(batch)}/{total})", flush=True)
            last_printed_pct = current_pct

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
    print(f"[Server #{chunk_id}] STARTING ULTRA-OPTIMIZED TRANSLATION", flush=True)
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
        
        expected_chunks = [(base_chunk_num + (i // 100)) for i in range(0, total_recipes, 100)]
        all_exist = all(os.path.exists(f"{output_dir}/chunk_{c_num}.json") for c_num in expected_chunks)
        
        if all_exist:
            print(f"---> [{lang_idx}/{total_languages}] Skipping '{lang_key.upper()}': Already completed.", flush=True)
            continue

        lang_start_time = time.time()
        print(f"\n---> [{lang_idx}/{total_languages}] Processing Language: '{lang_key.upper()}' ({nllb_code})", flush=True)

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
            # 1. تسطيح وتجميع كافة نصوص الـ 1000 وصفة لتسريع معالجة المصفوفات
            names = [r.get("name", "") for r in recipes]
            categories = [r.get("recipeCategory", "General") for r in recipes]
            descriptions = [r.get("description", "") for r in recipes]

            all_ingredients = []
            ing_spans = []
            all_instructions = []
            inst_spans = []

            for r in recipes:
                ings = r.get("recipeIngredient", [])
                st_ing = len(all_ingredients)
                all_ingredients.extend(ings)
                ing_spans.append((st_ing, len(all_ingredients)))

                insts = extract_instructions(r)
                st_inst = len(all_instructions)
                all_instructions.extend(insts)
                inst_spans.append((st_inst, len(all_instructions)))

            # 2. الترجمة دفعة واحدة بكفاءة عالية على المعالج
            trans_names = translate_flat_list(names, model, tokenizer, nllb_code, batch_size=16, label="Names")
            trans_categories = translate_flat_list(categories, model, tokenizer, nllb_code, batch_size=16, label="Categories")
            trans_descriptions = translate_flat_list(descriptions, model, tokenizer, nllb_code, batch_size=16, label="Descriptions")
            trans_all_ingredients = translate_flat_list(all_ingredients, model, tokenizer, nllb_code, batch_size=16, label="Ingredients")
            trans_all_instructions = translate_flat_list(all_instructions, model, tokenizer, nllb_code, batch_size=16, label="Instructions")

            # 3. إعادة بناء كائنات الوصفات بنفس الهيكل الأصلي
            for idx, recipe in enumerate(recipes):
                sub_chunk_offset = idx // 100
                current_chunk_num = base_chunk_num + sub_chunk_offset

                st_ing, en_ing = ing_spans[idx]
                recipe_ing = trans_all_ingredients[st_ing:en_ing]

                st_inst, en_inst = inst_spans[idx]
                recipe_inst = trans_all_instructions[st_inst:en_inst]

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
                    "ingredients": recipe_ing,
                    "instructions": recipe_inst,
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
        print(f"     [✓ Done] '{lang_key.upper()}' finished in {elapsed_lang:.2f}s ({elapsed_lang/60:.2f} min)", flush=True)

    total_time = time.time() - start_time
    print(f"\n[Server #{chunk_id}] PROCESS COMPLETED IN {total_time/60:.2f} MINUTES!\n", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-id", type=int, required=True)
    args = parser.parse_args()
    process_translation_chunk(args.chunk_id)
