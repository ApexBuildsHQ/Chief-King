import math
import os
import sys
import time
import json

sys.stdout.reconfigure(line_buffering=True)

def build_global_assets():
    start_time = time.time()
    print("\n==================================================", flush=True)
    print("STARTING GLOBAL ASSETS CONSOLIDATION (IMAGES MAP & INDEXES)", flush=True)
    print("==================================================\n", flush=True)

    base_dir = "public/data/recipes"
    
    if not os.path.exists(base_dir):
        print(f"[ERROR] Directory {base_dir} does not exist!", flush=True)
        sys.exit(1)

    languages = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
    
    # 1. بناء images_map.json بتنسيق (ID -> {name, image})
    print(f"[Step 1/2] Building minified images_map.json with English names & images...", flush=True)
    images_map = {}
    en_dir = os.path.join(base_dir, "en")
    
    if os.path.exists(en_dir):
        en_files = []
        for f in os.listdir(en_dir):
            if f.startswith("chunk_") and f.endswith(".json"):
                try:
                    chunk_num = int(f.split('_')[1].split('.')[0])
                    en_files.append((chunk_num, f))
                except ValueError:
                    continue
        
        en_files.sort(key=lambda x: x[0])

        for _, file in en_files:
            file_path = os.path.join(en_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                for r in recipes:
                    rec_id = str(r.get("id", ""))
                    if rec_id:
                        images_map[rec_id] = {
                            "name": r.get("name", ""),
                            "image": r.get("image", "")
                        }

        os.makedirs("public/data", exist_ok=True)
        map_output_path = "public/data/images_map.json"
        
        with open(map_output_path, 'w', encoding='utf-8') as f:
            json.dump(images_map, f, ensure_ascii=False, separators=(',', ':'))
            
        print(f"[✓ SUCCESS] Created Master Images Map: {map_output_path} ({len(images_map)} items)\n", flush=True)

    # 2. إنشاء ملفات الفهارس الديناميكية المضغوطة
    print(f"[Step 2/2] Generating Dynamic Minified Index Files for each language...", flush=True)
    items_per_index = 5000

    for lang_idx, lang in enumerate(languages, 1):
        lang_dir = os.path.join(base_dir, lang)
        chunk_files = []
        for f in os.listdir(lang_dir):
            if f.startswith("chunk_") and f.endswith(".json"):
                try:
                    chunk_num = int(f.split('_')[1].split('.')[0])
                    chunk_files.append((chunk_num, f))
                except ValueError:
                    continue

        chunk_files.sort(key=lambda x: x[0])

        all_indexes = []
        for _, file in chunk_files:
            file_path = os.path.join(lang_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                for r in recipes:
                    all_indexes.append({
                        "id": str(r.get("id", "")),
                        "name": r.get("name", ""),
                        "category": r.get("category", ""),
                        "c": r.get("c", 1)
                    })

        total_recipes = len(all_indexes)
        total_index_files = math.ceil(total_recipes / items_per_index) if total_recipes > 0 else 1

        for idx_num in range(1, total_index_files + 1):
            start = (idx_num - 1) * items_per_index
            end = start + items_per_index
            index_chunk = all_indexes[start:end]

            index_path = os.path.join(lang_dir, f"index_{idx_num}.json")
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_chunk, f, ensure_ascii=False, separators=(',', ':'))

        print(f"    [✓ Created Indexes for '{lang}'] Total recipes: {total_recipes}", flush=True)

    total_time = time.time() - start_time
    print(f"\nALL ASSETS & INDEXES GENERATED IN {total_time:.2f} SECONDS!\n", flush=True)

if __name__ == "__main__":
    build_global_assets()
