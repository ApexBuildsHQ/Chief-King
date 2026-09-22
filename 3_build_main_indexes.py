import json
import os

LANGUAGES = [
    "ar", "en", "es", "fr", "de", "zh", "ja", "hi", "ru", "pt",
    "it", "tr", "nl", "pl", "sv", "vi", "th", "id", "fa", "he",
    "uk", "ro", "hu", "cs", "el", "da", "fi", "no", "sk", "bg",
    "hr", "sr", "lt", "sl", "et", "lv", "sw", "ms", "fil", "ur",
    "bn", "ta", "te", "mr", "kn", "ml", "gu", "pa", "am", "ko"
]

def merge_all_indexes():
    os.makedirs("dist_final_indexes", exist_ok=True)
    
    for lang in LANGUAGES:
        all_items_for_lang = []
        
        # تجميع الفهارس من الـ 20 أجزاء
        for part_num in range(1, 21):
            part_file = f"dist_index_parts/index_part_{part_num}_{lang}.json"
            if os.path.exists(part_file):
                with open(part_file, 'r', encoding='utf-8') as f:
                    all_items_for_lang.extend(json.load(f))

        # تقسيم الـ 20,000 عنصر إلى 4 ملفات فهارس (5,000 عنصر/ملف)
        items_per_index = 5000
        for i in range(4):
            chunk_items = all_items_for_lang[i * items_per_index : (i + 1) * items_per_index]
            out_file = f"dist_final_indexes/main_index_{i + 1}_{lang}.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_items, f, ensure_ascii=False)
                
        print(f"✅ تم إنشاء الـ 4 ملفات فهارس المكتملة للغة: {lang}")

if __name__ == "__main__":
    merge_all_indexes()

