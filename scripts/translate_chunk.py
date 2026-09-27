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

def translate_text(text, model, tokenizer, target_lang_code):
    if not text or not isinstance(text, str):
        return text if text else ""
    try:
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        target_lang_id = tokenizer.convert_tokens_to_ids(target_lang_code)
        
        with torch.no_grad():
            translated_tokens = model.generate(
                **inputs,
                forced_bos_token_id=target_lang_id,
                max_length=512
            )
            
        return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
    except Exception as e:
        print(f"      [!] Warning: Translation failed for text fragment. Error: {e}", flush=True)
        return text

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
    print(f"[Server #{chunk_id}] STARTING TRANSLATION & CHUNKING PROCESS", flush=True)
    print(f"==================================================\n", flush=True)

    print(f"[Server #{chunk_id}] [Step 1/3] Loading Meta NLLB-200 Model...", flush=True)
    model_name = "facebook/nllb-200-distilled-600M"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.src_lang = "eng_Latn"
    
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model.eval()

    input_file = f"output_recipes_seo_2/chunk_recipes_{chunk_id}.json"
    print(f"[Server #{chunk_id}] [Step 2/3] Reading source JSON file: {input_file}", flush=True)
    
    if not os.path.exists(input_file):
        print(f"[CRITICAL ERROR] File not found: {input_file}", flush=True)
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    total_recipes = len(recipes)
    base_chunk_num = (chunk_id - 1) * 10 + 1

    print(f"[Server #{chunk_id}] [Step 3/3] Starting 50 Languages Processing Loop...\n", flush=True)
    
    total_languages = len(NLLB_LANG_MAP)
    for lang_idx, (lang_key, nllb_code) in enumerate(NLLB_LANG_MAP.items(), 1):
        lang_start_time = time.time()
        print(f"---> [{lang_idx}/{total_languages}] Processing Language: '{lang_key.upper()}' ({nllb_code})", flush=True)

        is_english = (lang_key == 'en')
        translated_recipes = []

        for idx, recipe in enumerate(recipes, 1):
            sub_chunk_offset = (idx - 1) // 100
            current_chunk_num = base_chunk_num + sub_chunk_offset

            raw_name = recipe.get("name", "")
            raw_category = recipe.get("recipeCategory", "General")
            raw_description = recipe.get("description", "")
            raw_ingredients = recipe.get("recipeIngredient", [])
            raw_instructions = extract_instructions(recipe)

            if is_english:
                translated_name = raw_name
                translated_category = raw_category
                translated_description = raw_description
                translated_ingredients = raw_ingredients
                translated_instructions = raw_instructions
            else:
                translated_name = translate_text(raw_name, model, tokenizer, nllb_code)
                translated_category = translate_text(raw_category, model, tokenizer, nllb_code)
                translated_description = translate_text(raw_description, model, tokenizer, nllb_code)
                translated_ingredients = [translate_text(ing, model, tokenizer, nllb_code) for ing in raw_ingredients]
                translated_instructions = [translate_text(step, model, tokenizer, nllb_code) for step in raw_instructions]

            translated_recipe = {
                "id": str(recipe.get("id")),
                "name": translated_name,
                "category": translated_category,
                "description": translated_description,
                "image": recipe.get("image", ""),  # إضافة رابط الصورة لحفظه واستخراجه لاحقاً
                "prepTime": recipe.get("prepTime", ""),
                "cookTime": recipe.get("cookTime", ""),
                "totalTime": recipe.get("totalTime", ""),
                "yield": recipe.get("recipeYield", ""),
                "ingredients": translated_ingredients,
                "instructions": translated_instructions,
                "nutrition": recipe.get("nutrition", {}),
                "c": current_chunk_num
            }
            translated_recipes.append(translated_recipe)

        for i in range(0, len(translated_recipes), 100):
            sub_list = translated_recipes[i:i+100]
            current_chunk_num = base_chunk_num + (i // 100)
            
            output_dir = f"public/data/recipes/{lang_key}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = f"{output_dir}/chunk_{current_chunk_num}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sub_list, f, ensure_ascii=False, indent=2)

        elapsed_lang = time.time() - lang_start_time
        print(f"---> Finished '{lang_key.upper()}' in {elapsed_lang:.2f} seconds.", flush=True)

    total_time = time.time() - start_time
    print(f"\n[Server #{chunk_id}] COMPLETED IN {total_time/60:.2f} MINUTES!\n", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-id", type=int, required=True)
    args = parser.parse_args()
    process_translation_chunk(args.chunk_id)
