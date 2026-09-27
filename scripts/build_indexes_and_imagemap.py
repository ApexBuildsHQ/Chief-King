import os
import sys
import json
import time

# تفعيل الطباعة الفورية اللحظية
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
    print(f"[Step 1/2] Building images_map.json from English source files...", flush=True)
    print(f"Found {len(languages)} total language directories.\n", flush=True)

    # 1. بناء images_map.json
    images_map = {}
    en_dir = os.path.join(base_dir, "en")
    
    if os.path.exists(en_dir):
        en_files = sorted(
            [f for f in os.listdir(en_dir) if f.startswith("chunk_") and f.endswith(".json")],
            key=lambda x: int(x.split('_')[1].split('.')[0])
        )
        print(f"Reading {len(en_files)} English chunk files to build master images map...", flush=True)

        for file in en_files:
            file_path = os.path.join(en_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                for r in recipes:
                    images_map[str(r["id"])] = r.get("image", "")
            print(f"   Processed {file} -> Total mapped images so far: {len(images_map)}", flush=True)

        os.makedirs("public/data", exist_ok=True)
        map_output_path = "public/data/images_map.json"
        with open(map_output_path, 'w', encoding='utf-8') as f:
            json.dump(images_map, f, ensure_ascii=False, indent=2)
        print(f"\n[✓ SUCCESS] Created Master Images Map: {map_output_path} ({len(images_map)} total items)\n", flush=True)
    else:
        print("[!] Warning: English directory 'en' not found. Creating empty images_map.json.", flush=True)

    # 2. إنشاء ملفات الفهارس الأربعة لكل لغة
    print(f"[Step 2/2] Generating 4 Index Files (index_1 to index_4) for each language...", flush=True)

    for lang_idx, lang in enumerate(languages, 1):
        lang_dir = os.path.join(base_dir, lang)
        print(f"--> [{lang_idx}/{len(languages)}] Building indexes for language: '{lang}'", flush=True)

        chunk_files = sorted(
            [f for f in os.listdir(lang_dir) if f.startswith("chunk_") and f.endswith(".json")],
            key=lambda x: int(x.split('_')[1].split('.')[0])
        )

        all_indexes = []
        for file in chunk_files:
            file_path = os.path.join(lang_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                for r in recipes:
                    all_indexes.append({
                        "id": str(r["id"]),
                        "name": r["name"],
                        "category": r["category"],
                        "c": r["c"]
                    })

        total_lang_recipes = len(all_indexes)
        items_per_index = 5000

        for idx_num in range(1, 5):
            start = (idx_num - 1) * items_per_index
            end = start + items_per_index
            index_chunk = all_indexes[start:end]

            index_path = os.path.join(lang_dir, f"index_{idx_num}.json")
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_chunk, f, ensure_ascii=False, indent=2)

            print(f"     [✓ Created Index] {index_path} ({len(index_chunk)} items)", flush=True)

        print(f"    Completed '{lang}' indexes ({total_lang_recipes} total recipes processed).\n", flush=True)

    total_time = time.time() - start_time
    print("==================================================", flush=True)
    print(f"ALL ASSETS & INDEXES GENERATED SUCCESSFULLY IN {total_time:.2f} SECONDS!", flush=True)
    print("==================================================\n", flush=True)

if __name__ == "__main__":
    build_global_assets()
