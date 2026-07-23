const fs = require('fs');
require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');

// 1. جلب وتصفية المفاتيح الأربعة
const API_KEYS = [
  process.env.GEMINI_KEY_1,
  process.env.GEMINI_KEY_2,
  process.env.GEMINI_KEY_3,
  process.env.GEMINI_KEY_4
].filter(Boolean);

if (API_KEYS.length === 0) {
  console.error("❌ خطأ: لم يتم العثور على مفاتيح API. تأكد من إعداد ملف .env بـ GEMINI_KEY_1 إلى 4");
  process.exit(1);
}

// 2. الفئات الـ 20 الشاملة لأعلى الأكلات بحثاً عالمياً
const categories = [
  "Fast Food & Burgers", "Pizzas & Pies", "Pasta & Noodles", "Chicken & Poultry",
  "Meat & Steak", "Seafood & Fish", "Rice & Grain Dishes", "Cakes & Pastries",
  "Cookies & Biscuits", "Cold Desserts & Ice Cream", "Breakfast & Pancakes",
  "Soups & Broths", "Salads & Appetizers", "Smoothies & Drinks", "Keto & Low Carb",
  "Vegan & Vegetarian", "Fried Foods & Snacks", "Sauces & Dips", "Casseroles & Stews", "Viral Trending Recipes"
];

let currentKeyIndex = 0;
function getNextKey() {
  const key = API_KEYS[currentKeyIndex];
  currentKeyIndex = (currentKeyIndex + 1) % API_KEYS.length;
  return key;
}

async function fetchRecipeBatch(category, batchNum) {
  const apiKey = getNextKey();
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

  const prompt = `Act as an expert Global SEO Food Researcher.
Provide a clean JSON array of 200 UNIQUE, HIGH-SEARCH-VOLUME recipe titles globally in the category "${category}" (Batch ${batchNum} of 5).
Target real user search queries with millions of searches on Google.
Return ONLY a valid JSON array of strings (e.g., ["Classic Cheeseburger", "Crispy French Fries"]). No markdown formatting, no prose.`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text().trim();
    const cleanJson = text.replace(/```json|```/g, '').trim();
    return JSON.parse(cleanJson);
  } catch (err) {
    console.error(`⚠️ خطأ في الدفعة ${batchNum} للفئة ${category}:`, err.message);
    return [];
  }
}

async function startSeedingProcess() {
  console.log("🚀 بدء استخراج 20,000 وصفة فريدة ومستهدفة للـ SEO...");
  
  const uniqueSlugs = new Set();
  const masterRecipes = [];
  let idCounter = 1;

  for (let i = 0; i < categories.length; i++) {
    const cat = categories[i];
    console.log(`\n📌 [${i + 1}/20] معالجة فئة: ${cat}`);

    for (let batch = 1; batch <= 5; batch++) {
      const titles = await fetchRecipeBatch(cat, batch);
      let addedInBatch = 0;

      for (let title of titles) {
        if (!title || typeof title !== 'string') continue;

        const cleanTitle = title.trim();
        const slug = cleanTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

        if (!uniqueSlugs.has(slug) && slug.length > 2) {
          uniqueSlugs.add(slug);
          masterRecipes.push({
            id: idCounter++,
            title: cleanTitle,
            slug: slug,
            category: cat
          });
          addedInBatch++;
        }
      }

      console.log(`   - الدفعة ${batch}/5: تمت إضافة ${addedInBatch} وصفة جديدة. (الإجمالي: ${masterRecipes.length})`);
      await new Promise(r => setTimeout(r, 1500));
    }
  }

  fs.writeFileSync('./master_20k_recipes.json', JSON.stringify(masterRecipes, null, 2), 'utf8');
  console.log(`\n🎉 اكتملت العملية! تم حفظ ${masterRecipes.length} وصفة فريدة 100% في master_20k_recipes.json`);
}

startSeedingProcess();
