# process_recipes.py
import json
import os
import sys
import time
import urllib.parse
import subprocess
import requests
from datetime import datetime

# دالة لطباعة الخطوات لحظة بلحظة مع التوقيت والطباعة الفورية (flush=True)
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

# المجلد المحدد للملفات
BASE_DIR = "output_recipes_seo_2"

# نطاق الملفات المستلم من GitHub Actions (السيرفر الأول: 1 10 | السيرفر الثاني: 11 20)
START_FILE = int(sys.argv[1]) if len(sys.argv) > 1 else 1
END_FILE = int(sys.argv[2]) if len(sys.argv) > 2 else 10

PROGRESS_FILE = f"progress_group_{START_FILE}_{END_FILE}.json"
RELEASE_TAG = f"v1.0-images-{START_FILE}-{END_FILE}"
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "user/repo")

def ensure_github_release():
    log(f"🚀 [إعداد] جاري التحقق من وجود GitHub Release: {RELEASE_TAG}...")
    cmd = f'gh release view {RELEASE_TAG} || gh release create {RELEASE_TAG} --title "Recipe Images Group {START_FILE}-{END_FILE}" --notes "Automated images hosting"'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        log(f"✅ [إعداد] الـ Release جاهز للرفع: {RELEASE_TAG}")
    else:
        log(f"⚠️ [إعداد] تنبيه أثناء تهيئة Release: {res.stderr.strip()}")

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log(f"📥 [استعادة] تم تحميل التقدم السابق: الملف {data.get('current_file')}")
                return data
        except Exception as e:
            log(f"⚠️ [استعادة] خطأ في قراءة ملف التقدم، بدء جلسة جديدة: {e}")
    return {"current_file": START_FILE, "processed_indices": []}

def save_progress(file_idx, processed_indices):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"current_file": file_idx, "processed_indices": processed_indices}, f, indent=2)

def fetch_and_upload_image(recipe_name, file_num, recipe_idx, total_recipes):
    prompt = urllib.parse.quote(f"delicious {recipe_name} food photography, centered, high quality")
    # استخدام نموذج flux للصور مع تحديد أبعاد واضحة
    ai_url = f"https://pollinations.ai/p/{prompt}?width=800&height=600&nologo=true&model=flux&seed={recipe_idx}"
    
    clean_name = "".join([c if c.isalnum() else "_" for c in recipe_name]).lower()[:25]
    image_filename = f"img_f{file_num}_{recipe_idx}_{clean_name}.jpg"
    
    # فترات الانتظار المتصاعدة: 3 ثوانٍ -> 6 ثوانٍ -> 11 ثانية
    delays = [3, 6, 11]
    
    for attempt in range(3):
        log(f"⏱️ [انتظار] تأخير {delays[attempt]} ثوانٍ قبل المحاولة {attempt + 1}/3 للوجبة ({recipe_idx + 1}/{total_recipes})...")
        time.sleep(delays[attempt])
        
        try:
            log(f"🌐 [طلب] جلب الصورة للوصفة: '{recipe_name}' (محاولة {attempt + 1})")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }
            response = requests.get(ai_url, headers=headers, timeout=25)
            
            content_type = response.headers.get('Content-Type', '')
            image_size = len(response.content)
            
            # التحقق الصارم: يجب أن تكون استجابة 200 ومن نوع صورة وبحجم أكبر من 15,000 بايت (تجنباً لصفحات الأخطاء)
            if response.status_code == 200 and 'image' in content_type and image_size > 15000:
                log(f"📥 [تم التحميل] صورة صالحة بحجم: {image_size} bytes ({round(image_size / 1024, 1)} KB)")
                
                # حفظ مؤقت
                with open(image_filename, 'wb') as img_f:
                    img_f.write(response.content)
                
                # رفع إلى Release
                log(f"☁️ [رفع] رفع الصورة إلى GitHub Release...")
                upload_cmd = f'gh release upload {RELEASE_TAG} "{image_filename}" --clobber'
                result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
                
                if os.path.exists(image_filename):
                    os.remove(image_filename)
                
                if result.returncode == 0:
                    cdn_url = f"https://github.com/{REPO_NAME}/releases/download/{RELEASE_TAG}/{image_filename}"
                    log(f"✨ [نجاح] تم رفع الصورة بنجاح! الرابط: {cdn_url}")
                    return cdn_url
                else:
                    log(f"❌ [خطأ رفع] فشل الرفع عبر GitHub CLI: {result.stderr.strip()}")
            else:
                log(f"⚠️ [استجابة غير صالحة] الاستجابة ليست صورة حقيقية! الحجم: {image_size} bytes | النوع: {content_type} | كود الحالة: {response.status_code}")
        except Exception as e:
            log(f"💥 [استثناء] فشلت المحاولة {attempt + 1}: {e}")

    log(f"🛑 [فشل كامل] تعذر جلب الصورة بعد 3 محاولات. سيتم ترك الحقل فارغاً.")
    return ""

def run_pipeline():
    log(f"🏁 [بدء السيرفر] بدء المعالجة للمجلد '{BASE_DIR}' للملفات من {START_FILE} إلى {END_FILE}")
    ensure_github_release()
    
    progress = load_progress()
    start_file_num = progress["current_file"]

    for file_num in range(start_file_num, END_FILE + 1):
        file_path = os.path.join(BASE_DIR, f"chunk_recipes_{file_num}.json")
        
        log(f"\n📂 [ملف جديد] جاري فتح الملف: {file_path}")
        if not os.path.exists(file_path):
            log(f"❌ [خطأ] الملف {file_path} غير موجود! تجاوز...")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            recipes = json.load(f)

        total_recipes = len(recipes)
        log(f"📊 [معلومات الملف] إجمالي الوصفات في chunk_recipes_{file_num}.json: {total_recipes}")

        processed_indices = set(progress["processed_indices"]) if file_num == start_file_num else set()

        for idx, recipe in enumerate(recipes):
            if idx in processed_indices:
                continue

            recipe_name = recipe.get('name', 'recipe')
            current_img = recipe.get('image', '')

            # المعالجة إذا كانت الصورة فارغة أو ليست رابط GitHub Release
            if not current_img or "github.com" not in current_img:
                log(f"\n--- [معالجة الوجبة {idx + 1}/{total_recipes}] الاسم: '{recipe_name}' ---")
                image_url = fetch_and_upload_image(recipe_name, file_num, idx, total_recipes)
                recipe['image'] = image_url
            else:
                log(f"⏭️ [تجاوز] الوجبة {idx + 1}/{total_recipes} تحتوي بالفعل على رابط صورة معالج.")

            processed_indices.add(idx)

            # حفظ التقدم كل 5 وصفات لضمان عدم ضياع الجهد والطباعة المستمرة
            if len(processed_indices) % 5 == 0 or idx == total_recipes - 1:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(recipes, f, ensure_ascii=False, indent=2)
                save_progress(file_num, list(processed_indices))
                log(f"💾 [حفظ التقدم] تم حفظ التقدم للملف {file_num}: {len(processed_indices)}/{total_recipes} وصفة.")

        # إنهاء الملف بالكامل
        log(f"✅ [اكتمال ملف] تم الانتهاء بالكامل من الملف: {file_path}")
        save_progress(file_num + 1, [])

    log(f"🎉 [اكتمال السيرفر] تم الانتهاء من جميع الملفات المحددة من {START_FILE} إلى {END_FILE}!")

if __name__ == "__main__":
    run_pipeline()
