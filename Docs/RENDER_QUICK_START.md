# ⚡ Render - خطوات سريعة

## ✅ تم إصلاح المشكلة!

المشكلة كانت: **تعارض في إصدارات httpx**
- `apify-client` يحتاج `httpx>=0.25.1`
- `supabase` القديم يحتاج `httpx<0.25.0`

**الحل:** تحديث `requirements.txt` ✅

---

## 🚀 الخطوات (3 خطوات فقط!)

### الخطوة 1️⃣: رفع التحديثات على GitHub

افتح Git Bash:
```bash
cd /c/Users/pc/Desktop/instaanalysis
git add requirements.txt
git commit -m "Fix: Update dependencies for Render"
git push origin main
```

---

### الخطوة 2️⃣: إنشاء Web Service في Render

1. اذهب إلى: [https://render.com](https://render.com)
2. **Sign Up** → Continue with GitHub
3. **New +** → **Web Service**
4. اختر repository: `instaanalysis`
5. املأ الإعدادات:

**Name:** `instaanalysis`

**Runtime:** `Python 3`

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Instance Type:** `Free`

---

### الخطوة 3️⃣: إضافة Environment Variables

اضغط **Advanced** ثم أضف:

```
APIFY_TOKEN = [من .env]
SUPABASE_URL = [من .env]
SUPABASE_ANON_KEY = [من .env]
SUPABASE_SERVICE_KEY = [من .env]
SECRET_KEY = [من .env]
```

---

### ثم اضغط: **Create Web Service** 🎉

---

## ⏱️ الانتظار (5-7 دقائق)

سترى Logs:
```
==> Installing dependencies...
Successfully installed fastapi-0.104.1 ...
==> Starting service...
INFO: Uvicorn running on http://0.0.0.0:10000
==> Your service is live! 🎉
```

---

## ✅ تم! افتح URL:

```
https://instaanalysis.onrender.com
```

---

## 🎯 المزايا:

- ✅ **No Timeout** - Scraping يعمل بدون مشاكل!
- ✅ مجاني (750 ساعة/شهر)
- ✅ Auto-Deploy من GitHub
- ✅ Background Jobs مدعوم

---

## 📖 للتفاصيل الكاملة:

اقرأ: [RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md)
