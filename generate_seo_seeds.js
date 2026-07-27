const fs = require('fs');
require('dotenv').config();
const Groq = require('groq-sdk');
const { GoogleGenerativeAI } = require('@google/generative-ai');

// 1. تهيئة المفاتيح
const GROQ_KEY = process.env.GROQ_API_KEY;
const GEMINI_KEY = process.env.GEMINI_KEY_4;

if (!GROQ_KEY && !GEMINI_KEY) {
  console.error("❌ خطأ: لم يتم العثور على أي مفتاح API في ملف .env");
  process.exit(1);
}

const groq = GROQ_KEY ? new Groq({ apiKey: GROQ_KEY }) : null;
const genAI = GEMINI_KEY ? new GoogleGenerativeAI(GEMINI_KEY) : null;

// 2. الفئات الـ 20 الشاملة
const categories = [
  "Fast Food & Burgers", "Pizzas & Pies", "Pasta & Noodles", "Chicken & Poultry",
  "Meat & Steak", "Seafood & Fish", "Rice & Grain Dishes", "Cakes & Pastries",
  "Cookies & Biscuits", "Cold Desserts & Ice Cream", "Breakfast & Pancakes",
  "Soups & Broths", "Salads & Appetizers", "Smoothies & Drinks", "Keto & Low Carb",
  "Vegan & Vegetarian", "Fried Foods & Snacks", "Sauces & Dips", "Casseroles & Stews", "Viral Trending Recipes"
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const OUTPUT_FILE = './master_20k_recipes.json';
const PROGRESS_FILE = './seeding_progress.json';

// متغير لتتبع ما إذا كانت حصة Groq قد انتهت بالكامل للتحويل الدائم لـ Gemini في الجلسة الحالية
let groqExhausted = false;

// 3. دالة الاستدعاء المعتمدة على الأولوية المطلقة لـ Groq
async function fetchWithGroqFirstThenGemini(prompt) {
  // --- المرحلة الأولى: استخدام Groq حتى استنفاد الحصة بالكامل ---
  if (groq && !groqExhausted) {
    try {
      const completion = await groq.chat.completions.create({
        messages: [{ role: "user", content: prompt }],
        model: "llama-3.3-70b-versatile",
        temperature: 0.7,
        max_tokens: 4000
      });
      return completion.choices[0]?.message?.content;
    } catch (err70) {
      console.warn("⚠️ Groq (Llama 3.3) فشل أو وصل للحد، تجربة Groq (Llama 3.1)...");
      try {
        const completion = await groq.chat.completions.create({
          messages: [{ role: "user", content: prompt }],
          model: "llama-3.1-8b-instant",
          temperature: 0.7,
          max_tokens: 4000
        });
        return completion.choices[0]?.message?.content;
      } catch (err8) {
        console.warn("🔴 تم استهلاك حصة Groq بالكامل! التحويل الآن وبشكل دائم إلى Gemini...");
        groqExhausted = true; // التحويل إلى Gemini لباقي العمليات
      }
    }
  }

  // --- المرحلة الثانية: استخدام Gemini بعد نفاد Groq ---
  if (genAI) {
    try {
      const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
      const result = await model.generateContent(prompt);
      return result.response.text();
    } catch (errG2) {
      console.warn("⚠️ Gemini 2.0 Flash لم ينفذ الطلب، التجربة على Gemini 1.5 Flash...");
      try {
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
        const result = await model.generateContent(prompt);
        return result.response.text();
      } catch (errG1) {
        console.error("❌ فشلت محاولات Gemini أيضاً.");
      }
    }
  }

  return null; // تعذر الحصول على استجابة من جميع المفاتيح
}

// 4. معالجة وتنظيف الـ JSON
function parseRecipes(rawText) {
  if (!rawText) return [];
  try {
    const cleanJson = rawText.replace(/```json|```/g, '').trim();
    return JSON.parse(cleanJson);
  } catch (e) {
    const matches = rawText.match(/"([^"]+)"/g);
    if (matches) {
      return matches.map(m => m.replace(/"/g, '')).filter(m => m.length > 3 && !m.includes("recipe"));
    }
    return [];
  }
}

// 5. إدارة حفظ واسترجاع حالة التوقف (Checkpoint State)
function loadProgress() {
  if (fs.existsSync(PROGRESS_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8'));
    } catch (e) {
      return { catIndex: 0, batchIndex: 1 };
    }
  }
  return { catIndex: 0, batchIndex: 1 };
}

function saveProgress(catIndex, batchIndex) {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify({ catIndex, batchIndex }, null, 2), 'utf8');
}

// 6. تشغيل عملية التجميع والتسجيل
async function startSeedingProcess() {
  console.log("🚀 بدء نظام استخراج 20,000 وصفة مع حفظ تلقائي لموضع التوقف...");

  const uniqueSlugs = new Set();
  let masterRecipes = [];
  let idCounter = 1;

  // تحميل الوصفات المخزنة سابقاً
  if (fs.existsSync(OUTPUT_FILE)) {
    try {
      const existingData = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'));
      if (Array.isArray(existingData) && existingData.length > 0) {
        masterRecipes = existingData;
        masterRecipes.forEach(item => {
          if (item.slug) uniqueSlugs.add(item.slug);
          if (item.id >= idCounter) idCounter = item.id + 1;
        });
        console.log(`📂 تم تحميل ${masterRecipes.length} وصفة سابقة من الملف.`);
      }
    } catch (e) {
      console.log("⚠️ يتعذر قراءة ملف الوصفات القديم، سيتم البدء من جديد.");
    }
  }

  // تحميل نقطة التوقف الأخيرة
  let { catIndex, batchIndex } = loadProgress();
  console.log(`📍 الاستئناف من الفئة رقم [${catIndex + 1}/20] - الدفعة [${batchIndex}/5]`);

  for (let i = catIndex; i < categories.length; i++) {
    const cat = categories[i];
    const startBatch = (i === catIndex) ? batchIndex : 1;

    console.log(`\n📌 [${i + 1}/20] معالجة فئة: "${cat}"`);

    for (let batch = startBatch; batch <= 5; batch++) {
      console.log(`   ⏳ جلب الدفعة ${batch}/5 (200 وصفة)...`);

      const prompt = `Act as an expert Global SEO Food Researcher.
Provide a clean JSON array of 200 UNIQUE, HIGH-SEARCH-VOLUME recipe titles globally in the category "${cat}" (Batch ${batch} of 5).
Target real user search queries with millions of searches on Google.
Return ONLY a valid JSON array of strings (e.g. ["Classic Cheeseburger", "Crispy French Fries"]). No markdown formatting, no prose.`;

      const rawText = await fetchWithGroqFirstThenGemini(prompt);
      const titles = parseRecipes(rawText);

      // في حال فشل جميع النماذج والمفاتيح في إرجاع بيانات
      if (!titles || titles.length === 0) {
        console.error(`\n❌ توقف النظام: نفدت الحصص من جميع المفاتيح المتاحة عند الفئة [${i + 1}] الدفعة [${batch}].`);
        saveProgress(i, batch); // حفظ النقطة التي توقف عندها بالدقة
        console.log(`💾 تم حفظ نقطة التوقف بنجاح في ${PROGRESS_FILE}. أعد تشغيل السكريبت عند تجدد الحصص.`);
        process.exit(0);
      }

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

      // حفظ الوصفات ونقطة التقدم بعد كل دفعة ناجحة فوراً
      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(masterRecipes, null, 2), 'utf8');
      
      let nextCatIndex = i;
      let nextBatchIndex = batch + 1;
      if (nextBatchIndex > 5) {
        nextCatIndex = i + 1;
        nextBatchIndex = 1;
      }
      saveProgress(nextCatIndex, nextBatchIndex);

      console.log(`   ✅ تمت إضافة ${addedInBatch} وصفة جديدة. (إجمالي الملف: ${masterRecipes.length})`);

      // فترة استراحة 10 ثوانٍ بين كل طلب وآخر لاستعادة طاقة السيرفرات
      await sleep(10000);
    }
  }

  console.log(`\n🎉 اكتمل استخراج الـ 20,000 وصفة بنجاح! إجمالي الوصفات: ${masterRecipes.length}`);
  // مسح ملف التقدم بعد الانتهاء الكامل
  if (fs.existsSync(PROGRESS_FILE)) fs.unlinkSync(PROGRESS_FILE);
}

startSeedingProcess();
