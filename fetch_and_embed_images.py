import sys
import os
import json
import time
import random
import urllib.parse
import requests
import hashlib
from PIL import Image
from io import BytesIO

# الإعدادات الرئيسية
GITHUB_USERNAME = "ApexBuildsHQ"
IMAGES_REPO = "chief-king-images"
PUBLIC_CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_USERNAME}/{IMAGES_REPO}@main/recipes"

def log(message):
    print(message, flush=True)

def generate_recipe_id(recipe, index):
    """استخراج הـ ID أو توليد رقم فريد ثابت"""
    existing_id = recipe.get("id") or recipe.get("recipe_id")
    if existing_id is not None and str(existing_id).isdigit():
        return int(existing_id)
    
    recipe_name = recipe.get("name", f"recipe_{index}")
    generated_hash = hashlib.md5(recipe_name.encode('utf-8')).hexdigest()
    return int(generated_hash, 16) % 900000 + 100000

def generate_and_save_webp(recipe_name, recipe_id, output_path):
    """طلب الصورة من الـ API المباشر لـ Pollinations"""
    clean_name = recipe_name.replace("'", "").replace('"', "")
    prompt = urllib.parse.quote(f"delicious food photograph of {clean_name}, high quality culinary presentation, 8k plate dish")
    
    # استخدام الرابط المباشر المخصص للصور image.pollinations.ai مع تحديد النموذج flux
    ai_url = f"https://image.pollinations.ai/prompt/{prompt}?width=800&height=600&seed={recipe_id}&nologo=true&model=flux"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }
    
    start_time = time.time()
    for attempt in range(1, 4):
        log(f"   ↳ [محاولة {attempt}/3] طلب الصورة للوصفة (#{recipe_id})...")
        try:
            res = requests.get(ai_url, headers=headers, timeout=30)
            content_type = res.headers.get("content-type", "").lower()
            
            # التأكد من أن النتيجة صورة وليست صفحة HTML
            if res.status_code == 200 and "image" in content_type:
                raw_size_kb = len(res.content) / 1024
                
                img = Image.open(BytesIO(res.content)).convert("RGB")
                img.save(output_path, "WEBP", quality=80, optimize=True)
                
                webp_size_kb = os.path.getsize(output_path) / 1024
                elapsed = time.time() - start_time
                log(f"   ↳ [نجاح التوليد]: الحجم: {raw_size_kb:.1f}KB ← {webp_size_kb:.1f}KB | المستغرق: {elapsed:.2f} ثانية")
                return True
            else:
                log(f"   ⚠️ استجابة غير صالحة من السيرفر (Status: {res.status_code}, Type: {content_type})")
        except Exception as e:
            log(f"   ⚠️ خطأ أثناء المعالجة: {str(e)}")
            
        # انتظار متزايد في حال فشل المحاولة
        time.sleep(3 * attempt)
        
    log(f"   ❌ فشلت محاولات التوليد للوصفة #{recipe_id}.")
    return False

def process_chunk(chunk_id):
    input_file = f"output_recipes_seo/recipes_chunk_{chunk_id}.json"
    images_dir = "output_images"
    
    log(f"=== [بدء السيرفر الخاص بـ Chunk #{chunk_id}] ===")
    os.makedirs(images_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        log(f"❌ خطأ قاتل: الملف غير موجود: {input_file}")
        sys.exit(1)
        
    with open(input_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
        
    total_recipes = len(recipes)
    log(f"📖 تم تحميل {total_recipes} وصفة من {input_file}")
    
    updated_recipes = []
    success_count = 0
    fail_count = 0
    chunk_start_time = time.time()
    
    for index, recipe in enumerate(recipes, start=1):
        recipe_id = generate_recipe_id(recipe, index)
        recipe_name = recipe.get("name", "recipe")
        
        log(f"\n[{index}/{total_recipes}] معالجة: '{recipe_name}' (ID: {recipe_id})")
        
        webp_filename = f"recipe_{recipe_id}.webp"
        local_image_path = os.path.join(images_dir, webp_filename)
        cdn_image_url = f"{PUBLIC_CDN_BASE}/{webp_filename}"
        
        # التوليد والحفظ
        success = generate_and_save_webp(recipe_name, recipe_id, local_image_path)
        if success:
            success_count += 1
        else:
            fail_count += 1
            cdn_image_url = "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=800"
            
        # تأخير عشوائي بين 1.5 و 3 ثوانٍ لتوزيع طلبات السيرفرات الـ 20 ومنع الحظر
        time.sleep(random.uniform(1.5, 3.0))
            
        # ترتيب البيانات وضمان وجود id و image
        new_recipe = {"id": recipe_id}
        for key, value in recipe.items():
            if key in ["id", "recipe_id"]:
                continue
            new_recipe[key] = value
            if key == "description":
                new_recipe["image"] = cdn_image_url
                
        if "image" not in new_recipe:
            new_recipe["image"] = cdn_image_url
            
        updated_recipes.append(new_recipe)

    # حفظ الملف المحدث
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
        
    total_elapsed = time.time() - chunk_start_time
    log(f"\n==========================================")
    log(f"🎉 اكتمل عمل السيرفر لـ Chunk #{chunk_id} بنجاح!")
    log(f"📊 الإحصائيات: ناجح ({success_count}) | فاشل ({fail_count}) | الإجمالي ({total_recipes})")
    log(f"⏱️ الوقت المستغرق: {total_elapsed / 60:.2f} دقيقة")
    log(f"💾 تم تحديث الملف: {input_file}")
    log(f"==========================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("❌ خطأ: يرجى تمرير رقم الـ Chunk كمعامل مدخل.")
        sys.exit(1)
        
    chunk_num = sys.argv[1]
    process_chunk(chunk_num)
