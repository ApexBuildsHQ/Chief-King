import json
import os
import urllib.parse
from duckduckgo_search import DDGS

MASTER_FILE = './master_20k_recipes.json'
FALLBACK_IMAGE = "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=800&q=80"

def get_image(title):
    try:
        results = DDGS().images(f"{title} food dish recipe HD", max_results=1)
        if results and len(results) > 0:
            return results[0]['image']
    except Exception: pass
    return FALLBACK_IMAGE

def process():
    if not os.path.exists(MASTER_FILE):
        print(f"❌ لم يتم العثور على {MASTER_FILE}")
        return

    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    print(f"📸 جاري إضافة الصور والميديا لـ {len(recipes)} وصفة...")
    for recipe in recipes:
        if "image" not in recipe or not recipe["image"]:
            recipe["image"] = get_image(recipe.get("title", ""))
        
        encoded_query = urllib.parse.quote(f"{recipe.get('title', '')} recipe")
        recipe["youtube_search_url"] = f"https://www.youtube.com/results?search_query={encoded_query}"
        recipe["youtube_embed_url"] = f"https://www.youtube.com/embed?listType=search&list={encoded_query}"

    with open(MASTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print("✅ تم تجهيز الصور وفيديوهات اليوتيوب بنجاح!")

if __name__ == "__main__":
    process()

