# 🚀 دليل رفع المشروع على Vercel
**التاريخ:** 9 ديسمبر 2025

---

## 📋 جدول المحتويات

1. [تحديث GitHub Repository](#1-تحديث-github-repository)
2. [إعداد المشروع لـ Vercel](#2-إعداد-المشروع-لـ-vercel)
3. [رفع المشروع على Vercel](#3-رفع-المشروع-على-vercel)
4. [إعداد Environment Variables](#4-إعداد-environment-variables)
5. [مدة التجربة المجانية](#5-مدة-التجربة-المجانية)
6. [استكشاف الأخطاء](#6-استكشاف-الأخطاء)

---

## 1️⃣ تحديث GitHub Repository

### الخطوة 1: فتح Git Bash في مجلد المشروع

```bash
# انتقل إلى مجلد المشروع
cd /c/Users/pc/Desktop/instaanalysis
```

---

### الخطوة 2: التحقق من حالة Git

```bash
# عرض الملفات المعدلة
git status
```

**ستظهر لك:**
- ملفات معدلة (Modified) باللون الأحمر
- ملفات جديدة (Untracked) باللون الأحمر

---

### الخطوة 3: إضافة ملف .gitignore (مهم جداً!)

قبل رفع الملفات، تأكد من **عدم رفع البيئة الافتراضية** و **المتغيرات السرية**:

**أنشئ/عدل ملف `.gitignore`:**

```bash
# في Git Bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual Environment (مهم جداً!)
venv/
env/
ENV/
.venv/

# Environment Variables (سري!)
.env
.env.local
.env.production

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Database
*.db
*.sqlite
*.sqlite3

# Vercel
.vercel
EOF
```

---

### الخطوة 4: إضافة الملفات المعدلة

```bash
# إضافة جميع الملفات (ما عدا المستثناة في .gitignore)
git add .

# أو إضافة ملفات محددة فقط
git add main.py scraper.py scheduler.py dashboard.html
```

---

### الخطوة 5: إنشاء Commit

```bash
# إنشاء commit مع رسالة توضيحية
git commit -m "Update: Add Stories specialized scraper and Analytics page"
```

**أمثلة على رسائل commit جيدة:**
```bash
git commit -m "Fix: Stories Archive now uses specialized scraper"
git commit -m "Add: Client Analytics page with heatmap and charts"
git commit -m "Update: Separate Posts and Stories archives"
```

---

### الخطوة 6: رفع التحديثات إلى GitHub

```bash
# رفع التحديثات إلى الفرع الرئيسي (main)
git push origin main
```

**إذا واجهت خطأ (الفرع master بدلاً من main):**
```bash
git push origin master
```

**إذا طلب منك تسجيل الدخول:**
- سيفتح متصفح لتسجيل الدخول إلى GitHub
- أو استخدم GitHub Personal Access Token

---

### الخطوة 7: التحقق من الرفع

افتح GitHub Repository في المتصفح وتأكد من ظهور التحديثات:
```
https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
```

---

## 2️⃣ إعداد المشروع لـ Vercel

### ⚠️ ملاحظة مهمة عن البيئة الافتراضية (venv):

**Vercel لا يحتاج venv!**

عند الرفع على Vercel:
- ✅ Vercel يقرأ `requirements.txt` ويثبت المكتبات تلقائياً
- ✅ لا حاجة لرفع مجلد `venv/` (وهو مستبعد في `.gitignore`)
- ✅ Vercel ينشئ بيئة خاصة به على السيرفر

---

### الخطوة 1: إنشاء ملف `vercel.json`

هذا الملف يخبر Vercel كيفية تشغيل المشروع:

**أنشئ ملف `vercel.json` في جذر المشروع:**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  }
}
```

**شرح الملف:**
- `builds`: يحدد أن `main.py` هو نقطة البداية
- `routes`: يوجه جميع الطلبات إلى `main.py`
- `env`: يحدد إصدار Python (3.11)

---

### الخطوة 2: التأكد من ملف `requirements.txt`

تأكد من وجود جميع المكتبات المطلوبة:

```bash
# في Git Bash (إذا لم تكن قد أنشأته)
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
apify-client==1.6.4
supabase==2.0.3
python-dotenv==1.0.0
slowapi==0.1.9
httpx==0.25.1
bcrypt==4.1.1
EOF
```

**للتحقق من المكتبات المثبتة حالياً:**
```bash
# في Git Bash (داخل البيئة الافتراضية)
source venv/Scripts/activate
pip freeze > requirements.txt
deactivate
```

---

### الخطوة 3: تعديل `main.py` لـ Vercel

**في نهاية ملف `main.py`، تأكد من وجود:**

```python
# في نهاية main.py

# For Vercel deployment
app = app  # Export the FastAPI app instance

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**⚠️ ملاحظة:** Vercel لا يحتاج `uvicorn.run()` - سيتم تجاهله تلقائياً.

---

### الخطوة 4: إنشاء ملف `runtime.txt` (اختياري)

```bash
cat > runtime.txt << 'EOF'
python-3.11
EOF
```

---

### الخطوة 5: رفع التعديلات إلى GitHub

```bash
# إضافة الملفات الجديدة
git add vercel.json requirements.txt runtime.txt

# إنشاء commit
git commit -m "Add: Vercel configuration files"

# رفع إلى GitHub
git push origin main
```

---

## 3️⃣ رفع المشروع على Vercel

### الخطوة 1: إنشاء حساب Vercel

1. اذهب إلى: [https://vercel.com](https://vercel.com)
2. اضغط **"Sign Up"**
3. اختر **"Continue with GitHub"**
4. سجل الدخول بحساب GitHub الخاص بك
5. اسمح لـ Vercel بالوصول إلى repositories

---

### الخطوة 2: إنشاء مشروع جديد

1. اضغط **"Add New..."** → **"Project"**
2. ستظهر لك قائمة GitHub repositories
3. ابحث عن repository المشروع
4. اضغط **"Import"** بجانب اسم الـ repository

---

### الخطوة 3: إعدادات المشروع

**في صفحة Import Project:**

#### 1. **Project Name:**
```
instaanalysis
```
(أو أي اسم تريده)

#### 2. **Framework Preset:**
- اختر **"Other"** (لأنه FastAPI)

#### 3. **Root Directory:**
- اتركه فارغاً (./‎)

#### 4. **Build Command:**
- اتركه فارغاً (Vercel سيكتشف `vercel.json` تلقائياً)

#### 5. **Output Directory:**
- اتركه فارغاً

#### 6. **Install Command:**
```
pip install -r requirements.txt
```

---

### الخطوة 4: لا تضغط Deploy بعد!

**انتقل أولاً إلى إعداد Environment Variables** ⬇️

---

## 4️⃣ إعداد Environment Variables

### ⚠️ مهم جداً: متغيرات البيئة السرية

**قبل Deploy، أضف جميع المتغيرات من ملف `.env`:**

### الخطوة 1: فتح قسم Environment Variables

في صفحة Import Project:
1. اضغط على **"Environment Variables"** (قبل الضغط على Deploy)

---

### الخطوة 2: إضافة المتغيرات واحدة تلو الأخرى

**افتح ملف `.env` المحلي** ونسخ القيم:

#### 1. **APIFY_TOKEN:**
```
Name: APIFY_TOKEN
Value: [نسخ من .env]
Environment: Production, Preview, Development (✓ اختر الكل)
```

#### 2. **SUPABASE_URL:**
```
Name: SUPABASE_URL
Value: [نسخ من .env]
Environment: Production, Preview, Development
```

#### 3. **SUPABASE_ANON_KEY:**
```
Name: SUPABASE_ANON_KEY
Value: [نسخ من .env]
Environment: Production, Preview, Development
```

#### 4. **SUPABASE_SERVICE_KEY:**
```
Name: SUPABASE_SERVICE_KEY
Value: [نسخ من .env]
Environment: Production, Preview, Development
```

#### 5. **SECRET_KEY:**
```
Name: SECRET_KEY
Value: [نسخ من .env]
Environment: Production, Preview, Development
```

#### 6. **MAX_ACCOUNTS_BRONZE** (اختياري):
```
Name: MAX_ACCOUNTS_BRONZE
Value: 15
Environment: Production
```

#### 7. **MAX_ACCOUNTS_SILVER** (اختياري):
```
Name: MAX_ACCOUNTS_SILVER
Value: 50
Environment: Production
```

#### 8. **MAX_ACCOUNTS_GOLD** (اختياري):
```
Name: MAX_ACCOUNTS_GOLD
Value: 100
Environment: Production
```

---

### الخطوة 3: التحقق من المتغيرات

تأكد من إضافة **جميع المتغيرات** الموجودة في `.env`:
- ✅ APIFY_TOKEN
- ✅ SUPABASE_URL
- ✅ SUPABASE_ANON_KEY
- ✅ SUPABASE_SERVICE_KEY
- ✅ SECRET_KEY

---

### الخطوة 4: الضغط على Deploy

بعد إضافة جميع المتغيرات:
1. اضغط **"Deploy"**
2. انتظر 2-5 دقائق حتى يكتمل البناء

---

### الخطوة 5: التحقق من Deploy

**بعد اكتمال Deploy:**
1. ستحصل على رابط مثل:
   ```
   https://instaanalysis.vercel.app
   ```
2. اضغط على الرابط للتحقق من المشروع

---

## 5️⃣ مدة التجربة المجانية

### 📦 Vercel Free Plan (Hobby):

#### ✅ المزايا المجانية:

| الميزة | القيمة |
|-------|--------|
| **المدة** | **مجاني للأبد!** ✨ |
| **Deployments** | غير محدودة |
| **Bandwidth** | 100 GB/شهر |
| **Build Time** | 6,000 دقيقة/شهر |
| **Serverless Functions** | 100 GB-ساعة/شهر |
| **Max Function Duration** | 10 ثواني (هذا قد يكون مشكلة!) ⚠️ |
| **Custom Domains** | مجاني |
| **SSL Certificate** | مجاني (HTTPS تلقائي) |
| **Team Members** | 1 فقط |

#### ⚠️ القيود المهمة:

1. **مدة تنفيذ Function: 10 ثواني فقط!**
   - مشكلة: Apify scraping قد يستغرق 30-90 ثانية
   - **الحل:** استخدام Vercel Pro أو تقسيم العمليات

2. **عدد الطلبات (Requests):**
   - غير محدود، لكن مع Rate Limiting

3. **حجم الملفات:**
   - Max 50 MB لكل deployment

---

### 💎 Vercel Pro Plan (إذا احتجته):

| الميزة | القيمة |
|-------|--------|
| **السعر** | $20/شهر |
| **Max Function Duration** | **60 ثانية** (مناسب للـ Scraping) |
| **Bandwidth** | 1 TB/شهر |
| **Build Time** | غير محدود |

---

### 🎯 توصيتي:

#### للاختبار (1-3 أيام):
- ✅ استخدم **Free Plan**
- اختبر الواجهات والـ Dashboard
- ⚠️ قد تواجه مشكلة في Scraping (timeout بعد 10 ثواني)

#### للإنتاج:
- ✅ **Vercel Pro** ($20/شهر) - إذا أردت استضافة كاملة
- أو استخدم **Railway** / **Render** (بدائل أفضل لـ FastAPI)

---

## 6️⃣ استكشاف الأخطاء

### مشكلة 1: البناء فشل (Build Failed)

**الخطأ:**
```
Error: No module named 'fastapi'
```

**الحل:**
```bash
# تأكد من requirements.txt صحيح
cat requirements.txt

# أضف المكتبة المفقودة
echo "fastapi==0.104.1" >> requirements.txt

# رفع التحديث
git add requirements.txt
git commit -m "Fix: Add missing dependency"
git push origin main
```

---

### مشكلة 2: Environment Variables غير موجودة

**الخطأ:**
```
ValueError: APIFY_TOKEN not found in .env
```

**الحل:**
1. اذهب إلى Vercel Dashboard
2. اختر المشروع → **Settings** → **Environment Variables**
3. أضف المتغير المفقود
4. اضغط **"Redeploy"** من **Deployments** tab

---

### مشكلة 3: Timeout Error (10 seconds)

**الخطأ:**
```
Task timed out after 10.00 seconds
```

**السبب:**
- Apify scraping يستغرق أكثر من 10 ثواني
- Vercel Free Plan محدود بـ 10 ثواني

**الحلول:**

#### الحل 1: Upgrade إلى Pro Plan ($20/شهر)
```
Settings → Billing → Upgrade to Pro
```

#### الحل 2: استخدام Background Jobs (غير متاح في Vercel Free)

#### الحل 3: نقل Scraping لـ External Service:
- استخدم **Render** أو **Railway** لـ Backend
- Vercel فقط للـ Frontend

---

### مشكلة 4: Static Files لا تظهر

**الخطأ:**
```
404: /static/style.css not found
```

**الحل:**
```python
# في main.py، تأكد من:
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

**وتأكد من وجود مجلد `static/` في repository.**

---

### مشكلة 5: Database Connection Failed

**الخطأ:**
```
ConnectionError: Could not connect to Supabase
```

**الحل:**
1. تحقق من Environment Variables في Vercel
2. تأكد من صحة `SUPABASE_URL` و `SUPABASE_ANON_KEY`
3. تحقق من Supabase Dashboard أن المشروع نشط

---

## 🔄 تحديث المشروع بعد Deploy

### عند تعديل الكود:

```bash
# 1. تعديل الملفات المطلوبة
# 2. إضافة التعديلات
git add .

# 3. Commit
git commit -m "Update: Description of changes"

# 4. Push إلى GitHub
git push origin main
```

**✨ Vercel سيقوم تلقائياً بـ:**
- اكتشاف التحديث في GitHub
- بناء نسخة جديدة
- نشرها تلقائياً (Auto-Deploy)

**⏱️ الوقت:** 2-5 دقائق

---

## 📊 مراقبة المشروع

### في Vercel Dashboard:

1. **Deployments:** عرض جميع النسخ المنشورة
2. **Analytics:** إحصائيات الزوار (Pro فقط)
3. **Logs:** عرض Errors و Logs
4. **Settings:** تعديل Environment Variables

### لعرض Logs:

```
Vercel Dashboard → اختر المشروع → Deployments → اختر deployment → View Logs
```

---

## ✅ خلاصة الخطوات

### 1. تحديث GitHub:
```bash
cd /c/Users/pc/Desktop/instaanalysis
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### 2. إضافة ملفات Vercel:
- ✅ `vercel.json`
- ✅ `requirements.txt`
- ✅ `runtime.txt`
- ✅ `.gitignore` (استبعاد venv)

### 3. رفع على Vercel:
- ✅ Import من GitHub
- ✅ إضافة Environment Variables
- ✅ Deploy

### 4. التحقق:
- ✅ افتح الرابط `https://yourproject.vercel.app`
- ✅ اختبر Dashboard
- ✅ اختبر إضافة Client

---

## 🎁 نصائح إضافية

### 1. Custom Domain (مجاني):
```
Settings → Domains → Add Domain
```
يمكنك ربط نطاق خاص (مثل: `analytics.yoursite.com`)

### 2. Preview Deployments:
كل Branch جديد في GitHub سيحصل على preview URL تلقائياً

### 3. Rollback:
إذا واجهت مشكلة، يمكنك الرجوع لنسخة سابقة:
```
Deployments → اختر deployment قديم → ... → Promote to Production
```

---

## 🆘 إذا واجهت مشاكل

### خيارات بديلة لـ Vercel:

1. **Render.com** (أفضل لـ FastAPI):
   - Free Plan: 750 ساعة/شهر
   - No timeout limit!
   - مناسب للـ Background Jobs

2. **Railway.app**:
   - $5 مجاني عند التسجيل
   - No timeout limit
   - سهل جداً

3. **PythonAnywhere**:
   - Free Plan متاح
   - مناسب للمشاريع الصغيرة

---

## 📝 الملفات النهائية المطلوبة

تأكد من وجود هذه الملفات في repository:

```
instaanalysis/
├── main.py
├── scraper.py
├── scheduler.py
├── database.py
├── requirements.txt          ← مهم
├── vercel.json              ← مهم
├── runtime.txt              ← اختياري
├── .gitignore               ← مهم (استبعاد venv)
├── .env                     ← لا ترفعه! (محلي فقط)
├── dashboard.html
├── login.html
├── client.html
└── static/
    └── (CSS, JS files if any)
```

---

## 🎉 انتهى!

الآن لديك دليل شامل لرفع المشروع على Vercel.

**مدة التجربة:** مجاني للأبد! ✨

لكن قد تحتاج **Pro Plan ($20/شهر)** إذا واجهت مشكلة Timeout.

**بالتوفيق!** 🚀
