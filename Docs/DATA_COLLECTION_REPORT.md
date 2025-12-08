# 📊 تقرير شامل: جميع البيانات المسحوبة من الحسابات المستهدفة
**التاريخ:** 9 ديسمبر 2025

---

## 🎯 نظرة عامة

يقوم النظام بسحب **5 أنواع رئيسية** من البيانات من حسابات Instagram المستهدفة:

1. ✅ **بيانات الملف الشخصي (Profile Data)**
2. ✅ **المنشورات المفصلة (Posts Detailed)**
3. ✅ **الستوريات النشطة (Active Stories)**
4. ✅ **إعلانات Facebook (Facebook Ads)**
5. ✅ **التحليلات المحسوبة (Calculated Analytics)**

---

## 📋 القسم 1: بيانات الملف الشخصي (Profile Data)

### 🔧 المصدر:
- **Apify Actor:** `apify/instagram-scraper`
- **Function:** `get_profile_data()` في `scraper.py`
- **Endpoint:** `resultsType: 'details'`

### 📊 البيانات المسحوبة:

#### 1. معلومات الحساب الأساسية:
```json
{
  "followers_count": 1234567,          // عدد المتابعين
  "profile_pic_url": "https://...",    // صورة البروفايل (HD)
  "username": "aram3sam"                // اسم المستخدم
}
```

#### 2. معلومات النشاط:
```json
{
  "last_post_date": "2024-12-08",      // تاريخ آخر منشور
  "days_inactive": 2,                   // عدد أيام عدم النشاط
  "avg_posting_interval": 3.5,          // متوسط الفترة بين المنشورات (بالأيام)
  "post_url": "https://instagram.com/p/..." // رابط آخر منشور
}
```

#### 3. حالة النشاط (Status Signal):
```json
{
  "status_signal": "RED"  // حالة النشاط
}
```

**قيم Status Signal:**
- 🔴 **RED:** نشط (آخر منشور قريب)
- 🟡 **YELLOW:** نشاط متوسط (تجاوز المتوسط بقليل)
- 🟢 **GREEN:** غير نشط (أكثر من 14 يوم بدون منشور)

**المعادلة:**
```python
threshold = max(avg_interval + 2, 5)
if days_inactive > threshold:
    signal = "YELLOW"
if days_inactive > 14:
    signal = "GREEN"
```

### 💾 التخزين في قاعدة البيانات:

**جدول:** `clients`

| العمود | النوع | الوصف |
|--------|------|-------|
| `username` | TEXT | اسم المستخدم |
| `followers_count` | INTEGER | عدد المتابعين |
| `last_post_date` | TEXT | تاريخ آخر منشور |
| `days_inactive` | INTEGER | أيام عدم النشاط |
| `avg_posting_interval` | INTEGER | متوسط الفترة بين المنشورات |
| `status_signal` | TEXT | حالة النشاط (RED/YELLOW/GREEN) |
| `post_url` | TEXT | رابط آخر منشور |
| `profile_pic_url` | TEXT | رابط صورة البروفايل |

### ⏱️ التحديث:
- عند إضافة client جديد
- عند Refresh يدوي من Dashboard
- تلقائياً كل فترة (حسب scheduler)

---

## 📋 القسم 2: المنشورات المفصلة (Posts Detailed)

### 🔧 المصدر:
- **Apify Actor:** `apify/instagram-scraper`
- **Function:** `fetch_instagram_posts_detailed()` في `scraper.py`
- **Endpoint:** `resultsType: 'posts'`
- **Limit:** 20 منشور (افتراضي)

### 📊 البيانات المسحوبة لكل منشور:

```json
{
  "instagram_post_id": "3214567890123456789",  // معرف المنشور الفريد
  "post_url": "https://instagram.com/p/ABC123", // رابط المنشور
  "thumbnail_url": "https://scontent.cdninstagram.com/...", // الصورة المصغرة
  "likes_count": 12345,                         // عدد الإعجابات
  "comments_count": 234,                        // عدد التعليقات
  "caption": "نص المنشور الكامل...",           // النص المرفق
  "hashtags": ["#fashion", "#style", "#ootd"],  // الهاشتاقات (أول 10)
  "posted_at": "2024-12-08T15:30:00+00:00"     // تاريخ النشر (ISO format)
}
```

