const fs = require('fs');
require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');

// 1. جلب مفتاح API الرابع فقط
const API_KEY = process.env.GEMINI_KEY_4;

if (!API_KEY) {
  console.error("❌ خطأ: لم يتم العثور على GEMINI_KEY_4 في ملف .env");
  process.exit(1);
}

// إعداد مجسم الذكاء الاصطناعي بواسطة الموديل المعتمد 2.0-flash
const genAI = new GoogleGenerativeAI(API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

// 2. الفئات الـ 20 الشاملة لأعلى الأكلات بحثاً عالمياً
const categories = [
  "Fast Food & Burgers", "Pizzas & Pies", "Pasta & Noodles", "Chicken & Poultry",
  "Meat & Steak", "Seafood & Fish", "Rice & Grain Dishes", "Cakes & Pastries",
  "Cookies & Biscuits", "Cold Desserts & Ice Cream", "Breakfast & Pancakes",
  "Soups & Broths", "Salads & Appetizers", "Smoothies & Drinks", "Keto & Low Carb",
  "Vegan & Vegetarian", "Fried Foods & Snacks", "Sauces & Dips", "Casseroles & Stews", "Viral Trending Recipes"
];

// دالة الانتظار الزمني لتفادي تجاوز حد الـ 15 طلب/دقيقة (15 RPM)
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchRecipeBatch(category, batchNum) {
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

  const outputFile = './master_20k_recipes.json';
  const uniqueSlugs = new Set();
  let masterRecipes = [];
  let idCounter = 1;

  // استرجاع البيانات السابقة تلقائياً في حال إعادة تشغيل السكريبت
  if (fs.existsSync(outputFile)) {
    try {
      const existingData = JSON.parse(fs.readFileSync(outputFile, 'utf8'));
      if (Array.isArray(existingData) && existingData.length > 0) {
        masterRecipes = existingData;
        masterRecipes.forEach(item => {
          if (item.slug) uniqueSlugs.add(item.slug);
          if (item.id >= idCounter) idCounter = item.id + 1;
        });
        console.log(`📂 تم تحميل ${masterRecipes.length} وصفة موجودة سابقاً. جاري الاستكمال...`);
      }
    } catch (e) {
      console.log("⚠️ تعذر قراءة الملف القديم، سيتم البدء من جديد.");
    }
  }

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

      // 💾 حفظ تلقائي فوري بعد كل دفعة لضمان سلامة البيانات
      fs.writeFileSync(outputFile, JSON.stringify(masterRecipes, null, 2), 'utf8');

      console.log(`   - الدفعة ${batch}/5: تمت إضافة ${addedInBatch} وصفة جديدة. (الإجمالي: ${masterRecipes.length})`);

      // ⏳ انتظار 4.5 ثانية لحماية المفتاح من تجاوز 15 طلب/دقيقة
      await sleep(4500);
    }
  }

  console.log(`\n🎉 اكتملت العملية بنجاح! تم حفظ ${masterRecipes.length} وصفة فريدة 100% في ${outputFile}`);
}

startSeedingProcess();
