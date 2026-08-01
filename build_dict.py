import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

# 🌍 الـ 50 لغة العالمية المستهدفة
TARGET_LANGUAGES = [
    'ar', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-CN', 'ja', 'ko',
    'tr', 'hi', 'bn', 'pa', 'vi', 'th', 'el', 'nl', 'sv', 'no',
    'fi', 'da', 'pl', 'cs', 'hu', 'ro', 'uk', 'he', 'id', 'ms',
    'fa', 'ur', 'sw', 'am', 'tl', 'zu', 'kn', 'ta', 'te', 'mr',
    'gu', 'ml', 'si', 'my', 'km', 'lo', 'ne', 'hy', 'sq', 'bs'
]

DICT_FILE = './ingredients_dict.json'

NUMBER_SYSTEMS = {
    "ar": {"0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩"},
    "fa": {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"},
    "ur": {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"},
    "hi": {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"},
    "bn": {"0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪", "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯"},
    "ne": {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"}
}

RAW_UNITS = [
    "ml", "liter", "g", "kg", "cup", "tbsp", "tsp", "pinch", "piece", 
    "clove", "slice", "oz", "lb", "quart", "gallon", "dash", "handful", 
    "can", "package", "bunch", "head", "stalk", "sprig", "tin", "sheet", 
    "drop", "stick", "bar", "cube", "jar", "bottle", "scoop"
]

RAW_INGREDIENTS = [
    "ground beef", "beef", "beef steak", "beef ribs", "veal", "lamb", "ground lamb",
    "lamb chops", "chicken breast", "chicken thigh", "chicken wing", "chicken leg",
    "whole chicken", "turkey", "duck", "goat meat", "bacon", "sausage", "ham",
    "fish fillet", "salmon", "tuna", "cod", "sea bass", "tilapia", "trout",
    "shrimp", "prawns", "lobster", "crab", "squid", "calamari", "octopus",
    "mussels", "clams", "oysters", "anchovies", "sardines", "garlic", "onion", 
    "red onion", "white onion", "spring onion", "shallot", "leek", "tomato", 
    "cherry tomato", "sun-dried tomato", "potato", "sweet potato", "carrot",
    "cucumber", "zucchini", "eggplant", "bell pepper", "red bell pepper", "green pepper",
    "chili pepper", "jalapeno", "spinach", "lettuce", "kale", "arugula", "broccoli",
    "cauliflower", "cabbage", "red cabbage", "brussels sprouts", "asparagus", "celery",
    "artichoke", "green beans", "peas", "corn", "mushroom", "button mushroom",
    "parsley", "cilantro", "basil", "oregano", "thyme", "rosemary", "mint", "dill",
    "sage", "tarragon", "ginger", "lemongrass", "lemon", "lime", "orange", "apple", 
    "banana", "strawberry", "blueberry", "raspberry", "blackberry", "mango", "pineapple", 
    "peach", "plum", "cherry", "fig", "date", "raisins", "cranberry", "avocado", "coconut", 
    "pomegranate", "olive oil", "extra virgin olive oil", "vegetable oil", "canola oil", 
    "coconut oil", "sesame oil", "sunflower oil", "corn oil", "avocado oil", "butter", 
    "unsalted butter", "ghee", "margarine", "lard", "milk", "whole milk", "skim milk", 
    "heavy cream", "whipping cream", "sour cream", "condensed milk", "evaporated milk", 
    "yogurt", "greek yogurt", "buttermilk", "egg", "egg yolk", "egg white", "cheddar cheese", 
    "mozzarella cheese", "parmesan cheese", "feta cheese", "cream cheese", "ricotta cheese", 
    "gouda cheese", "swiss cheese", "salt", "sea salt", "kosher salt", "black pepper", 
    "white pepper", "paprika", "smoked paprika", "sweet paprika", "cayenne pepper", 
    "cumin", "ground cumin", "coriander", "turmeric", "cinnamon", "cardamom", "cloves", 
    "nutmeg", "star anise", "curry powder", "garam masala", "saffron", "chili flakes", 
    "mustard powder", "vanilla extract", "vanilla bean", "baking powder", "baking soda", 
    "yeast", "dry yeast", "flour", "all-purpose flour", "whole wheat flour", "bread flour", 
    "cake flour", "cornstarch", "semolina", "sugar", "white sugar", "brown sugar", 
    "powdered sugar", "honey", "maple syrup", "rice", "basmati rice", "jasmine rice", 
    "arborio rice", "brown rice", "pasta", "spaghetti", "penne", "macaroni", "noodles", 
    "ramen noodles", "oats", "quinoa", "couscous", "chickpeas", "lentils", "red lentils", 
    "green lentils", "black beans", "kidney beans", "white beans", "soy sauce", 
    "low sodium soy sauce", "fish sauce", "oyster sauce", "hoisin sauce", "teriyaki sauce", 
    "hot sauce", "sriracha", "worcestershire sauce", "tomato paste", "tomato sauce", 
    "mayonnaise", "mustard", "dijon mustard", "ketchup", "tahini", "peanut butter", 
    "almonds", "walnuts", "cashews", "pistachios", "peanuts", "pecans", "hazelnuts", 
    "pine nuts", "sesame seeds", "chia seeds", "flax seeds", "vinegar", "white vinegar", 
    "apple cider vinegar", "balsamic vinegar"
]

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_translation(task):
    """دالة لترجمة عنصر واحد لفرع لغوي محدد"""
    category, item, lang = task
    try:
        trans = GoogleTranslator(source='en', target=lang).translate(item)
        return category, item, lang, trans
    except Exception:
        return category, item, lang, item

def build_mega_dictionary():
    print("🚀 بدء إنشاء القاموس الشامل بطريقة الترجمة المتوازية السريعة...")

    current_dict = load_json(DICT_FILE)
    if "number_systems" not in current_dict:
        current_dict["number_systems"] = NUMBER_SYSTEMS
    if "units" not in current_dict:
        current_dict["units"] = {}
    if "ingredients" not in current_dict:
        current_dict["ingredients"] = {}

    tasks = []

    # تجميع جميع المهام الناقصة فقط
    for unit in RAW_UNITS:
        if unit not in current_dict["units"]:
            current_dict["units"][unit] = {"en": unit}
        for lang in TARGET_LANGUAGES:
            if lang not in current_dict["units"][unit]:
                tasks.append(("units", unit, lang))

    for ing in RAW_INGREDIENTS:
        if ing not in current_dict["ingredients"]:
            current_dict["ingredients"][ing] = {"en": ing}
        for lang in TARGET_LANGUAGES:
            if lang not in current_dict["ingredients"][ing]:
                tasks.append(("ingredients", ing, lang))

    total_tasks = len(tasks)
    print(f"📊 إجمالي عمليات الترجمة المطلوبة: {total_tasks} عملية...")

    if total_tasks == 0:
        print("✅ القاموس اكتمال ترجمته بالكامل مسبقاً!")
        return

    # تنفيذ الترجمة بواسطة 10 خيوط متوازية (10 Threads)
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_translation, task) for task in tasks]
        
        for future in as_completed(futures):
            category, item, lang, trans = future.result()
            current_dict[category][item][lang] = trans
            completed += 1
            
            if completed % 100 == 0 or completed == total_tasks:
                print(f"⚡ تم إنجاز {completed}/{total_tasks} عملية ترجمة...", flush=True)
                save_json(DICT_FILE, current_dict)

    save_json(DICT_FILE, current_dict)
    print("\n🎉 تم إنشاء وتحسين الملف النهائي وحفظه بنجاح باسم ingredients_dict.json!")

if __name__ == "__main__":
    build_mega_dictionary()

