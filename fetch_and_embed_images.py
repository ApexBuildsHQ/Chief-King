import sys
import os
import json
import time
import urllib.parse
import requests
from PIL import Image
from io import BytesIO

# إعدادات المخرجات
GITHUB_USERNAME = "ApexBuildsHQ"
IMAGES_REPO = "chief-king-images"
PUBLIC_CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_USERNAME}/{IMAGES_REPO}@main/recipes"

def log(message):
    """طباعة فورية بدون تخزين مؤقت لعرضها مباشرة في GitHub Actions Logs"""
    print(message, flush=True)

def generate_and_save_webp(recipe_name, recipe_id, output_path):
    """توليد الصورة وتتبع تفاصيل العملية بحجم الملف والوقت"""
    prompt = urllib.parse.quote(f"delicious food photograph of {recipe_name}, high quality culinary presentation, 8k plate dish")
    ai_url = f"https://pollinations.ai/p/{prompt}?width=800&height=600&seed={recipe_id}&nologo=true"
    
    start_time = time.time()
    
    for attempt in range(1, 4):
        log(f"   ↳ [محاولة {attempt}/3] طلب توليد الصورة للوصفة (#{recipe_id})...")
        try:
            res = requests.get(ai_url, timeout=25)
            log(f"   ↳ [رمز الاستجابة]: {res.status_code}")
            
            if res.status_code == 200:
                raw_size_kb = len(res.content) / 1024
                
                # فتح الصورة ومعالجتها
                img = Image.open(BytesIO(res.content))
                img = img.convert("RGB")
                img.save(output_path, "WEBP", quality=80, optimize=True)
                
                webp_size_kb = os.path.getsize(output_path) / 1024
                elapsed = time.time() - start_time
                
                log(f"   ↳ [نجاح التوليد]: الحجم الأصلي: {raw_size_kb:.1f}KB ← المضغوط: {webp_size_kb:.1f}KB | المستغرق: {elapsed:.2f} ثانية")
                return True
            else:
                log(f"   ⚠️ فشل الطلب بكود: {res.status_code}. الانتظار ثانيتين...")
        except requests.exceptions.Timeout:
            log("   ⚠️ انتهت مهلة الاتصال (Timeout). جاري إعادة المحاولة...")
        except Exception as e:
            log(f"   ⚠️ خطأ أثناء المعالجة: {str(e)}")
            
        time.sleep(2)
        
    log(f"   ❌ فشلت جميع المحاولات للوصفة #{recipe_id}.")
    return False

def process_chunk(chunk_id):
    input_file = f"chunk_recipes_seo/chunk_{chunk_id}.json"
    output_dir = "output_recipes_seo"
    images_dir = "output_images"
    
    log(f"=== [بدء السيرفر الخاص بـ Chunk #{chunk_id}] ===")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    log(f"✔ تم تجهيز المجلدات المحلية: '{output_dir}' و '{images_dir}'")
    
    if not os.path.exists(input_file):
        log(f"❌ خطأ قاتل: الملف المطلوب غير موجود: {input_file}")
        sys.exit(1)
        
    with open(input_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
        
    total_recipes = len(recipes)
    log(f"📖 تم تحميل {total_recipes} وصفة من الملف {input_file}")
    
    updated_recipes = []
    success_count = 0
    fail_count = 0
    
    chunk_start_time = time.time()
    
    for index, recipe in enumerate(recipes, start=1):
        recipe_id = recipe.get("id")
        recipe_name = recipe.get("name", "recipe")
        
        log(f"\n[{index}/{total_recipes}] جاري معالجة: '{recipe_name}' (ID: {recipe_id})")
        
        webp_filename = f"recipe_{recipe_id}.webp"
        local_image_path = os.path.join(images_dir, webp_filename)
        cdn_image_url = f"{PUBLIC_CDN_BASE}/{webp_filename}"
        
        success = generate_and_save_webp(recipe_name, recipe_id, local_image_path)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            cdn_image_url = "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=800"
            
        # إعادة بناء الكائن لوضع image أسفل description مباشرة
        new_recipe = {}
        for key, value in recipe.items():
            new_recipe[key] = value
            if key == "description":
                new_recipe["image"] = cdn_image_url
                
        if "image" not in new_recipe:
            new_recipe["image"] = cdn_image_url
            
        updated_recipes.append(new_recipe)

    # حفظ الملف النهائي
    output_file = os.path.join(output_dir, f"chunk_{chunk_id}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
        
    total_elapsed = time.time() - chunk_start_time
    log(f"\n==========================================")
    log(f"🎉 اكتمل عمل السيرفر لـ Chunk #{chunk_id} بنجاح!")
    log(f"📊 الإحصائيات: ناجح ({success_count}) | فاشل ({fail_count}) | الإجمالي ({total_recipes})")
    log(f"⏱️ الإجمالي الزمني: {total_elapsed / 60:.2f} دقيقة")
    log(f"💾 تم حفظ الملف المحدث في: {output_file}")
    log(f"==========================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("❌ خطأ: يرجى تمرير رقم الـ Chunk كمعامل مدخل.")
        sys.exit(1)
        
    chunk_num = sys.argv[1]
    process_chunk(chunk_num)
