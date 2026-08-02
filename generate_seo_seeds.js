const fs = require('fs');
require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');
const Groq = require('groq-sdk');

const GEMINI_KEY = process.env.GEMINI_KEY_4;
const GROQ_KEY = process.env.GROQ_API_KEY;

if (!GEMINI_KEY && !GROQ_KEY) {
  console.error("❌ خطأ: لم يتم العثور على أي مفاتيح API في متغيرات البيئة!");
  process.exit(1);
}

const genAI = GEMINI_KEY ? new GoogleGenerativeAI(GEMINI_KEY) : null;
const groq = GROQ_KEY ? new Groq({ apiKey: GROQ_KEY }) : null;

const RAW_FILE = './raw_recipes.json';
const OUTPUT_FILE = './master_20k_recipes.json';
const PROGRESS_FILE = './seeding_progress.json';

const BATCH_SIZE = 50;
const DELAY_MS = 3 * 1000; // 3 ثوانٍ فقط بين الدفعات

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchSeoTitlesFromAI(batchItems) {
  const titlesList = batchItems.map((item, idx) => `${idx + 1}. "${item.title}"`).join('\n');
  
  const prompt = `You are a Global SEO Food Expert.
Analyze these ${batchItems.length} recipe titles.
Compare each title against high-volume global search trend queries (billions of daily searches).
If the title already matches a top search query, keep it.
If a slightly different title has much higher monthly search volume, update it to the top search volume title.

Return ONLY a JSON array of objects with keys "id" and "seo_title":
[{"id": 1, "seo_title": "Best Authentic Homemade Cheeseburger"}]

Titles:
${titlesList}`;

  if (genAI) {
    try {
      const model = genAI.getGenerativeModel({ 
        model: "gemini-2.0-flash",
        generationConfig: { responseMimeType: "application/json" }
      });
      const result = await model.generateContent(prompt);
      const parsed = JSON.parse(result.response.text());
      return Array.isArray(parsed) ? parsed : (parsed.recipes || Object.values(parsed)[0] || []);
    } catch (e) {
      console.warn("⚠️ تعثر Gemini، التحويل إلى Groq...");
    }
  }

  if (groq) {
    try {
      const completion = await groq.chat.completions.create({
        messages: [{ role: "user", content: prompt }],
        model: "llama-3.3-70b-versatile",
        temperature: 0.3,
        max_tokens: 4000,
        response_format: { type: "json_object" }
      });
      const parsed = JSON.parse(completion.choices[0]?.message?.content);
      return Array.isArray(parsed) ? parsed : (parsed.recipes || Object.values(parsed)[0] || []);
    } catch (e) {
      console.error("❌ فشلت محاولات Groq أيضاً.");
    }
  }

  return [];
}

async function startEngine() {
  console.log("🚀 بدء محرك مطابقة السيو وتحسين العناوين لـ Chief King...");

  if (!fs.existsSync(RAW_FILE)) {
    console.error(`❌ الملف الخام ${RAW_FILE} غير موجود!`);
    process.exit(1);
  }

  const rawRecipes = JSON.parse(fs.readFileSync(RAW_FILE, 'utf8'));
  let masterRecipes = [];

  if (fs.existsSync(OUTPUT_FILE)) {
    try {
      masterRecipes = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'));
    } catch (e) {}
  }

  let { startIndex } = fs.existsSync(PROGRESS_FILE) 
    ? JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8')) 
    : { startIndex: 0 };

  for (let i = startIndex; i < rawRecipes.length; i += BATCH_SIZE) {
    const batch = rawRecipes.slice(i, i + BATCH_SIZE);
    console.log(`\n📌 معالجة الدفعة من [${i + 1}] إلى [${i + batch.length}] من إجمالي ${rawRecipes.length}...`);

    const seoResults = await fetchSeoTitlesFromAI(batch);

    batch.forEach((item, idx) => {
      const seoMatch = seoResults.find(r => r.id === idx + 1);
      const finalTitle = (seoMatch && seoMatch.seo_title) ? seoMatch.seo_title : item.title;

      masterRecipes.push({
        id: i + idx + 1,
        title: finalTitle,
        original_title: item.title,
        category: item.category || "General",
        description: item.description || "",
        prepTime: item.prepTime || "15m",
        cookTime: item.cookTime || "20m",
        ingredients: item.ingredients || [],
        instructions: item.instructions || [],
        rating: item.rating || 5.0
      });
    });

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(masterRecipes, null, 2));
    fs.writeFileSync(PROGRESS_FILE, JSON.stringify({ startIndex: i + BATCH_SIZE }));

    console.log(`✅ تم حفظ الدفعة بنجاح. (الإجمالي: ${masterRecipes.length})`);

    if (i + BATCH_SIZE < rawRecipes.length) {
      await sleep(DELAY_MS);
    }
  }

  console.log("🎉 اكتمل تدقيق ومطابقة السيو لجميع الوصفات بنجاح!");
  if (fs.existsSync(PROGRESS_FILE)) fs.unlinkSync(PROGRESS_FILE);
}

startEngine();
