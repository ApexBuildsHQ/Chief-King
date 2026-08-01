import json
import os
import time
import re
import urllib.parse
from deep_translator import GoogleTranslator

# الـ 50 لغة العالمية المستهدفة
TARGET_LANGUAGES = [
    'ar', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-CN', 'ja', 'ko',
    'tr', 'hi', 'bn', 'pa', 'vi', 'th', 'el', 'nl', 'sv', 'no',
    'fi', 'da', 'pl', 'cs', 'hu', 'ro', 'uk', 'he', 'id', 'ms',
    'fa', 'ur', 'sw', 'am', 'tl', 'zu', 'kn', 'ta', 'te', 'mr',
    'gu', 'ml', 'si', 'my', 'km', 'lo', 'ne', 'hy', 'sq', 'bs'
]

MASTER_FILE = './master_20k_recipes.json'
DICT_FILE = './ingredients_dict.json'
OUTPUT_DIR = './chunk_recipes'
PROGRESS_FILE = './python_trans_progress.json'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

dictionary = load_json(DICT_FILE)

def preprocess_numbers_and_units(text, lang):
    """تحويل الأرقام والوحدات المحددة سلفاً في القاموس قبل أو بعد الترجمة"""
    if not text or not isinstance(text, str):
        return text

    # 1. تحويل الأرقام حسب اللغة
    num_map = dictionary.get("number_systems", {}).get(lang, {})
    for eng_digit, local_digit in num_map.items():
        text = text.replace(eng_digit, local_digit)

    # 2. استبدال الوحدات الأساسية
    units = dictionary.get("units", {})
    for u_key, lang_map in units.items():
        if lang in lang_map and u_key in text:
            pattern = r'\b' + re.escape(u_key) + r'\b'
            text = re.sub(pattern, lang_map[lang], text)

    return text

def translate_single_text(text, target_lang):
    """ترجمة نص فردي وتغطية المكونات الغريبة أوتوماتيكياً عبر Deep Translator"""
    if not text or not isinstance(text, str):
        return text if text else ""
    
    ingredients_map = dictionary.get("ingredients", {})
    for ing_key, lang_map in ingredients_map.items():
        if lang_map.get(target_lang) and ing_key in text.lower():
            pattern = re.compile(re.escape(ing_key), re.IGNORECASE)
            text = pattern.sub(lang_map[target_lang], text)

    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return preprocess_numbers_and_units(translated, target_lang)
    except Exception:
        time.sleep(0.3)
        return preprocess_numbers_and_units(text, target_lang)

def translate_field(field_data, target_lang):
    """معالجة الحقول سواء كانت نصاً عادياً أو مصفوفة (Array) كالخطوات والمكونات"""
    if not field_data:
        return [] if isinstance(field_data, list) else ""

    if isinstance(field_data, list):
        return [translate_single_text(str(item), target_lang) for item in field_data]
    else:
        return translate_single_text(str(field_data), target_lang)

def translate_nutrition(nutrition_data, target_lang):
    """ترجمة وترتيب الحقائق الغذائية (كربوهيدرات، دهون، بروتين، سعرات) مع معالجة الأرقام والوحدات"""
    if not nutrition_data:
        return {}
    
    if isinstance(nutrition_data, dict):
        translated_nutrition = {}
        for key, val in nutrition_data.items():
            translated_key = translate_single_text(str(key), target_lang)
            translated_val = preprocess_numbers_and_units(str(val), target_lang)
            translated_nutrition[translated_key] = translated_val
        return translated_nutrition
    else:
        return translate_field(nutrition_data, target_lang)

def start_translation():
    master_data = load_json(MASTER_FILE)
    if not master_data or not isinstance(master_data, list):
        print("❌ لم يتم العثور على ملف master_20k_recipes.json أو أن البيانات غير مكتملة.")
        return

    print(f"🚀 بدء محرك الترجمة الشامل لـ {len(master_data)} وصفة إلى 50 لغة...")

    progress = load_json(PROGRESS_FILE)
    start_idx = progress.get("recipe_index", 0)

    # 📌 دمج 200 وصفة في كل ملف حسب طلبك
    CHUNK_SIZE = 200
    total_recipes = len(master_data)

    for i in range(start_idx, total_recipes, CHUNK_SIZE):
        batch = master_data[i:i + CHUNK_SIZE]
        chunk_num = (i // CHUNK_SIZE) + 1

        print(f"\n📦 جاري معالجة وتوليد الـ Chunk رقم {chunk_num} (الوصفات {i+1} إلى {min(i+CHUNK_SIZE, total_recipes)})...")

        for lang in TARGET_LANGUAGES:
            translated_chunk = []
            for item in batch:
                # 1. عنوان الوصفة
                translated_title = translate_field(item.get("title"), lang)
                
                # توليد روابط اليوتيوب المخصصة بلغة الوصفة
                encoded_query = urllib.parse.quote(f"{translated_title} recipe")
                yt_search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                yt_embed_url = f"https://www.youtube.com/embed?listType=search&list={encoded_query}"

                # 📌 ترتيب عناصر الوصفة النهائي والدقيق بالترتيب المطلوب
                translated_item = {
                    "id": item.get("id"),
                    "title": translated_title,                                                      # 1. عنوان الوصفة
                    "category": translate_field(item.get("category"), lang),                        # تصنيف الوصفة
                    "description": translate_field(item.get("description"), lang),                 # 2. الوصف الخاص بالوصفة
                    "image": item.get("image", ""),                                                 # 3. الصورة الجاذبة
                    "prepTime": preprocess_numbers_and_units(item.get("prepTime", ""), lang),       # وقت التحضير
                    "cookTime": preprocess_numbers_and_units(item.get("cookTime", ""), lang),       # وقت الطهي
                    "ingredients": translate_field(item.get("ingredients", []), lang),              # 4. المقادير المطلوبة
                    "instructions": translate_field(item.get("instructions", []), lang),            # 5. خطوات الطهي
                    "nutrition": translate_nutrition(item.get("nutrition", item.get("nutrition_facts", {})), lang), # 6. المعلومات الغذائية
                    "youtube_search_url": yt_search_url,                                           # 7. رابط بحث اليوتيوب
                    "youtube_embed_url": yt_embed_url                                               # 8. رابط إطار اليوتيوب (Embed)
                }
                translated_chunk.append(translated_item)

            # 📌 اسم الملف بصيغة chunk-{lang}-{chunk_num}.json (مثال: chunk-ar-1.json)
            file_name = f"chunk-{lang}-{chunk_num}.json"
            save_json(os.path.join(OUTPUT_DIR, file_name), translated_chunk)

        save_json(PROGRESS_FILE, {"recipe_index": i + CHUNK_SIZE})
        print(f"✅ اكتمل حفظ الـ Chunk {chunk_num} لجميع الـ 50 لغة بنجاح.")

    print("\n🎉 تم إنهاء ترجمة وتقسيم الملفات بنجاح 100%!")
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

if __name__ == "__main__":
    start_translation()

