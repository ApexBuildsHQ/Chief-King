import json
import os
import time
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

# 1️⃣ أنظمة الأرقام المحلية للغات الشرقية
NUMBER_SYSTEMS = {
    "ar": {"0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩"},
    "fa": {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"},
    "ur": {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"},
    "hi": {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"},
    "bn": {"0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪", "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯"},
    "ne": {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"}
}

# 2️⃣ الوحدات والمقاييس الشاملة
RAW_UNITS = [
    "ml", "liter", "g", "kg", "cup", "tbsp", "tsp", "pinch", "piece", 
    "clove", "slice", "oz", "lb", "quart", "gallon", "dash", "handful", 
    "can", "package", "bunch", "head", "stalk", "sprig", "tin", "sheet", 
    "drop", "stick", "bar", "cube", "jar", "bottle", "scoop"
]

# 3️⃣ القائمة الشاملة والضخمة لجميع المقادير والمكونات العالمية
RAW_INGREDIENTS = [
    # --- اللحوم والدواجن (Meat & Poultry) ---
    "ground beef", "beef", "beef steak", "beef ribs", "veal", "lamb", "ground lamb",
    "lamb chops", "chicken breast", "chicken thigh", "chicken wing", "chicken leg",
    "whole chicken", "turkey", "duck", "goat meat", "bacon", "sausage", "ham",

    # --- المأكولات البحرية (Seafood) ---
    "fish fillet", "salmon", "tuna", "cod", "sea bass", "tilapia", "trout",
    "shrimp", "prawns", "lobster", "crab", "squid", "calamari", "octopus",
    "mussels", "clams", "oysters", "anchovies", "sardines",

    # --- الخضراوات والأعشاب الطازجة (Vegetables & Herbs) ---
    "garlic", "onion", "red onion", "white onion", "spring onion", "shallot", "leek",
    "tomato", "cherry tomato", "sun-dried tomato", "potato", "sweet potato", "carrot",
    "cucumber", "zucchini", "eggplant", "bell pepper", "red bell pepper", "green pepper",
    "chili pepper", "jalapeno", "spinach", "lettuce", "kale", "arugula", "broccoli",
    "cauliflower", "cabbage", "red cabbage", "brussels sprouts", "asparagus", "celery",
    "artichoke", "green beans", "peas", "corn", "mushroom", "button mushroom",
    "parsley", "cilantro", "basil", "oregano", "thyme", "rosemary", "mint", "dill",
    "sage", "tarragon", "ginger", "lemongrass",

    # --- الفواكه المخصصة للطهي والحلويات (Fruits) ---
    "lemon", "lime", "orange", "apple", "banana", "strawberry", "blueberry", "raspberry",
    "blackberry", "mango", "pineapple", "peach", "plum", "cherry", "fig", "date",
    "raisins", "cranberry", "avocado", "coconut", "pomegranate",

    # --- الزيوت والدهون (Oils & Fats) ---
    "olive oil", "extra virgin olive oil", "vegetable oil", "canola oil", "coconut oil",
    "sesame oil", "sunflower oil", "corn oil", "avocado oil", "butter", "unsalted butter",
    "ghee", "margarine", "lard",

    # --- منتجات الألبان والبيض (Dairy & Eggs) ---
    "milk", "whole milk", "skim milk", "heavy cream", "whipping cream", "sour cream",
    "condensed milk", "evaporated milk", "yogurt", "greek yogurt", "buttermilk",
    "egg", "egg yolk", "egg white", "cheddar cheese", "mozzarella cheese", "parmesan cheese",
    "feta cheese", "cream cheese", "ricotta cheese", "gouda cheese", "swiss cheese",

    # --- التوابل والبهارات (Spices & Seasonings) ---
    "salt", "sea salt", "kosher salt", "black pepper", "white pepper", "paprika",
    "smoked paprika", "sweet paprika", "cayenne pepper", "cumin", "ground cumin",
    "coriander", "turmeric", "cinnamon", "cardamom", "cloves", "nutmeg", "star anise",
    "curry powder", "garam masala", "saffron", "chili flakes", "mustard powder",
    "vanilla extract", "vanilla bean", "baking powder", "baking soda", "yeast", "dry yeast",

    # --- الحبوب والنشويات والبقوليات (Grains & Legumes) ---
    "flour", "all-purpose flour", "whole wheat flour", "bread flour", "cake flour",
    "cornstarch", "semolina", "sugar", "white sugar", "brown sugar", "powdered sugar",
    "honey", "maple syrup", "rice", "basmati rice", "jasmine rice", "arborio rice",
    "brown rice", "pasta", "spaghetti", "penne", "macaroni", "noodles", "ramen noodles",
    "oats", "quinoa", "couscous", "chickpeas", "lentils", "red lentils", "green lentils",
    "black beans", "kidney beans", "white beans",

    # --- الصوصات والمكسرات والمعدلات (Sauces, Nuts & Condiments) ---
    "soy sauce", "low sodium soy sauce", "fish sauce", "oyster sauce", "hoisin sauce",
    "teriyaki sauce", "hot sauce", "sriracha", "worcestershire sauce", "tomato paste",
    "tomato sauce", "mayonnaise", "mustard", "dijon mustard", "ketchup", "tahini",
    "peanut butter", "almonds", "walnuts", "cashews", "pistachios", "peanuts",
    "pecans", "hazelnuts", "pine nuts", "sesame seeds", "chia seeds", "flax seeds",
    "chia seeds", "vinegar", "white vinegar", "apple cider vinegar", "balsamic vinegar"
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

def translate_safe(text, target_lang):
    """ترجمة مع إعادة المحاولة التلقائية في حالة انقطاع الشبكة"""
    for attempt in range(3):
        try:
            return GoogleTranslator(source='en', target=target_lang).translate(text)
        except Exception:
            time.sleep(1)
    return text  # العودة للنص الأصلي إذا فشلت المحاولات

def build_mega_dictionary():
    print("🚀 بدء إنشاء القاموس الشامل الأكبر للمقادير والوحدات...")

    current_dict = load_json(DICT_FILE)
    
    if "number_systems" not in current_dict:
        current_dict["number_systems"] = NUMBER_SYSTEMS
    if "units" not in current_dict:
        current_dict["units"] = {}
    if "ingredients" not in current_dict:
        current_dict["ingredients"] = {}

    # 1. معالجة وترجمة الوحدات
    print(f"\n📏 [1/2] جاري معالجة {len(RAW_UNITS)} وحدة قياس مع الـ 50 لغة...")
    for idx, unit in enumerate(RAW_UNITS, 1):
        if unit not in current_dict["units"]:
            current_dict["units"][unit] = {"en": unit}

        updated = False
        for lang in TARGET_LANGUAGES:
            if lang not in current_dict["units"][unit]:
                trans = translate_safe(unit, lang)
                current_dict["units"][unit][lang] = trans
                updated = True

        if updated:
            save_json(DICT_FILE, current_dict)
            print(f"  ✅ ({idx}/{len(RAW_UNITS)}) اكتملت وحدة: {unit}")

    # 2. معالجة وترجمة المكونات
    print(f"\n🥦 [2/2] جاري معالجة {len(RAW_INGREDIENTS)} مكون عالمي لـ 50 لغة...")
    for idx, ing in enumerate(RAW_INGREDIENTS, 1):
        if ing not in current_dict["ingredients"]:
            current_dict["ingredients"][ing] = {"en": ing}

        updated = False
        for lang in TARGET_LANGUAGES:
            if lang not in current_dict["ingredients"][ing]:
                trans = translate_safe(ing, lang)
                current_dict["ingredients"][ing][lang] = trans
                updated = True

        if updated:
            save_json(DICT_FILE, current_dict)
            print(f"  ✅ ({idx}/{len(RAW_INGREDIENTS)}) تم ترجمة المكون: {ing}")

    print("\n🎉 تم إنشاء الملف النهائي وحفظه بنجاح باسم ingredients_dict.json!")

if __name__ == "__main__":
    build_mega_dictionary()

