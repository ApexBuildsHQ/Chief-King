import json
import argparse
import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# تحسين استخدام المعالج على سيرفرات GitHub Actions
torch.set_num_threads(os.cpu_count() or 2)

# قائمة الـ 50 لغة الأكثر انتشاراً عالمياً مع أكواد NLLB المخصصة
LANG_MAP = {
    "ar": "arb_Arab", "en": "eng_Latn", "es": "spa_Latn", "fr": "fra_Latn", "de": "deu_Latn",
    "zh": "zho_Hans", "ja": "jpn_Jpan", "hi": "hin_Deva", "ru": "rus_Cyrl", "pt": "por_Latn",
    "it": "ita_Latn", "tr": "tur_Latn", "nl": "nld_Latn", "pl": "pol_Latn", "sv": "swe_Latn",
    "vi": "vie_Latn", "th": "tha_Thai", "id": "ind_Latn", "fa": "pes_Arab", "he": "heb_Hebr",
    "uk": "ukr_Cyrl", "ro": "ron_Latn", "hu": "hun_Latn", "cs": "ces_Latn", "el": "ell_Grek",
    "da": "dan_Latn", "fi": "fin_Latn", "no": "nob_Latn", "sk": "slk_Latn", "bg": "bul_Cyrl",
    "hr": "hrv_Latn", "sr": "srp_Cyrl", "lt": "lit_Latn", "sl": "slv_Latn", "et": "est_Latn",
    "lv": "lvs_Latn", "sw": "swh_Latn", "ms": "zsm_Latn", "fil": "tgl_Latn", "ur": "urd_Arab",
    "bn": "ben_Beng", "ta": "tam_Taml", "te": "tel_Telu", "mr": "mar_Deva", "kn": "kan_Knda",
    "ml": "mal_Mlym", "gu": "guj_Gujr", "pa": "pan_Guru", "am": "amh_Ethi", "ko": "kor_Hang"
}

def load_nllb_model():
    print("⏳ جاري تحميل نموذج الذكاء الاصطناعي للترجمة NLLB-200...")
    model_name = "facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    # تثبيت اللغة المصدر افتراضياً كاللغة الإنجليزية لرفع الدقة
    tokenizer.src_lang = "eng_Latn"
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    return tokenizer, model, device

def translate_batch(texts, target_code, tokenizer, model, device, max_batch_size=16):
    """
    ترجمة نصوص معالجة بكفاءة عالية:
    1. حل مشكلة NllbTokenizer ومعرفات اللغات ليكون متوافقاً مع كل الإصدارات
    2. تقسيم الدفعات لتوفير الذاكرة والوصول لأعلى كفاءة
    3. تسريع عملية التوليد مع الحفاظ على دقة المعنى
    """
    if not texts:
        return []

    # تحديد معرّف اللغة الهدف بشكل آمن ودقيق
    try:
        target_lang_id = tokenizer.convert_tokens_to_ids(target_code)
    except Exception:
        target_lang_id = tokenizer.lang_code_to_id.get(target_code) if hasattr(tokenizer, 'lang_code_to_id') else None

    tokenizer.src_lang = "eng_Latn"
    results = []

    # معالجة النصوص على دفعات (Mini-batches)
    for i in range(0, len(texts), max_batch_size):
        batch_texts = texts[i:i + max_batch_size]
        
        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(device)

        with torch.no_grad():
            translated_tokens = model.generate(
                **inputs,
                forced_bos_token_id=target_lang_id,
                max_length=512,
                num_beams=1,      # تسريع توليد النصوص بأكثر من 3 أضعاف
                do_sample=False  # توليد محدد ومباشر (Greedy Search)
            )

        decoded = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
        results.extend(decoded)

    return results

def process_part(part_num):
    input_file = f"raw_parts/recipes_part_{part_num}.json"
    if not os.path.exists(input_file):
        print(f"❌ الملف {input_file} غير موجود!")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    tokenizer, model, device = load_nllb_model()
    os.makedirs("dist_chunks", exist_ok=True)
    os.makedirs("dist_index_parts", exist_ok=True)

    for lang_key, nllb_code in LANG_MAP.items():
        # تجاوز الترجمة للغة الإنجليزية لتسريع المعالجة فورياً
        if lang_key == "en":
            print(f"⚡ [Part {part_num}] تجاوز الترجمة للغة الإنجليزية (English Direct Pass)...")
            translated_recipes = []
            index_items = []
            for idx, rcp in enumerate(recipes):
                chunk_sub_num = (idx // 200) + 1
                chunk_id = f"p{part_num}_{chunk_sub_num}"
                
                translated_recipes.append({
                    "id": rcp["id"],
                    "seo_title": rcp["seo_title"],
                    "category": rcp["category"],
                    "image_url": rcp["image_url"],
                    "prep_time": rcp["prep_time"],
                    "cook_time": rcp["cook_time"],
                    "servings": rcp["servings"],
                    "ingredients": rcp["ingredients"],
                    "instructions": rcp["instructions"]
                })
                index_items.append({
                    "id": rcp["id"],
                    "title": rcp["seo_title"],
                    "image_url": rcp["image_url"],
                    "category": rcp["category"],
                    "chunk_id": chunk_id
                })
        else:
            print(f"🌐 [Part {part_num}] جاري الترجمة إلى اللغة: {lang_key}...")
            translated_recipes = []
            index_items = []

            for idx, rcp in enumerate(recipes):
                chunk_sub_num = (idx // 200) + 1
                chunk_id = f"p{part_num}_{chunk_sub_num}"

                # تجميع نصوص الوصفة الكاملة في مصفوفة واحدة لمعالجتها بدفعة موحدة
                ingredients = rcp.get("ingredients", [])
                instructions = rcp.get("instructions", [])
                n_ing = len(ingredients)
                
                all_recipe_texts = [rcp["seo_title"]] + ingredients + instructions

                # ترجمة كافة نصوص الوصفة دفعة واحدة
                translated_all = translate_batch(all_recipe_texts, nllb_code, tokenizer, model, device)

                t_title = translated_all[0] if translated_all else rcp["seo_title"]
                t_ingredients = translated_all[1 : 1 + n_ing]
                t_instructions = translated_all[1 + n_ing :]

                translated_recipes.append({
                    "id": rcp["id"],
                    "seo_title": t_title,
                    "category": rcp["category"],
                    "image_url": rcp["image_url"],
                    "prep_time": rcp["prep_time"],
                    "cook_time": rcp["cook_time"],
                    "servings": rcp["servings"],
                    "ingredients": t_ingredients,
                    "instructions": t_instructions
                })

                index_items.append({
                    "id": rcp["id"],
                    "title": t_title,
                    "image_url": rcp["image_url"],
                    "category": rcp["category"],
                    "chunk_id": chunk_id
                })

        # تقسيم الـ 1,000 وصفة المترجمة إلى 5 ملفات Chunks (200 وصفة في كل ملف)
        for i in range(5):
            chunk_data = translated_recipes[i*200 : (i+1)*200]
            chunk_file = f"dist_chunks/chunk_p{part_num}_{i+1}_{lang_key}.json"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False)

        # حفظ جزء الفهرس لهذه اللغة والـ Part
        index_file = f"dist_index_parts/index_part_{part_num}_{lang_key}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_items, f, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, required=True, help="Part number (1-20)")
    args = parser.parse_args()
    process_part(args.part)

