import json
import os
import sys
import time
import urllib.parse
import requests
from datetime import datetime
from huggingface_hub import HfApi

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

BASE_DIR = "output_recipes_seo_2"

# استقبال رقم الملف المتولى من السيرفر (من 1 إلى 20)
FILE_NUM = int(sys.argv[1]) if len(sys.argv) > 1 else 1

PROGRESS_FILE = f"progress_file_{FILE_NUM}.json"

# جلب الإعدادات من متغيرات البيئة
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "bin-data-node/recipe-images")

if not HF_TOKEN:
    log("❌ [خطأ قاتل] لم يتم العثور على HF_TOKEN في متغيرات البيئة!")
    sys.exit(1)

hf_api = HfApi(token=HF_TOKEN)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log(f"📥 [استعادة التقدم] تم تحميل التقدم السابق لـ chunk_recipes_{FILE_NUM}.json: تم معالجة {len(data.get('processed_indices', []))} وجبة.")
                return set(data.get('processed_indices', []))
        except Exception as e:
            log(f"⚠️ [استعادة التقدم] تعذر قراءة ملف التقدم، بدء جلسة جديدة: {e}")
    return set()

def save_progress(processed_indices):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"file_num": FILE_NUM, "processed_indices": list(processed_indices)}, f, indent=2)

def generate_ai_prompt(recipe):
    """بناء وصف دقيق وجذاب للذكاء الاصطناعي مستعيناً بالاسم والوصف والكلمات المفتاحية"""
    name = recipe.get('name', 'Delicious Dish')
    description = recipe.get('description', '')
    keywords = recipe.get('keywords', [])
    category = recipe.get('recipeCategory', '')
    
    # تنظيف واختصار الوصف للتركيز على الشكل البصري
    clean_desc = description[:120] if description else "appetizing freshly cooked meal"
    
    # دمج الكلمات المفتاحية
    kw_str = ""
    if isinstance(keywords, list) and keywords:
        kw_str = ", " + ", ".join(keywords[:4])
    elif isinstance(keywords, str) and keywords:
        kw_str = ", " + keywords

    prompt = (
        f"Award-winning professional food photography of {name}. "
        f"{clean_desc}. Category: {category}{kw_str}. "
        f"Gourmet presentation, vibrant colors, studio culinary lighting, 8k resolution, highly detailed texture, depth of field, top-down view."
    )
    return prompt

def generate_and_upload_hf(recipe, recipe_idx, total_recipes):
    recipe_name = recipe.get('name', f'recipe_{recipe_idx}')
    clean_name = "".join([c if c.isalnum() else "_" for c in recipe_name]).lower()[:25]
    
    image_filename = f"img_f{FILE_NUM}_{recipe_idx}_{clean_name}.jpg"
    repo_path = f"images/file_{FILE_NUM}/{image_filename}"
    
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    prompt = generate_ai_prompt(recipe)
    delays = [2, 5, 10]
    
    for attempt in range(3):
        log(f"⏱️ [انتظار] تأخير {delays[attempt]} ثوانٍ قبل المحاولة {attempt + 1}/3 للوجبة ({recipe_idx + 1}/{total_recipes})...")
        time.sleep(delays[attempt])
        
        try:
            log(f"🎨 [إنشاء AI] جاري طلب توليد صورة جودة عالية للوصفة: '{recipe_name}'")
            log(f"📝 [Prompt]: {prompt[:100]}...")
            
            response = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=50)
            
            if response.status_code == 200 and len(response.content) > 15000:
                img_kb = round(len(response.content) / 1024, 1)
                log(f"📥 [تم التوليد بنجاح] حجم الصورة الناتجة: {img_kb} KB")
                
                # حفظ مؤقت
                with open(image_filename, 'wb') as img_f:
                    img_f.write(response.content)
                
                # رفع إلى Hugging Face Dataset
                log(f"☁️ [رفع HuggingFace] رفع إلى المستودع: {HF_DATASET_REPO}/{repo_path}")
                hf_api.upload_file(
                    path_or_fileobj=image_filename,
                    path_in_repo=repo_path,
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset"
                )
                
                if os.path.exists(image_filename):
                    os.remove(image_filename)
                
                # رابط الصورة المباشر من CDN
                cdn_url = f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/{repo_path}"
                log(f"✨ [نجاح تام] تم التوليد والرفع! الرابط الجديد: {cdn_url}")
                return cdn_url
                
            elif response.status_code == 503:
                log(f"⏳ [تحميل النموذج] سيرفر HF يبني النموذج حالياً، إعادة المحاولة...")
            else:
                log(f"⚠️ [استجابة غير صالحة] كود الحالة: {response.status_code} | المحتوى: {response.text[:100]}")
                
        except Exception as e:
            log(f"💥 [استثناء] حدث خطأ أثناء المحاولة {attempt + 1}: {e}")

    log(f"🛑 [فشل كامل] تعذر التوليد بعد 3 محاولات للوجبة: '{recipe_name}'.")
    return ""

def run_pipeline():
    log(f"🚀 [بدء السيرفر المستقل #{FILE_NUM}] التكليف: معالجة chunk_recipes_{FILE_NUM}.json")
    
    file_path = os.path.join(BASE_DIR, f"chunk_recipes_{FILE_NUM}.json")
    if not os.path.exists(file_path):
        log(f"❌ [خطأ] الملف المطلوب {file_path} غير موجود!")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    total_recipes = len(recipes)
    log(f"📊 [معلومات] إجمالي الوصفات في الملف {FILE_NUM}: {total_recipes} وصفة.")

    processed_indices = load_progress()

    for idx, recipe in enumerate(recipes):
        if idx in processed_indices:
            continue

        recipe_name = recipe.get('name', 'recipe')
        current_img = recipe.get('image', '')

        # إذا كانت الصورة غير معالجة أو لم تُرفع على HuggingFace بعد
        if not current_img or "huggingface.co" not in current_img:
            log(f"\n--- [معالجة الوجبة {idx + 1}/{total_recipes}] الاسم: '{recipe_name}' ---")
            image_url = generate_and_upload_hf(recipe, idx, total_recipes)
            
            if image_url:
                recipe['image'] = image_url
        else:
            log(f"⏭️ [تجاوز] الوجبة {idx + 1}/{total_recipes} تحتوي على رابط صورة جديد بالفعل.")

        processed_indices.add(idx)

        # حفظ التقدم بصفة دورية كل 5 وجبات
        if len(processed_indices) % 5 == 0 or idx == total_recipes - 1:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            save_progress(processed_indices)
            log(f"💾 [حفظ تلقائي] تم تحديث JSON وملف التقدم: {len(processed_indices)}/{total_recipes} وجبة مكتملة.")

    log(f"\n🎉 [اكتمال السيرفر #{FILE_NUM}] تم الانتهاء من جميع الـ 1000 وصفة الخاصة بهذا السيرفر بنجاح!")

if __name__ == "__main__":
    run_pipeline()