### 🔍 تفاصيل الحقول:

#### 1. **instagram_post_id:**
- معرف فريد من Instagram
- يُستخدم لتجنب التكرار
- مثال: `"3214567890123456789"` أو `"ABC123"` (shortCode)

#### 2. **post_url:**
- رابط مباشر للمنشور
- صيغة: `https://instagram.com/p/{shortCode}`

#### 3. **thumbnail_url:**
- رابط الصورة المصغرة (CDN)
- يُستخدم في العرض في الواجهة
- يتم تحميله عبر `/proxy/image` لتجنب CORS

#### 4. **likes_count & comments_count:**
- أرقام دقيقة من Instagram API
- تُستخدم في حساب Engagement Rate

#### 5. **caption:**
- النص الكامل للمنشور
- قد يكون فارغاً
- يُستخرج منه الهاشتاقات

#### 6. **hashtags:**
- مستخرجة تلقائياً من caption
- محدودة بـ 10 هاشتاقات (الأوائل فقط)
- تُخزن كـ Array في PostgreSQL

#### 7. **posted_at:**
- ISO 8601 format
- مع timezone (UTC)
- يُستخدم في التجميع حسب التاريخ

### 💾 التخزين في قاعدة البيانات:

**جدول:** `posts`

```sql
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT,                    -- ربط بالـ client
    instagram_post_id TEXT UNIQUE,       -- معرف فريد
    post_url TEXT,
    thumbnail_url TEXT,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    caption TEXT,
    hashtags TEXT[],                     -- Array من الهاشتاقات
    posted_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 📈 استخدامات البيانات:

1. **Posts Archive:**
   - عرض جميع المنشورات مجمعة حسب التاريخ
   - Preview (أول 6 posts)
   - Modal مع pagination (50 post/page)

2. **Engagement Metrics:**
   - حساب Avg Likes per Post
   - حساب Avg Comments per Post
   - حساب Engagement Rate

3. **Activity Heatmap:**
   - عدد المنشورات في كل يوم
   - تلوين حسب الكثافة

4. **Engagement Trend Chart:**
   - رسم بياني لآخر 30 يوم
   - خط Likes + Comments + Engagement Rate

### ⏱️ التحديث:
- عند إضافة client جديد (20 منشور)
- تلقائياً كل فترة محددة
- يتم تجنب التكرار (duplicate check على `instagram_post_id`)

---

## 📋 القسم 3: الستوريات النشطة (Active Stories)

### 🔧 المصدر:
- **Apify Actor:** `datavoyantlab/instagram-story-downloader`
- **Function:** `fetch_instagram_stories()` في `scraper.py`
- **⚠️ خاص بـ Stories النشطة فقط** (آخر 24 ساعة)

### 📊 البيانات المسحوبة لكل ستوري:

```json
{
  "instagram_story_id": "3782635307116907165",  // معرف الستوري الفريد
  "thumbnail_url": "https://scontent.cdninstagram.com/...", // الصورة المصغرة
  "story_url": "https://instagram.fbeg1-1.fna.fbcdn.net/...", // رابط الملف الكامل (فيديو/صورة)
  "story_type": "video",                        // نوع الملف (image/video)
  "posted_at": "2024-12-08T12:34:48+00:00",    // تاريخ النشر
  "expires_at": "2024-12-09T12:34:48+00:00"    // تاريخ الانتهاء (بعد 24 ساعة)
}
```

### 🔍 تفاصيل الحقول:

#### 1. **instagram_story_id:**
- معرف فريد من Instagram
- مثال: `"3782635307116907165"`

#### 2. **thumbnail_url:**
- رابط الصورة المصغرة (CDN)
- يُستخدم في العرض في Stories Archive
- يُحمل عبر `/proxy/image`

#### 3. **story_url:**
- **جديد!** رابط مباشر للملف الكامل
- صورة أو فيديو
- يُفتح عند النقر على الستوري

#### 4. **story_type:**
- القيم: `"image"` أو `"video"`
- يُحدد نوع المحتوى

#### 5. **posted_at & expires_at:**
- **posted_at:** Unix timestamp محول لـ ISO format
- **expires_at:** posted_at + 24 ساعة
- Stories تنتهي تلقائياً بعد 24 ساعة

### 💾 التخزين في قاعدة البيانات:

**جدول:** `stories`

```sql
CREATE TABLE stories (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT,
    instagram_story_id TEXT NOT NULL,
    thumbnail_url TEXT,
    thumbnail_storage_path TEXT,         -- مسار في Supabase Storage (اختياري)
    story_type TEXT DEFAULT 'image',
    story_url TEXT,                      -- رابط الملف الكامل
    posted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, instagram_story_id)
);
```

### 📈 استخدامات البيانات:

1. **Stories Archive:**
   - عرض Stories النشطة (آخر 24 ساعة)
   - Preview (أول 6 stories)
   - Modal مع pagination

2. **Activity Calendar:**
   - عدد Stories في كل يوم
   - دمج مع Posts في Heatmap

3. **Inactivity Alerts:**
   - تنبيهات إذا لم يتم نشر stories لفترة طويلة

### ⚠️ ملاحظات مهمة:

1. **Stories تنتهي بعد 24 ساعة:**
   - لا يمكن جلب stories منتهية الصلاحية
   - النظام يجلب فقط Stories النشطة حالياً

2. **تحديث كل 20 ساعة:**
   - يضمن جلب Stories جديدة قبل انتهائها
   - يحفظ أرشيف للـ Stories (حتى بعد انتهائها على Instagram)

3. **حسابات Public فقط:**
   - Apify لا يدعم الحسابات الخاصة
   - يحتاج الحساب أن يكون عام

### ⏱️ التحديث:
- عند إضافة client جديد
- تلقائياً كل 20 ساعة (scheduler)
- يتم تجنب التكرار

---

## 📋 القسم 4: إعلانات Facebook (Facebook Ads)

### 🔧 المصدر:
- **Apify Actor:** `curious_coder/facebook-ads-library-scraper`
- **Function:** `check_facebook_ads()` في `scraper.py`
- **شرط:** يجب إدخال رابط صفحة Facebook

### 📊 البيانات المسحوبة:

```json
{
  "ads_count": 5,              // عدد الإعلانات النشطة
  "ads_status": "HAS_ADS",     // حالة الإعلانات
  "facebook_page_url": "https://www.facebook.com/page123"
}
```

### 🔍 تفاصيل الحقول:

#### 1. **ads_count:**
- عدد الإعلانات **النشطة حالياً** على Facebook
- يتم فلترة النتائج لاستبعاد "ADS_NOT_FOUND"

#### 2. **ads_status:**
القيم الممكنة:
- `"HAS_ADS"` - لديه إعلانات نشطة
- `"NO_ADS"` - لا توجد إعلانات
- `"UNKNOWN"` - لم يتم الفحص بعد
- `"ERROR"` - خطأ في الفحص

#### 3. **facebook_page_url:**
- رابط صفحة Facebook
- يُدخله المستخدم يدوياً
- اختياري (إذا لم يُدخل، لن يتم فحص الإعلانات)

### 💾 التخزين في قاعدة البيانات:

**جدول:** `clients`

| العمود | النوع | الوصف |
|--------|------|-------|
| `facebook_page_url` | TEXT | رابط صفحة Facebook |
| `ads_status` | TEXT | حالة الإعلانات |
| `ads_count` | INTEGER | عدد الإعلانات النشطة |

### 📈 استخدامات البيانات:

1. **Dashboard Display:**
   - عرض عدد الإعلانات في بطاقة Client
   - أيقونة خاصة للحسابات التي لديها إعلانات

2. **Lead Qualification:**
   - تحديد Leads النشطة (التي تدير إعلانات)
   - فلترة Clients حسب وجود إعلانات

### ⚠️ ملاحظات:

1. **اختياري:**
   - لا يتم فحص الإعلانات إلا إذا أدخل المستخدم رابط Facebook

2. **Facebook Ads Library:**
   - يسحب من مكتبة الإعلانات العامة
   - لا يحتاج إلى permissions خاصة

3. **Limit:**
   - يسحب أول 10 إعلانات فقط

### ⏱️ التحديث:
- عند إضافة client جديد (إذا تم إدخال رابط Facebook)
- عند Refresh يدوي
- يمكن تحديثه لاحقاً

---

## 📋 القسم 5: التحليلات المحسوبة (Calculated Analytics)

### 🔧 المصدر:
- **Calculation:** محسوبة من البيانات المسحوبة
- **Function:** تحليلات في `scheduler.py` و `main.py`

### 📊 التحليلات المحسوبة:

#### 1. **Engagement Rate (معدل التفاعل):**

**المعادلة:**
```python
engagement_rate = ((avg_likes + avg_comments) / followers_count) * 100
```

**مثال:**
```
Avg Likes: 12,345
Avg Comments: 234
Followers: 1,234,567

