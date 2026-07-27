const fs = require('fs');
const path = require('path');
require('dotenv').config();
const Groq = require('groq-sdk');
const { GoogleGenerativeAI } = require('@google/generative-ai');

// 1. جلب مفتاح Groq ومفتاح Gemini الرابع فقط
const GROQ_KEY = process.env.GROQ_API_KEY;
const GEMINI_KEY = process.env.GEMINI_KEY_4;

if (!GROQ_KEY && !GEMINI_KEY) {
  console.error("❌ خطأ: لم يتم العثور على GROQ_API_KEY أو GEMINI_KEY_4 في ملف .env");
  process.exit(1);
}

const groq = GROQ_KEY ? new Groq({ apiKey: GROQ_KEY }) : null;
const genAI = GEMINI_KEY ? new GoogleGenerativeAI(GEMINI_KEY) : null;

// 2. الـ 50 لغة مقسمة إلى 5 مجموعات لتفادي التجاوز المسموح به للتوكنات
const LANGUAGE_GROUPS = [
  ["ar", "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"],
  ["ko", "tr", "hi", "bn", "pa", "jv", "vi", "th", "el", "nl"],
  ["sv", "no", "fi", "da", "pl", "cs", "hu", "ro", "uk", "he"],
  ["id", "ms", "fa", "ur", "sw", "am", "tl", "zu", "kn", "ta"],
  ["te", "mr", "gu", "ml", "si", "my", "km", "lo", "ne", "hy"]
];

const ALL_LANGUAGES = LANGUAGE_GROUPS.flat();
const outputDir = path.join(__dirname, 'chunk_recipes');
if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

const PROGRESS_FILE = './translation_progress.json';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let groqExhausted = false;

// 3. دالة استدعاء الذكاء الاصطناعي بنظام الأولوية والتناوب (Groq ثم Gemini Key 4)
async function fetchWithGroqFirstThenGemini(prompt) {
  // --- المرحلة الأولى: Groq ---
  if (groq && !groqExhausted) {
    try {
      const completion = await groq.chat.completions.create({
        messages: [{ role: "user", content: prompt }],
        model: "llama-3.3-70b-versatile",
        temperature: 0.5,
        max_tokens: 8000
      });
      return completion.choices[0]?.message?.content;
    } catch (err70) {
      console.warn("⚠️ Groq (Llama 3.3) تعثر، التجربة على Groq (Llama 3.1)...");
      try {
        const completion = await groq.chat.completions.create({
          messages: [{ role: "user", content: prompt }],
          model: "llama-3.1-8b-instant",
          temperature: 0.5,
          max_tokens: 8000
        });
        return completion.choices[0]?.message?.content;
      } catch (err8) {
        console.warn("🔴 تم استهلاك حصة Groq بالكامل! التحويل الفوري والدائم إلى Gemini Key 4...");
        groqExhausted = true;
      }
    }
  }

  // --- المرحلة الثانية: Gemini (المفتاح الرابع فقط) ---
  if (genAI) {
    try {
      const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
      const result = await model.generateContent(prompt);
      return result.response.text();
    } catch (errG2) {
      console.warn("⚠️ Gemini 2.0 Flash لم ينفذ الطلب، تجربة Gemini 1.5 Flash...");
      try {
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
        const result = await model.generateContent(prompt);
        return result.response.text();
      } catch (errG1) {
        console.error("❌ فشل استخراج الترجمة من Gemini أيضاً.");
      }
    }
  }

  return null;
}

// 4. تنظيف واستخراج الـ JSON
function parseJsonFromText(rawText) {
  if (!rawText) return null;
  try {
    const cleanJson = rawText.replace(/```json|```/g, '').trim();
    return JSON.parse(cleanJson);
  } catch (err) {
    console.error("⚠️ خطأ في قراءة بنية JSON المرجعة.");
    return null;
  }
}

async function translateBatchForLanguages(recipesBatch, langGroup) {
  const prompt = `Act as a Professional Culinary Translator & SEO Expert.
Translate and complete details for the provided ${recipesBatch.length} recipes into these language codes: ${langGroup.join(', ')}.

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

RETURN ONLY A VALID JSON OBJECT where top-level keys are the language codes (${langGroup.join(', ')}), each containing an array of the processed recipe objects. No markdown formatting, no prose.`;

  const rawText = await fetchWithGroqFirstThenGemini(prompt);
  return parseJsonFromText(rawText);
}

