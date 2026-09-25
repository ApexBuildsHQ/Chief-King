import json
import os
import sys
import time
import urllib.parse
import subprocess
import requests

# استلام نطاق الملفات من وسائط السكربت (مثال: python process_recipes.py 1 10)
START_FILE = int(sys.argv[1]) if len(sys.argv) > 1 else 1
END_FILE = int(sys.argv[2]) if len(sys.argv) > 2 else 10

PROGRESS_FILE = f"progress_group_{START_FILE}_{END_FILE}.json"
RELEASE_TAG = f"v1.0-images-{START_FILE}-{END_FILE}"
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "user/repo")

# إنشاء الـ Release على GitHub إذا لم يكن موجوداً
def ensure_github_release():
    cmd = f'gh release view {RELEASE_TAG} || gh release create {RELEASE_TAG} --title "Recipe Images Group {START_FILE}-{END_FILE}" --notes "Automated images hosting"'
    subprocess.run(cmd, shell=True, capture_output=True)

# تحميل التقدم السابق
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"current_file": START_FILE, "processed_indices": []}

# حفظ التقدم
def save_progress(file_idx, processed_indices):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"current_file": file_idx, "processed_indices": processed_indices}, f, indent=2)

def fetch_and_upload_image(recipe_name, file_num, recipe_idx):
    prompt = urllib.parse.quote(f"delicious {recipe_name}, high quality food photography, professional lighting, tasty meal, centered")
    ai_url = f"https://pollinations.ai/p/{prompt}?width=800&height=600&nologo=true&seed={recipe_idx}"
    
    clean_name = "".join([c if c.isalnum() else "_" for c in recipe_name]).lower()[:25]
    image_filename = f"img_f{file_num}_{recipe_idx}_{clean_name}.jpg"
    
    # قائمة فترات الانتظار: المحاولة 1 (3 ثوانٍ)، المحاولة 2 (3+3=6 ثوانٍ)، المحاولة 3 (6+5=11 ثانية)
    delays = [3, 6, 11]
    
    for attempt in range(3):
        time.sleep(delays[attempt])
        try:
            # تغيير الـ User-Agent لتقليل احتمالية الحظر عند كل طلب
            headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Bot_{file_num}_{recipe_idx}_{attempt})'}
            response = requests.get(ai_url, headers=headers, timeout=20)
            
            if response.status_code == 200 and len(response.content) > 3000:
                # حفظ الصورة مؤقتاً
                with open(image_filename, 'wb') as img_f:
                    img_f.write(response.content)
                
                # رفع الصورة إلى GitHub Release عبر GitHub CLI
                upload_cmd = f'gh release upload {RELEASE_TAG} "{image_filename}" --clobber'
                result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
                
                # حذف الملف المحلي مؤقتاً لتوفير المساحة
                if os.path.exists(image_filename):
                    os.remove(image_filename)
                
                if result.returncode == 0:
                    # إرجاع رابط الصورة المباشر من CDN الخاص بـ GitHub
                    return f"https://github.com/{REPO_NAME}/releases/download/{RELEASE_TAG}/{image_filename}"
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {recipe_name}: {e}")

    # إذا فشلت المحاولات الثلاث، يُترك الحقل فارغاً تماماً
    return ""

def run_pipeline():
    ensure_github_release()
    progress = load_progress()
    start_file_num = progress["current_file"]

    for file_num in range(start_file_num, END_FILE + 1):
        json_filename = f"chunk_recipes_{file_num}.json"
        
        if not os.path.exists(json_filename):
            print(f"File {json_filename} not found, skipping...")
            continue

        with open(json_filename, 'r', encoding='utf-8') as f:
            recipes = json.load(f)

        processed_indices = set(progress["processed_indices"]) if file_num == start_file_num else set()

        for idx, recipe in enumerate(recipes):
            if idx in processed_indices:
                continue

            # معالجة الوصفة فقط إذا كانت الصورة فارغة أو غير معالجة سابقاً
            if not recipe.get('image') or "github.com" not in recipe.get('image', ''):
                image_url = fetch_and_upload_image(recipe.get('name', 'food'), file_num, idx)
                recipe['image'] = image_url

            processed_indices.add(idx)

            # حفظ التقدم والملف بعد كل 10 وصفات لتجنب فقدان البيانات عند التوقف المفاجئ
            if len(processed_indices) % 10 == 0:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(recipes, f, ensure_ascii=False, indent=2)
                save_progress(file_num, list(processed_indices))
                print(f"[File {file_num}] Progress saved: {len(processed_indices)}/{len(recipes)}")

        # حفظ الملف بالكامل عند الانتهاء منه
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        
        # إعادة ضبط التقدم للملف التالي
        save_progress(file_num + 1, [])

if __name__ == "__main__":
    run_pipeline()
