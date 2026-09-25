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
    print(message, flush=True)

def generate_and_save_webp(recipe_name, recipe_id, output_path):
    prompt = urllib.parse.quote(f"delicious food photograph of {recipe_name}, high quality culinary presentation, 8k plate dish")
    ai_url = f"https://pollinations.ai/p/{prompt}?width=800&height=600&seed={recipe_id}&nologo=true"
    
    start_time = time.time()
    for attempt in range(1, 4):
        log(f"   ↳ [محاولة {attempt}/3] طلب توليد الصورة للوصفة (#{recipe_id})...")
        try:
            res = requests.get(ai_url, timeout=25)
            if res.status_code == 200:
                raw_size_kb = len(res.content) / 1024
                img = Image.open(BytesIO(res.content)).convert("RGB")
                img.save(output_path, "WEBP", quality=80, optimize=True)
                webp_size_kb = os.path.getsize(output_path) / 1024
                elapsed = time.time() - start_time
                log(f"   ↳ [نجاح التوليد]: الحجم الأصلي: {raw_size_kb:.1f}KB ← المضغوط: {webp_size_kb:.1f}KB | المستغرق: {elapsed:.2f} ثانية")
                return True
        except Exception as e:
            log(f"   ⚠️ خطأ أثناء المعالجة: {str(e)}")
        time.sleep(2)
        
    log(f"   ❌ فشلت جميع المحاولات للوصفة #{recipe_id}.")
    return False

def process_chunk(chunk_id):
    # تم التعديل للمسار والاسم الصحيحين الموجودين في المستودع
    input_file = f"output_recipes_seo/recipes_chunk_{chunk_id}.json"
    images_dir = "output_images"
    
    log(f"=== [بدء السيرفر الخاص بـ Chunk #{chunk_id}] ===")
    os.makedirs(images_dir, exist_ok=True)
    
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
            
        new_recipe = {}
        for key, value in recipe.items():
            new_recipe[key] = value
            if key == "description":
                new_recipe["image"] = cdn_image_url
                
        if "image" not in new_recipe:
            new_recipe["image"] = cdn_image_url
            
        updated_recipes.append(new_recipe)

    # حفظ التحديثات في نفس الملف
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
        
    total_elapsed = time.time() - chunk_start_time
    log(f"\n==========================================")
    log(f"🎉 اكتمل عمل السيرفر لـ Chunk #{chunk_id} بنجاح!")
    log(f"📊 الإحصائيات: ناجح ({success_count}) | فاشل ({fail_count}) | الإجمالي ({total_recipes})")
    log(f"⏱️ الإجمالي الزمني: {total_elapsed / 60:.2f} دقيقة")
    log(f"💾 تم تحديث الملف: {input_file}")
    log(f"==========================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("❌ خطأ: يرجى تمرير رقم الـ Chunk كمعامل مدخل.")
        sys.exit(1)
        
    chunk_num = sys.argv[1]
    process_chunk(chunk_num)