// 5. إدارة حفظ واستعادة التقدم عند التوقف (Checkpoint System)
function loadProgress() {
  if (fs.existsSync(PROGRESS_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8'));
    } catch (e) {
      return { batchIndex: 0, chunkIndexCounters: {}, langBuffers: {} };
    }
  }
  return { batchIndex: 0, chunkIndexCounters: {}, langBuffers: {} };
}

function saveProgress(state) {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(state, null, 2), 'utf8');
}

// 6. تشغيل النظام الرئيسي
async function startMasterTranslation() {
  const masterFile = './master_20k_recipes.json';
  if (!fs.existsSync(masterFile)) {
    console.error("❌ لم يتم العثور على ملف الوصفات الرئيسي master_20k_recipes.json");
    process.exit(1);
  }

  const masterData = JSON.parse(fs.readFileSync(masterFile, 'utf8'));
  console.log(`🚀 بدء ترجمة ومعالجة ${masterData.length} وصفة إلى 50 لغة...`);

  const RECIPES_PER_SUB_BATCH = 20;
  const totalSubBatches = Math.ceil(masterData.length / RECIPES_PER_SUB_BATCH);

  let { batchIndex, chunkIndexCounters, langBuffers } = loadProgress();

  ALL_LANGUAGES.forEach(lang => {
    if (!langBuffers[lang]) langBuffers[lang] = [];
    if (!chunkIndexCounters[lang]) chunkIndexCounters[lang] = 1;
  });

  console.log(`📍 استئناف الترجمة من الدفعة الفرعية [${batchIndex + 1}/${totalSubBatches}]`);

  for (let b = batchIndex; b < totalSubBatches; b++) {
    const batchStart = b * RECIPES_PER_SUB_BATCH;
    const batch = masterData.slice(batchStart, batchStart + RECIPES_PER_SUB_BATCH);

    console.log(`\n🔄 معالجة الدفعة الفرعية ${b + 1}/${totalSubBatches} (الوصفات ${batchStart + 1} - ${batchStart + batch.length})...`);

    for (let group of LANGUAGE_GROUPS) {
      const groupResult = await translateBatchForLanguages(batch, group);

      if (groupResult) {
        for (let lang of group) {
          if (groupResult[lang] && Array.isArray(groupResult[lang])) {
            langBuffers[lang].push(...groupResult[lang]);
          }
        }
      } else {
        console.error(`⚠️ تعذر جلب ترجمة المجموعة [${group.join(', ')}]. سيتم التوقف وحفظ موقع العمل.`);
        saveProgress({ batchIndex: b, chunkIndexCounters, langBuffers });
        console.log(`💾 تم حفظ موضع التوقف عند الدفعة ${b + 1}. أعد تشغيل السكريبت للاستكمال لاحقاً.`);
        process.exit(0);
      }

      await sleep(2000);
    }

    // حفظ أجزاء الـ 100 وصفة لكل لغة داخل مجلد chunk_recipes
    ALL_LANGUAGES.forEach(lang => {
      if (langBuffers[lang].length >= 100 || (b === totalSubBatches - 1 && langBuffers[lang].length > 0)) {
        const chunkData = langBuffers[lang].splice(0, 100);
        const chunkNum = chunkIndexCounters[lang]++;
        const fileName = `chunk_${lang}_${chunkNum}.json`;

        fs.writeFileSync(path.join(outputDir, fileName), JSON.stringify(chunkData, null, 2), 'utf8');
        console.log(`   💾 تم إنشاء الملف: chunk_recipes/${fileName}`);
      }
    });

    saveProgress({ batchIndex: b + 1, chunkIndexCounters, langBuffers });
  }

  console.log("\n🎉 تم إنهاء الترجمة وإنشاء جميع الملفات بنجاح داخل مجلد chunk_recipes!");
  if (fs.existsSync(PROGRESS_FILE)) fs.unlinkSync(PROGRESS_FILE);
}

startMasterTranslation();
