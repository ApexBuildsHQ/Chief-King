const fs = require('fs');
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const API_KEYS = [
  process.env.GEMINI_KEY_1,
  process.env.GEMINI_KEY_2,
  process.env.GEMINI_KEY_3,
  process.env.GEMINI_KEY_4
].filter(Boolean);

if (API_KEYS.length === 0) {
  console.error("❌ خطأ: لم يتم توفير مفاتيح API في بيئة العمل.");
  process.exit(1);
}

// 50 لغة عالمية مقسمة إلى 5 مجموعات لتفادي التجاوز المسموح به للتوكنات
const LANGUAGE_GROUPS = [
  ["ar", "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"],
  ["ko", "tr", "hi", "bn", "pa", "jv", "vi", "th", "el", "nl"],
  ["sv", "no", "fi", "da", "pl", "cs", "hu", "ro", "uk", "he"],
  ["id", "ms", "fa", "ur", "sw", "am", "tl", "zu", "kn", "ta"],
  ["te", "mr", "gu", "ml", "si", "my", "km", "lo", "ne", "hy"]
];

const ALL_LANGUAGES = LANGUAGE_GROUPS.flat();

let currentKeyIndex = 0;
function getNextKey() {
  const key = API_KEYS[currentKeyIndex];
  currentKeyIndex = (currentKeyIndex + 1) % API_KEYS.length;
  return key;
}

const outputDir = path.join(__dirname, 'chunk_recipes');
if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

async function translateBatchForLanguages(recipesBatch, langGroup) {
  const apiKey = getNextKey();
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

  const prompt = `Act as a Professional Culinary Translator & SEO Expert.
Translate and complete details for the provided 20 recipes into these language codes: ${langGroup.join(', ')}.

For each recipe, provide:
- id
- title (translated)
- description (short SEO meta description)
- prepTime (e.g. "15 mins")
- cookTime (e.g. "30 mins")
- ingredients (array of strings)
- instructions (array of step strings)
- nutrition (calories, protein, carbs, fat)

INPUT RECIPES:
${JSON.stringify(recipesBatch.map(r => ({ id: r.id, title: r.title, slug: r.slug })))}

RETURN ONLY A VALID JSON OBJECT where top-level keys are the language codes (${langGroup.join(', ')}), each containing an array of the 20 processed recipe objects. No markdown formatting.`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text().trim();
    const cleanJson = text.replace(/```json|```/g, '').trim();
    return JSON.parse(cleanJson);
  } catch (err) {
    console.error(`⚠️ خطأ في معالجة مجموعة اللغات [${langGroup.slice(0,3).join(',')}...]:`, err.message);
    return null;
  }
}

async function startMasterTranslation() {
  const masterData = JSON.parse(fs.readFileSync('./master_20k_recipes.json', 'utf8'));
  console.log(`🚀 بدء ترجمة ومعالجة ${masterData.length} وصفة إلى 50 لغة...`);

  const RECIPES_PER_SUB_BATCH = 20; 
  const langBuffers = {};
  ALL_LANGUAGES.forEach(lang => { langBuffers[lang] = []; });

  let chunkIndexCounters = {};
  ALL_LANGUAGES.forEach(lang => { chunkIndexCounters[lang] = 1; });

  const totalSubBatches = Math.ceil(masterData.length / RECIPES_PER_SUB_BATCH);

  for (let b = 0; b < totalSubBatches; b++) {
    const batchStart = b * RECIPES_PER_SUB_BATCH;
    const batch = masterData.slice(batchStart, batchStart + RECIPES_PER_SUB_BATCH);

    console.log(`\n🔄 معالجة الدفعة الفرعية ${b + 1}/${totalSubBatches} (الوصفات ${batchStart + 1} - ${batchStart + batch.length})...`);

    // إرسال الطلبات لكل مجموعة لغوية
    for (let group of LANGUAGE_GROUPS) {
      const groupResult = await translateBatchForLanguages(batch, group);
      
      if (groupResult) {
        for (let lang of group) {
          if (groupResult[lang] && Array.isArray(groupResult[lang])) {
            langBuffers[lang].push(...groupResult[lang]);
          }
        }
      }
      await new Promise(r => setTimeout(r, 1200)); // حماية الـ RPM
    }

    // حفظ الملفات كلما تجمعت 100 وصفة في التخزين المؤقت لكل لغة
    ALL_LANGUAGES.forEach(lang => {
      if (langBuffers[lang].length >= 100 || (b === totalSubBatches - 1 && langBuffers[lang].length > 0)) {
        const chunkData = langBuffers[lang].splice(0, 100);
        const chunkNum = chunkIndexCounters[lang]++;
        const fileName = `chunk_${lang}_${chunkNum}.json`;
        
        fs.writeFileSync(path.join(outputDir, fileName), JSON.stringify(chunkData, null, 2), 'utf8');
        console.log(`   💾 تم إنشاء: chunk_recipes/${fileName}`);
      }
    });
  }

  console.log("\n🎉 تم إنهاء إنشاء الـ 10,000 ملف بنجاح وتجهيز المجلد chunk_recipes للرفع!");
}

startMasterTranslation();
