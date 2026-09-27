import os
import sys
import json
import time
import argparse
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# تفعيل الطباعة الفورية اللحظية في مجرى الإخراج
sys.stdout.reconfigure(line_buffering=True)

# خريطة أكواد اللغات الـ 50 لنموذج Meta NLLB-200
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

def translate_text(text, translator, target_lang_code):
    if not text or not isinstance(text, str):
        return text
    try:
        res = translator(text, tgt_lang=target_lang_code, max_length=512)
        return res[0]['translation_text']
    except Exception as e:
        print(f"      [!] Warning: Translation failed for text fragment. Error: {e}", flush=True)
        return text

def process_translation_chunk(chunk_id):
    start_time = time.time()
    print(f"\n==================================================", flush=True)
    print(f"[Server #{chunk_id}] STARTING TRANSLATION & CHUNKING PROCESS", flush=True)
    print(f"==================================================\n", flush=True)

    # 1. تحميل النموذج
    print(f"[Server #{chunk_id}] [Step 1/4] Loading Meta NLLB-200 Model into memory...", flush=True)
    model_name = "facebook/nllb-200-distilled-600M"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    translator = pipeline('translation', model=model, tokenizer=tokenizer, src_lang="eng_Latn")
    print(f"[Server #{chunk_id}] [Step 1/4] Model loaded successfully!\n", flush=True)

    # 2. قراءة الملف الأساسي
    input_file = f"output_recipes_seo_2/chunk_recipes_{chunk_id}.json"
    print(f"[Server #{chunk_id}] [Step 2/4] Reading source JSON file: {input_file}", flush=True)
    
    if not os.path.exists(input_file):
        print(f"[CRITICAL ERROR] File not found: {input_file}", flush=True)
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    total_recipes = len(recipes)
    base_chunk_num = (chunk_id - 1) * 10 + 1
    print(f"[Server #{chunk_id}] Loaded {total_recipes} recipes. Target Chunk ID range: {base_chunk_num} to {base_chunk_num + 9}\n", flush=True)

    # 3. معالجة اللغات المحددة
    print(f"[Server #{chunk_id}] [Step 3/4] Starting 50 Languages Processing Loop...\n", flush=True)
    
    total_languages = len(NLLB_LANG_MAP)
    for lang_idx, (lang_key, nllb_code) in enumerate(NLLB_LANG_MAP.items(), 1):
        lang_start_time = time.time()
        print(f"---> [{lang_idx}/{total_languages}] Processing Language: '{lang_key.upper()}' ({nllb_code})", flush=True)

        is_english = (lang_key == 'en')
        if is_english:
            print(f"     [Info] English language detected: Bypassing AI translation (Direct Parsing)...", flush=True)

        translated_recipes = []

        for idx, recipe in enumerate(recipes, 1):
            sub_chunk_offset = (idx - 1) // 100
            current_chunk_num = base_chunk_num + sub_chunk_offset

            # الترجمة أو التجاوز المباشر إذا كانت اللغة إنجليزية
            translated_recipe = {
                "id": str(recipe.get("id")),
                "name": translate_text(recipe.get("name", ""), translator, nllb_code) if not is_english else recipe.get("name"),
                "category": translate_text(recipe.get("category", "Main"), translator, nllb_code) if not is_english else recipe.get("category", "Main"),
                "instructions": translate_text(recipe.get("instructions", ""), translator, nllb_code) if not is_english else recipe.get("instructions"),
                "ingredients": [translate_text(ing, translator, nllb_code) for ing in recipe.get("ingredients", [])] if not is_english else recipe.get("ingredients", []),
                "c": current_chunk_num
            }
            translated_recipes.append(translated_recipe)

            # طباعة نسبة التقدم كل 100 وصفة
            if idx % 100 == 0 or idx == total_recipes:
                pct = (idx / total_recipes) * 100
                print(f"     Progress [{lang_key.upper()}]: {idx}/{total_recipes} recipes completed ({pct:.0f}%)", flush=True)

        # 4. التفكيك والحفظ إلى ملفات تحتوي على 100 وصفة
        print(f"     Saving 100-recipe files for language '{lang_key}'...", flush=True)
        for i in range(0, len(translated_recipes), 100):
            sub_list = translated_recipes[i:i+100]
            current_chunk_num = base_chunk_num + (i // 100)
            
            output_dir = f"public/data/recipes/{lang_key}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = f"{output_dir}/chunk_{current_chunk_num}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sub_list, f, ensure_ascii=False, indent=2)
            
            print(f"     [✓ Created File] {output_path} (Contains {len(sub_list)} recipes)", flush=True)

        elapsed_lang = time.time() - lang_start_time
        print(f"---> Finished '{lang_key.upper()}' in {elapsed_lang:.2f} seconds.\n", flush=True)

    total_time = time.time() - start_time
    print(f"==================================================", flush=True)
    print(f"[Server #{chunk_id}] ALL JOBS COMPLETED SUCCESSFULLY IN {total_time/60:.2f} MINUTES!", flush=True)
    print(f"==================================================\n", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-id", type=int, required=True)
    args = parser.parse_args()
    process_translation_chunk(args.chunk_id)
