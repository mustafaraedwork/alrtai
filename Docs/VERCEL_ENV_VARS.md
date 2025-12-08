# 🔐 Environment Variables لـ Vercel

## ⚠️ مهم جداً: انسخ هذه القيم من ملف `.env` المحلي

---

## 📋 القائمة الكاملة للمتغيرات المطلوبة

### 1️⃣ Apify (لجلب بيانات Instagram)

```
Name: APIFY_TOKEN
Value: [انسخ من .env]
Environment: ✓ Production, ✓ Preview, ✓ Development
```

**كيف تحصل على القيمة:**
1. افتح ملف `.env` في المشروع المحلي
2. ابحث عن `APIFY_TOKEN=`
3. انسخ القيمة (بعد `=`)

---

### 2️⃣ Supabase URL (قاعدة البيانات)

```
Name: SUPABASE_URL
Value: [انسخ من .env]
Environment: ✓ Production, ✓ Preview, ✓ Development
```

**مثال على القيمة:**
```
https://abcdefghijk.supabase.co
```

---

### 3️⃣ Supabase Anon Key (مفتاح عام)

```
Name: SUPABASE_ANON_KEY
Value: [انسخ من .env]
Environment: ✓ Production, ✓ Preview, ✓ Development
```

**ملاحظة:** هذا مفتاح طويل جداً (مئات الأحرف)

---

### 4️⃣ Supabase Service Key (مفتاح سري)

```
Name: SUPABASE_SERVICE_KEY
Value: [انسخ من .env]
Environment: ✓ Production, ✓ Preview, ✓ Development
```

**⚠️ تحذير:** هذا مفتاح حساس جداً! لا تشاركه مع أحد.

---

### 5️⃣ Secret Key (لـ JWT Authentication)

```
Name: SECRET_KEY
Value: [انسخ من .env]
Environment: ✓ Production, ✓ Preview, ✓ Development
```

**إذا لم يكن لديك واحد، أنشئه:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 6️⃣ Max Accounts Limits (اختياري)

```
Name: MAX_ACCOUNTS_BRONZE
Value: 15
Environment: ✓ Production
```

```
Name: MAX_ACCOUNTS_SILVER
Value: 50
Environment: ✓ Production
```

```
Name: MAX_ACCOUNTS_GOLD
Value: 100
Environment: ✓ Production
```

---

## 📝 كيفية إضافتها في Vercel

### طريقة 1: عند أول Deploy

1. في صفحة **Import Project**
2. قبل الضغط على **Deploy**
3. اضغط على **Environment Variables**
4. أضف كل متغير على حدة:
   - اكتب **Name**
   - الصق **Value**
   - اختر **All Environments** (Production + Preview + Development)
   - اضغط **Add**
5. بعد إضافة الكل، اضغط **Deploy**

---

### طريقة 2: بعد Deploy

1. اذهب إلى **Vercel Dashboard**
2. اختر المشروع
3. اذهب إلى **Settings** → **Environment Variables**
4. اضغط **Add New**
5. أدخل **Name** و **Value**
6. اختر **Environments**
7. اضغط **Save**
8. اذهب إلى **Deployments** → **...** → **Redeploy**

---

## ✅ قائمة التحقق

قبل Deploy، تأكد من إضافة:

- [ ] `APIFY_TOKEN`
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_ANON_KEY`
- [ ] `SUPABASE_SERVICE_KEY`
- [ ] `SECRET_KEY`
- [ ] `MAX_ACCOUNTS_BRONZE` (اختياري)
- [ ] `MAX_ACCOUNTS_SILVER` (اختياري)
- [ ] `MAX_ACCOUNTS_GOLD` (اختياري)

---

## 🔍 كيفية التحقق من صحة المتغيرات

بعد Deploy، افتح **Deployment Logs** في Vercel:

### إذا رأيت:
```
✅ Application startup complete
```
**معناها:** جميع المتغيرات صحيحة! ✨

### إذا رأيت:
```
❌ ValueError: APIFY_TOKEN not found in .env
```
**معناها:** المتغير `APIFY_TOKEN` مفقود أو خاطئ.

**الحل:**
1. اذهب إلى **Settings** → **Environment Variables**
2. أضف/عدل المتغير المفقود
3. اضغط **Redeploy**

---

## 🚨 أخطاء شائعة

### 1. نسيت إضافة متغير:
```
Error: SUPABASE_URL not found
```
**الحل:** أضف المتغير في Settings

---

### 2. قيمة خاطئة:
```
Error: Could not connect to Supabase
```
**الحل:** تحقق من صحة `SUPABASE_URL` و `SUPABASE_ANON_KEY`

---

### 3. مسافات زائدة:
```
APIFY_TOKEN= abc123
```
**خطأ!** مسافة قبل القيمة

**صحيح:**
```
APIFY_TOKEN=abc123
```

---

## 💡 نصيحة

**احفظ نسخة من Environment Variables في مكان آمن:**

1. أنشئ ملف `env_backup.txt` (محلي فقط - لا ترفعه!)
2. الصق فيه جميع المتغيرات
3. احفظه في مكان آمن (خارج Git)

**مثال:**
```
APIFY_TOKEN=abc123def456
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJI...
SUPABASE_SERVICE_KEY=eyJhbGciOiJI...
SECRET_KEY=abc123def456
```

⚠️ **لا ترفع هذا الملف على GitHub أبداً!**

---

## ✅ تم!

الآن لديك قائمة كاملة بجميع المتغيرات المطلوبة.

**التالي:** ارجع لـ [VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md) لمتابعة الخطوات.
