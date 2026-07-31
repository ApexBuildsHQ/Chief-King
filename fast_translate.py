import json
import os
import time
from deep_translator import GoogleTranslator

# الـ 50 لغة المستهدفة
TARGET_LANGUAGES = [
    'ar', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-CN', 'ja', 'ko',
    'tr', 'hi', 'bn', 'pa', 'vi', 'th', 'el', 'nl', 'sv', 'no',
    'fi', 'da', 'pl', 'cs', 'hu', 'ro', 'uk', 'he', 'id', 'ms',
    'fa', 'ur', 'sw', 'am', 'tl', 'zu', 'kn', 'ta', 'te', 'mr',
    'gu', 'ml', 'si', 'my', 'km', 'lo', 'ne', 'hy', 'sq', 'bs'
]

MASTER_FILE = './master_20k_recipes.json'
OUTPUT_DIR = './chunk_recipes'
PROGRESS_FILE = './python_trans_progress.json'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_text(text, target_lang):
    if not text:
        return ""
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        time.sleep(1)
        return text

def start_translation():
    master_data = load_json(MASTER_FILE)
    if not master_data:
        print("❌ لم يتم العثور على ملف master_20k_recipes.json")
        return

    print(f"🚀 بدء الترجمة إلى 50 لغة لـ {len(master_data)} وصفة باستخدام Deep Translation...")

    progress = load_json(PROGRESS_FILE) or {"recipe_index": 0}
    start_idx = progress.get("recipe_index", 0)

    # تقسيم الوصفات إلى Chunks (كل ملف يحتوي 100 وصفة لكل لغة)
    CHUNK_SIZE = 100
    total_recipes = len(master_data)

    for i in range(start_idx, total_recipes, CHUNK_SIZE):
        batch = master_data[i:i + CHUNK_SIZE]
        chunk_num = (i // CHUNK_SIZE) + 1

        print(f"\n📦 معالجة الـ Chunk رقم {chunk_num} (الوصفات {i+1} إلى {min(i+CHUNK_SIZE, total_recipes)})...")

        for lang in TARGET_LANGUAGES:
            translated_chunk = []
            for item in batch:
                translated_item = {
                    "id": item.get("id"),
                    "title": translate_text(item.get("title"), lang),
                    "category": item.get("category"),
                    "description": translate_text(item.get("description"), lang),
                    "prepTime": item.get("prepTime"),
                    "cookTime": item.get("cookTime")
                }
                translated_chunk.append(translated_item)

            file_name = f"chunk_{lang}_{chunk_num}.json"
            save_json(os.path.join(OUTPUT_DIR, file_name), translated_chunk)
            print(f"   💾 تم حفظ: {file_name}")

        save_json(PROGRESS_FILE, {"recipe_index": i + CHUNK_SIZE})

    print("\n🎉 تم إنشاء كافة أجزاء الترجمة لـ 50 لغة عالمية بنجاح!")
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

if __name__ == "__main__":
    start_translation()
