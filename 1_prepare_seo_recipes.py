import json
import re
import os

def clean_title_for_seo(title: str) -> str:
    """تنظيف العنوان من الكلمات العشوائية وتحويله لنية بحث صافية (SEO Intent)"""
    if not title:
        return "Classic Recipe"
    
    # حذف الكلمات غير المحسنة لمحركات البحث والرموز
    stop_words = r'\b(my|grandma\'s|mom\'s|secret|famous|world\'s best|easy|quick|delish|ultimate|best ever|delicious|authentic|yummy)\b'
    cleaned = re.sub(stop_words, '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = ' '.join(cleaned.split()).title()
    
    # التأكد من إلحاق كلمة Recipe بطريقة طبيعية إذا لم تكن موجودة
    if not cleaned.lower().endswith('recipe'):
        cleaned = f"{cleaned} Recipe"
        
    return cleaned

def process_raw_dataset(input_file="raw_recipes.json"):
    print("⏳ جاري قراءة البيانات ومعالجة عناوين الـ SEO...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # اختيار أول 20,000 وصفة أعلى تقييماً وشهرة
    top_20k = raw_data[:20000]
    processed_recipes = []

    for idx, rcp in enumerate(top_20k):
        seo_title = clean_title_for_seo(rcp.get("title", ""))
        
        # بنية الوصفة المعيارية الموحدة
        processed_recipes.append({
            "id": f"rcp_{idx + 1:05d}",
            "seo_title": seo_title,
            "category": rcp.get("category", "Main Course"),
            "image_url": rcp.get("image_url", "https://via.placeholder.com/300"),
            "prep_time": rcp.get("prep_time", "15 mins"),
            "cook_time": rcp.get("cook_time", "30 mins"),
            "servings": rcp.get("servings", "4"),
            "ingredients": rcp.get("ingredients", []),
            "instructions": rcp.get("instructions", [])
        })

    # إنشاء المجلد للـ Raw Parts
    os.makedirs("raw_parts", exist_ok=True)

    # تقسيم الـ 20,000 وصفة إلى 20 ملفاً (1,000 وصفة/ملف)
    chunk_size = 1000
    for part_idx in range(20):
        start_i = part_idx * chunk_size
        end_i = start_i + chunk_size
        part_data = processed_recipes[start_i:end_i]
        
        filename = f"raw_parts/recipes_part_{part_idx + 1}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(part_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ تم إنشاء: {filename} يحتوي على {len(part_data)} وصفة.")

if __name__ == "__main__":
    process_raw_dataset()