Engagement Rate = ((12,345 + 234) / 1,234,567) * 100 = 1.02%
```

**التخزين:**
- **جدول:** `analytics_snapshots`
- **العمود:** `engagement_rate` (DECIMAL 5,2)

---

#### 2. **Average Likes per Post (متوسط الإعجابات):**

**المعادلة:**
```python
avg_likes = SUM(likes_count) / COUNT(posts)
```

**التخزين:**
- **جدول:** `analytics_snapshots`
- **العمود:** `avg_likes` (DECIMAL 10,2)

---

#### 3. **Average Comments per Post (متوسط التعليقات):**

**المعادلة:**
```python
avg_comments = SUM(comments_count) / COUNT(posts)
```

**التخزين:**
- **جدول:** `analytics_snapshots`
- **العمود:** `avg_comments` (DECIMAL 10,2)

---

#### 4. **Posts per Day (معدل النشر):**

**المعادلة:**
```python
days_tracked = (NOW - tracking_started_at).days
posts_per_day = total_posts / days_tracked
```

**التخزين:**
- **جدول:** `analytics_snapshots`
- **العمود:** `posts_per_day` (DECIMAL 5,2)

---

#### 5. **Activity Calendar (تقويم النشاط):**

**البيانات لكل يوم:**
```json
{
  "activity_date": "2024-12-08",
  "posts_count": 3,        // عدد Posts في هذا اليوم
  "stories_count": 5,      // عدد Stories في هذا اليوم
  "has_activity": true     // هل يوجد نشاط؟
}
```

**التخزين:**
- **جدول:** `activity_calendar`

**الاستخدام:**
- Activity Heatmap (52 أسبوع)
- تلوين الأيام حسب عدد المنشورات

---

#### 6. **Engagement Trend (اتجاه التفاعل):**

**البيانات لآخر 30 يوم:**
```json
{
  "dates": ["Dec 1", "Dec 2", ..., "Dec 30"],
  "likes": [1200, 1350, ...],
  "comments": [45, 52, ...],
  "engagement_rate": [4.2, 4.5, ...]
}
```

**الحساب:**
- مجموع Likes لجميع Posts في كل يوم
- مجموع Comments لجميع Posts في كل يوم
- حساب Engagement Rate لكل يوم

**الاستخدام:**
- Engagement Trend Chart (خط بياني)

---

### 💾 جدول Analytics Snapshots:

```sql
CREATE TABLE analytics_snapshots (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    avg_likes DECIMAL(10,2) DEFAULT 0,
    avg_comments DECIMAL(10,2) DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    posts_per_day DECIMAL(5,2) DEFAULT 0,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, snapshot_date)
);
```

**الغرض:**
- حفظ لقطات يومية من التحليلات
- تتبع التغيرات مع الوقت
- عرض التوجهات (trends)

---

## 📊 ملخص شامل: جميع الحقول المسحوبة

### 🎯 البيانات من Instagram:

| الفئة | الحقل | المصدر | الاستخدام |
|------|------|--------|----------|
| **Profile** | `followers_count` | Apify Profile | Stat Card + Engagement Rate |
| **Profile** | `profile_pic_url` | Apify Profile | Header Display |
| **Profile** | `last_post_date` | محسوب من Posts | Dashboard Signal |
| **Profile** | `days_inactive` | محسوب | Dashboard Signal |
| **Profile** | `avg_posting_interval` | محسوب من Posts | Status Signal Logic |
| **Profile** | `status_signal` | محسوب | Dashboard Color (RED/YELLOW/GREEN) |
| **Posts** | `instagram_post_id` | Apify Posts | Unique Identifier |
| **Posts** | `post_url` | Apify Posts | Click to Instagram |
| **Posts** | `thumbnail_url` | Apify Posts | Display in Archive |
| **Posts** | `likes_count` | Apify Posts | Engagement Metrics |
| **Posts** | `comments_count` | Apify Posts | Engagement Metrics |
| **Posts** | `caption` | Apify Posts | Display (optional) |
| **Posts** | `hashtags` | مستخرج من Caption | Analysis (optional) |
| **Posts** | `posted_at` | Apify Posts | Date Grouping + Heatmap |
| **Stories** | `instagram_story_id` | Apify Stories | Unique Identifier |
| **Stories** | `thumbnail_url` | Apify Stories | Display in Archive |
| **Stories** | `story_url` | Apify Stories | Direct Link to Media |
| **Stories** | `story_type` | Apify Stories | image/video |
| **Stories** | `posted_at` | Apify Stories | Date Grouping |
| **Stories** | `expires_at` | محسوب (+24h) | Expiration Logic |

### 💰 البيانات من Facebook:

| الحقل | المصدر | الاستخدام |
|------|--------|----------|
| `facebook_page_url` | User Input | Link to Facebook |
| `ads_count` | Facebook Ads Library | Lead Qualification |
| `ads_status` | Facebook Ads Library | Dashboard Display |

### 📈 التحليلات المحسوبة:

| الحقل | المعادلة | الاستخدام |
|------|---------|----------|
| `engagement_rate` | (avg_likes + avg_comments) / followers * 100 | Stat Card |
| `avg_likes` | SUM(likes) / COUNT(posts) | Stat Card |
| `avg_comments` | SUM(comments) / COUNT(posts) | Stat Card |
| `posts_per_day` | total_posts / days_tracked | Stat Card |
| `activity_calendar` | COUNT posts/stories per day | Heatmap |
| `engagement_trend` | Daily aggregation | Chart |

---

## 🔄 جدول التحديث (Refresh Schedule)

| نوع البيانات | متى يتم السحب | التردد |
|-------------|--------------|--------|
| **Profile Data** | عند إضافة client + Refresh يدوي | حسب الطلب |
| **Posts** | عند إضافة client + تلقائي | مرة واحدة أو حسب scheduler |
| **Stories** | عند إضافة client + تلقائي | كل 20 ساعة |
| **Facebook Ads** | عند إضافة client + Refresh يدوي | حسب الطلب |
| **Analytics** | عند تغيير البيانات | يُحسب تلقائياً |

---

## 📁 الجداول في قاعدة البيانات

### الجداول الرئيسية:

1. **`users`** - مستخدمي النظام
2. **`clients`** - الحسابات المتتبعة
3. **`posts`** - أرشيف المنشورات
4. **`stories`** - أرشيف الستوريات
5. **`analytics_snapshots`** - لقطات التحليلات اليومية
6. **`activity_calendar`** - تقويم النشاط (Heatmap)
7. **`inactivity_alerts`** - تنبيهات عدم النشاط

### العلاقات:

```
users (1) ──── (N) clients
clients (1) ──── (N) posts
clients (1) ──── (N) stories
clients (1) ──── (N) analytics_snapshots
clients (1) ──── (N) activity_calendar
clients (1) ──── (N) inactivity_alerts
```

---

## 🎯 حالات الاستخدام

### 1. عند إضافة Client جديد:

**البيانات المسحوبة:**
1. ✅ Profile Data (followers, profile pic, last post)
2. ✅ Posts Detailed (20 post)
3. ✅ Stories Active (آخر 24 ساعة)
4. ✅ Facebook Ads (إذا تم إدخال رابط)
5. ✅ Analytics Calculated (engagement rate, avg likes, etc.)

**الوقت المتوقع:** 30-60 ثانية

---

### 2. عند فتح صفحة Analytics (📊):

**البيانات المعروضة:**
1. ✅ Profile Picture + Username
2. ✅ 6 Stat Cards (Followers, Engagement, Likes, Comments, Posts/Day, Total Posts)
3. ✅ Activity Heatmap (52 week)
4. ✅ Engagement Trend Chart (30 days)
5. ✅ Posts Archive (preview 6 + modal)
6. ✅ Stories Archive (preview 6 + modal)

**المصدر:**
- API calls لـ `/api/client/{id}`, `/api/client/{id}/posts`, `/api/client/{id}/stories`

---

### 3. التحديث التلقائي (Scheduler):

**كل 20 ساعة:**
1. ✅ جلب Stories جديدة لجميع Clients
2. ✅ تحديث Activity Calendar
3. ✅ التحقق من duplicate (تجنب إعادة حفظ نفس Story)

---

## ⚠️ القيود والملاحظات

### 1. Instagram Stories:
- ❌ لا يمكن جلب Stories منتهية (بعد 24 ساعة)
- ❌ حسابات Private لا تُجلب
- ✅ فقط Stories النشطة

### 2. Facebook Ads:
- ❌ يحتاج رابط صفحة Facebook (user input)
- ✅ يسحب من Ads Library العامة

### 3. Apify Rate Limits:
- Stories Scraper: 4 runs/minute
- Instagram Scraper: حسب خطة Apify

### 4. البيانات التاريخية:
- ✅ Posts: يتم حفظها للأبد
- ✅ Stories: يتم حفظها كأرشيف (حتى بعد انتهائها)
- ✅ Analytics: يتم حفظ snapshots يومية

---

## 📊 الخلاصة النهائية

### ما الذي نسحبه؟

1. **من Instagram Profile:**
   - عدد المتابعين
   - صورة البروفايل
   - تاريخ آخر منشور
   - نشاط الحساب

2. **من Instagram Posts:**
   - 20 منشور لكل client
   - صور مصغرة
   - عدد الإعجابات والتعليقات
   - النصوص والهاشتاقات
   - تواريخ النشر

3. **من Instagram Stories:**
   - Stories النشطة فقط (آخر 24 ساعة)
   - صور مصغرة
   - روابط الملفات الكاملة
   - نوع المحتوى (صورة/فيديو)
   - تواريخ النشر والانتهاء

4. **من Facebook Ads Library:**
   - عدد الإعلانات النشطة
   - حالة الإعلانات

5. **تحليلات محسوبة:**
   - معدل التفاعل
   - متوسط الإعجابات والتعليقات
   - معدل النشر
   - تقويم النشاط
   - اتجاهات التفاعل

---

## 🚀 الاستخدام المستقبلي

يمكن استخدام هذه البيانات في:

1. **تقارير مفصلة** (PDF Export)
2. **تنبيهات ذكية** (Inactivity Alerts)
3. **مقارنات بين Clients**
4. **توقعات مستقبلية** (Predictive Analytics)
5. **Lead Scoring** (تقييم جودة الـ Leads)

---

**تم إنشاء التقرير بنجاح!** ✅

هذا التقرير يوضح **جميع البيانات** التي يسحبها النظام من الحسابات المستهدفة.
