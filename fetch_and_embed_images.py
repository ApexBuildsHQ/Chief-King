import sys
import os
import json
import time
import urllib.parse
import requests
from PIL import Image
from io import BytesIO

# الإعدادات الرئيسية
GITHUB_USERNAME = "ApexBuildsHQ"
IMAGES_REPO = "chief-king-images"
PUBLIC_CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_USERNAME}/{IMAGES_REPO}@main/recipes"

def generate_and_save_webp(recipe_name, recipe_id, output_path):
    """توليد صورة احترافية للوجبة وتحويلها إلى صيغة WebP مضغوطة"""
    prompt = urllib.parse.quote(f"delicious food photograph of {recipe_name}, high quality culinary presentation, 8k plate dish")
    ai_url = f"https://pollinations.ai/p/{prompt}?width=800&height=600&seed={recipe_id}&nologo=true"
    
    for attempt in range(3):
        try:
            res = requests.get(ai_url, timeout=20)
            if res.status_code == 200:
                # فتح الصورة وتقليل حجمها وحفظها بصيغة WebP
                img = Image.open(BytesIO(res.content))
                img = img.convert("RGB")
                img.save(output_path, "WEBP", quality=80, optimize=True)
                return True
        except Exception:
            time.sleep(2)
    return False

def process_chunk(chunk_id):
    input_file = f"chunk_recipes_seo/chunk_{chunk_id}.json"
    output_dir = "output_recipes_seo"
    images_dir = "output_images"
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"❌ الملف غير موجود: {input_file}")
        sys.exit(1)
        
    with open(input_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
        
    updated_recipes = []
    
    print(f"🚀 بدء معالجة Chunk #{chunk_id} (إجمالي الوصفات: {len(recipes)})...")
    
    for index, recipe in enumerate(recipes):
        recipe_id = recipe.get("id")
        recipe_name = recipe.get("name", "recipe")
        
        webp_filename = f"recipe_{recipe_id}.webp"
        local_image_path = os.path.join(images_dir, webp_filename)
        cdn_image_url = f"{PUBLIC_CDN_BASE}/{webp_filename}"
        
        # 1. توليد وحفظ الصورة محلياً
        success = generate_and_save_webp(recipe_name, recipe_id, local_image_path)
        if not success:
            # صورة افتراضية في حالة الفشل الممتد
            cdn_image_url = "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=800"
            
        # 2. ترتيب الحقول بحيث يوضع image أسفل description مباشرة
        new_recipe = {}
        for key, value in recipe.items():
            new_recipe[key] = value
            if key == "description":
                new_recipe["image"] = cdn_image_url
                
        if "image" not in new_recipe:
            new_recipe["image"] = cdn_image_url
            
        updated_recipes.append(new_recipe)
        print(f"[{index + 1}/{len(recipes)}] ✅ تمت معالجة الوصفة {recipe_id}")

    # 3. حفظ ملف الـ JSON المحدث
    output_file = os.path.join(output_dir, f"chunk_{chunk_id}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated_recipes, f, ensure_ascii=False, indent=2)
        
    print(f"🎉 التكتمل Chunk #{chunk_id} وحفظ البيانات في {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("يرجى تحديد رقم الـ Chunk، مثال: python fetch_and_embed_images.py 1")
        sys.exit(1)
        
    chunk_num = sys.argv[1]
    process_chunk(chunk_num)
