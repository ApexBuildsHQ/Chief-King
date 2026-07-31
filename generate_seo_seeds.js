const fs = require('fs');
require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');
const Groq = require('groq-sdk');

const GEMINI_KEY = process.env.GEMINI_KEY_4; // الأولوية الأولى
const GROQ_KEY = process.env.GROQ_API_KEY;  // الاحتياطي

if (!GEMINI_KEY && !GROQ_KEY) {
  console.error("❌ خطأ: لم يتم العثور على أي مفاتيح API في متغيرات البيئة!");
  process.exit(1);
}

const genAI = GEMINI_KEY ? new GoogleGenerativeAI(GEMINI_KEY) : null;
const groq = GROQ_KEY ? new Groq({ apiKey: GROQ_KEY }) : null;

const categories = [
  "Fast Food & Burgers", "Pizzas & Pies", "Pasta & Noodles", "Chicken & Poultry",
  "Meat & Steak", "Seafood & Fish", "Rice & Grain Dishes", "Cakes & Pastries",
  "Cookies & Biscuits", "Cold Desserts & Ice Cream", "Breakfast & Pancakes",
  "Soups & Broths", "Salads & Appetizers", "Smoothies & Drinks", "Keto & Low Carb",
  "Vegan & Vegetarian", "Fried Foods & Snacks", "Sauces & Dips", "Casseroles & Stews", "Viral Trending Recipes"
];

const BATCH_SIZE = 100;
const DELAY_MS = 2 * 60 * 1000; // دقيقتان كاملتان بين كل طلب
const OUTPUT_FILE = './master_20k_recipes.json';
const PROGRESS_FILE = './seeding_progress.json';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchGeminiFirstThenGroq(prompt) {
  // 1. الأولوية لـ Gemini API
  if (genAI) {
    try {
      const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
      const result = await model.generateContent(prompt);
      return result.response.text();
    } catch (e) {
      console.warn("⚠️ Gemini 2.0 تعثر، المحاولة مع Gemini 1.5...");
      try {
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
        const result = await model.generateContent(prompt);
        return result.response.text();
      } catch (errG) {
        console.warn("🔴 تعذر استجابة Gemini! التحويل المؤقت إلى Groq...");
      }
    }
  }

  // 2. خط الدفاع الثاني: Groq
  if (groq) {
    try {
      const completion = await groq.chat.completions.create({
        messages: [{ role: "user", content: prompt }],
        model: "llama-3.3-70b-versatile",
        temperature: 0.5,
        max_tokens: 4000
      });
      return completion.choices[0]?.message?.content;
    } catch (e) {
      console.error("❌ فشلت محاولات Groq أيضاً.");
    }
  }

  return null;
}

function parseJson(rawText) {
  if (!rawText) return [];
  try {
    const cleanJson = rawText.replace(/```json|```/g, '').trim();
    return JSON.parse(cleanJson);
  } catch (e) {
    console.error("⚠️ خطأ في تنسيق JSON العائد.");
    return [];
  }
}

async function startEngine() {
  console.log("🚀 بدء محرك استخراج الـ 20,000 وصفة المعتمد على Gemini SEO...");

  let masterRecipes = [];
  let idCounter = 1;

  if (fs.existsSync(OUTPUT_FILE)) {
    try {
      masterRecipes = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'));
      idCounter = masterRecipes.length + 1;
    } catch (e) {}
  }

  let { catIndex, batchIndex } = fs.existsSync(PROGRESS_FILE) 
    ? JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8')) 
    : { catIndex: 0, batchIndex: 1 };

  for (let i = catIndex; i < categories.length; i++) {
    const cat = categories[i];
    const startBatch = (i === catIndex) ? batchIndex : 1;

    for (let batch = startBatch; batch <= 10; batch++) { // 10 دفعات × 100 وصفة = 1000 وصفة لكل قسم
      console.log(`\n📌 القسم [${i + 1}/20]: ${cat} | الدفعة [${batch}/10] (${BATCH_SIZE} وصفة)...`);

      const prompt = `Act as a Global SEO Food Expert.
Generate a JSON array of exactly ${BATCH_SIZE} unique recipes in category "${cat}".
Compare each title with top global Google search trends (billions of searches).
Return ONLY a JSON array of objects with keys: "title", "seo_title", "description", "prepTime", "cookTime".
Example: [{"title": "Burger", "seo_title": "Best Homemade Cheeseburger Recipe", "description": "...", "prepTime": "15m", "cookTime": "15m"}]`;

      const rawText = await fetchGeminiFirstThenGroq(prompt);
      const items = parseJson(rawText);

      if (!items || items.length === 0) {
        console.error("❌ تعذر جلب الدفعة، يتم حفظ التقدم والتوقف مؤقتاً.");
        fs.writeFileSync(PROGRESS_FILE, JSON.stringify({ catIndex: i, batchIndex: batch }));
        process.exit(0);
      }

      items.forEach(item => {
        masterRecipes.push({
          id: idCounter++,
          title: item.seo_title || item.title,
          category: cat,
          description: item.description,
          prepTime: item.prepTime,
          cookTime: item.cookTime
        });
      });

      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(masterRecipes, null, 2));
      
      let nextCat = (batch === 10) ? i + 1 : i;
      let nextBatch = (batch === 10) ? 1 : batch + 1;
      fs.writeFileSync(PROGRESS_FILE, JSON.stringify({ catIndex: nextCat, batchIndex: nextBatch }));

      console.log(`✅ تمت معالجة وحفظ ${items.length} وصفة. (الإجمالي: ${masterRecipes.length})`);

      if (masterRecipes.length < 20000) {
        console.log(`⏳ استراحة دقيقتين كاملتين (120 ثانية) للحفاظ على جودة الردود واستقرار السيرفر...`);
        await sleep(DELAY_MS);
      }
    }
  }

  console.log("🎉 اكتمل استخراج وتدقيق 20,000 وصفة بنجاح!");
  if (fs.existsSync(PROGRESS_FILE)) fs.unlinkSync(PROGRESS_FILE);
}

startEngine();

