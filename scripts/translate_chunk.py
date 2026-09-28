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

# خريطة الـ 50 لغة المعتمدة لنموذج NLLB-200
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

NUTRITION_KEYS = [
    "calories", "fatContent", "saturatedFatContent", "cholesterolContent",
    "sodiumContent", "carbohydrateContent", "fiberContent", "sugarContent", "proteinContent"
]

def translate_flat_list(texts_list, model, tokenizer, target_lang_code, batch_size=16, label="Texts"):
    """ترجمة قائمة مفرودة كاملة من النصوص بسرعة مع إظهار نسبة التقدم الحية"""
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
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
                
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

        current_pct = int(((i + len(batch)) / total) * 100)
        if current_pct % 20 == 0 and current_pct != last_printed_pct:
            print(f"      [Progress] {label}: {current_pct}% ({i + len(batch)}/{total})", flush=True)
            last_printed_pct = current_pct

    return translated_results

def extract_instructions(recipe_data):
    """استخراج نصوص الخطوات سواء كانت مصفوفة نصية أو كائنات HowToStep"""
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
    print(f"[Server #{chunk_id}] STARTING FULL RECIPE TRANSLATION", flush=True)
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
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)
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
                
                item = recipe.copy()
                item["id"] = str(recipe.get("id"))
                item["category"] = recipe.get("recipeCategory", recipe.get("category", "General"))
                item["yield"] = recipe.get("recipeYield", recipe.get("yield", ""))
                item["ingredients"] = recipe.get("recipeIngredient", recipe.get("ingredients", []))
                item["instructions"] = extract_instructions(recipe)
                # الحفاظ المطلق على الصورة و c
                item["image"] = recipe.get("image", "")
                item["c"] = current_chunk_num
                translated_recipes.append(item)
        else:
            # 1. تجميع كافة الحقول النصية القابلة للترجمة
            names = [r.get("name", "") for r in recipes]
            categories = [r.get("recipeCategory", r.get("category", "General")) for r in recipes]
            descriptions = [r.get("description", "") for r in recipes]
            keywords = [r.get("keywords", "") for r in recipes]
            yields = [str(r.get("recipeYield", r.get("yield", ""))) for r in recipes]

            # تجميع اسم المؤلف Author Name
            author_names = []
            for r in recipes:
                auth = r.get("author", {})
                if isinstance(auth, dict):
                    author_names.append(auth.get("name", ""))
                elif isinstance(auth, str):
                    author_names.append(auth)
                else:
                    author_names.append("")

            all_ingredients = []
            ing_spans = []
            all_instructions = []
            inst_spans = []
            all_alt_names = []
            alt_spans = []
            all_nutrition_texts = []
            nut_spans = []

            for r in recipes:
                # المكونات
                ings = r.get("recipeIngredient", r.get("ingredients", []))
                st_ing = len(all_ingredients)
                all_ingredients.extend(ings)
                ing_spans.append((st_ing, len(all_ingredients)))

                # التعليمات والخطوات
                insts = extract_instructions(r)
                st_inst = len(all_instructions)
                all_instructions.extend(insts)
                inst_spans.append((st_inst, len(all_instructions)))

                # الأسماء البديلة
                alts = r.get("alternateName", [])
                if isinstance(alts, str):
                    alts = [alts]
                st_alt = len(all_alt_names)
                all_alt_names.extend(alts)
                alt_spans.append((st_alt, len(all_alt_names)))

                # القيم الغذائية Nutrition
                nut_obj = r.get("nutrition", {})
                st_nut = len(all_nutrition_texts)
                if isinstance(nut_obj, dict):
                    for k in NUTRITION_KEYS:
                        val = nut_obj.get(k, "")
                        if val:
                            all_nutrition_texts.append(str(val))
                nut_spans.append((st_nut, len(all_nutrition_texts)))

            # 2. إرسال المجموعات للترجمة على كارت الشاشة GPU
            trans_names = translate_flat_list(names, model, tokenizer, nllb_code, batch_size=16, label="Names")
            trans_categories = translate_flat_list(categories, model, tokenizer, nllb_code, batch_size=16, label="Categories")
            trans_descriptions = translate_flat_list(descriptions, model, tokenizer, nllb_code, batch_size=16, label="Descriptions")
            trans_keywords = translate_flat_list(keywords, model, tokenizer, nllb_code, batch_size=16, label="Keywords")
            trans_yields = translate_flat_list(yields, model, tokenizer, nllb_code, batch_size=16, label="Yields")
            trans_authors = translate_flat_list(author_names, model, tokenizer, nllb_code, batch_size=16, label="Authors")
            
            trans_all_ingredients = translate_flat_list(all_ingredients, model, tokenizer, nllb_code, batch_size=16, label="Ingredients")
            trans_all_instructions = translate_flat_list(all_instructions, model, tokenizer, nllb_code, batch_size=16, label="Instructions")
            trans_all_alt_names = translate_flat_list(all_alt_names, model, tokenizer, nllb_code, batch_size=16, label="AlternateNames")
            trans_all_nutrition = translate_flat_list(all_nutrition_texts, model, tokenizer, nllb_code, batch_size=16, label="Nutrition")

            # 3. إعادة تركيب الوصفة بالكامل بدون المساس بـ image أو c
            for idx, recipe in enumerate(recipes):
                sub_chunk_offset = idx // 100
                current_chunk_num = base_chunk_num + sub_chunk_offset

                st_ing, en_ing = ing_spans[idx]
                recipe_ing = trans_all_ingredients[st_ing:en_ing]

                st_inst, en_inst = inst_spans[idx]
                recipe_inst = trans_all_instructions[st_inst:en_inst]

                st_alt, en_alt = alt_spans[idx]
                recipe_alt = trans_all_alt_names[st_alt:en_alt]

                # تركيبة القيم الغذائية المترجمة
                st_nut, en_nut = nut_spans[idx]
                translated_nut_vals = trans_all_nutrition[st_nut:en_nut]
                
                original_nut = recipe.get("nutrition", {})
                new_nut = original_nut.copy() if isinstance(original_nut, dict) else {}
                
                nut_val_idx = 0
                if isinstance(original_nut, dict):
                    for k in NUTRITION_KEYS:
                        if original_nut.get(k, ""):
                            if nut_val_idx < len(translated_nut_vals):
                                new_nut[k] = translated_nut_vals[nut_val_idx]
                                nut_val_idx += 1

                # تركيبة خطوات Schema.org (HowToStep)
                raw_instructions = recipe.get("recipeInstructions", [])
                new_recipe_instructions = []
                if isinstance(raw_instructions, list) and len(raw_instructions) == len(recipe_inst):
                    for step_idx, step_obj in enumerate(raw_instructions):
                        if isinstance(step_obj, dict):
                            step_copy = step_obj.copy()
                            step_copy["text"] = recipe_inst[step_idx]
                            new_recipe_instructions.append(step_copy)
                        else:
                            new_recipe_instructions.append(recipe_inst[step_idx])
                else:
                    new_recipe_instructions = recipe_inst

                # تركيبة كائن المؤلف Author المترجم
                original_author = recipe.get("author", {})
                new_author = original_author.copy() if isinstance(original_author, dict) else original_author
                if isinstance(new_author, dict) and "name" in new_author:
                    new_author["name"] = trans_authors[idx]

                # نسخ كائن الوصفة الأصلي بالكامل للحفاظ على المكونات الثابتة (@context, @type, aggregateRating, prepTime...)
                item = recipe.copy()

                # تحديث كافة الحقول القابلة للترجمة
                item["id"] = str(recipe.get("id"))
                item["name"] = trans_names[idx]
                item["recipeCategory"] = trans_categories[idx]
                item["category"] = trans_categories[idx]
                item["description"] = trans_descriptions[idx]
                item["keywords"] = trans_keywords[idx]
                item["alternateName"] = recipe_alt
                item["recipeIngredient"] = recipe_ing
                item["ingredients"] = recipe_ing
                item["recipeInstructions"] = new_recipe_instructions
                item["instructions"] = recipe_inst
                item["nutrition"] = new_nut
                item["recipeYield"] = trans_yields[idx]
                item["yield"] = trans_yields[idx]
                item["author"] = new_author

                # =========================================================
                # حظر الترجمة بشكل صريح على حقل الصور وحقل رقم الـ Chunk
                # =========================================================
                item["image"] = recipe.get("image", "")  # رابط الصورة الأصلي كما هو بدون تغيير
                item["c"] = current_chunk_num           # رقم الـ Chunk عدد صحيح بدون تغيير

                translated_recipes.append(item)

        # حفظ الملفات المترجمة بواقع 100 وصفة لكل ملف chunk_X.json
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
