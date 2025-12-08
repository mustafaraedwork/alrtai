# 📋 TASK LIST - Client Analytics & Stories Archive Feature
## مشروع Alrt AI - ميزة تحليلات العميل وأرشيف الستوريات

**تاريخ الإنشاء:** 8 ديسمبر 2025
**الحالة:** جاهز للتنفيذ

---

## 🎯 نظرة عامة

إضافة ميزة شاملة لتتبع وتحليل نشاط حسابات Instagram المتابعة، تشمل:
- صفحة تفاصيل منفصلة لكل عميل
- تحليلات متقدمة (Engagement, معدل النشر، إلخ)
- Heatmap calendar مثل GitHub لعرض النشاط اليومي
- أرشيف الستوريات مع thumbnails
- نظام تنبيهات عند توقف النشاط

---

## 📁 المرحلة 1: قاعدة البيانات (Database Schema)

### Task 1.1: إنشاء جدول posts
- [✅] إنشاء جدول `posts` في Supabase
```sql
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    instagram_post_id TEXT UNIQUE NOT NULL,
    post_url TEXT,
    thumbnail_url TEXT,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    caption TEXT,
    hashtags TEXT[],
    posted_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- [✅] إضافة Index على `client_id` و `posted_at`
- [✅] إضافة Index على `instagram_post_id` للتحقق من التكرار

### Task 1.2: إنشاء جدول stories
- [✅] إنشاء جدول `stories` في Supabase
```sql
CREATE TABLE stories (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    instagram_story_id TEXT NOT NULL,
    thumbnail_url TEXT,
    thumbnail_storage_path TEXT,
    story_type TEXT DEFAULT 'image',
    posted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, instagram_story_id)
);
```
- [✅] إضافة Index على `client_id` و `posted_at`
- [ ] إضافة Index للتحقق من التكرار

### Task 1.3: إنشاء جدول analytics_snapshots
- [✅] إنشاء جدول `analytics_snapshots`
```sql
CREATE TABLE analytics_snapshots (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
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
- [ ] إضافة Index على `client_id` و `snapshot_date`

### Task 1.4: إنشاء جدول activity_calendar
- [✅] إنشاء جدول `activity_calendar` للـ Heatmap
```sql
CREATE TABLE activity_calendar (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    activity_date DATE NOT NULL,
    stories_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    has_activity BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, activity_date)
);
```
- [ ] إضافة Index على `client_id` و `activity_date`

### Task 1.5: إنشاء جدول inactivity_alerts
- [✅] إنشاء جدول `inactivity_alerts`
```sql
CREATE TABLE inactivity_alerts (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    alert_type TEXT DEFAULT 'STORIES_INACTIVE',
    days_inactive INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Task 1.6: تحديث جدول clients
- [✅] إضافة أعمدة جديدة لجدول `clients`
```sql
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tracking_started_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_story_date TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS stories_inactive_days INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_stories_archived INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_posts_tracked INTEGER DEFAULT 0;
```

---

## 📁 المرحلة 2: Supabase Storage

### Task 2.1: إنشاء Bucket للـ Thumbnails
- [ ] إنشاء bucket باسم `story-thumbnails`
- [ ] تعيين الصلاحيات (public read, authenticated write)
- [ ] تحديد الحد الأقصى لحجم الملف (500KB)

### Task 2.2: إنشاء Storage Policies
- [ ] Policy للقراءة العامة
- [ ] Policy للكتابة (authenticated users only)
- [ ] Policy للحذف (owner only)

---

## 📁 المرحلة 3: Backend - Scrapers

### Task 3.1: تحديث scraper.py - إضافة Stories Scraper
- [ ] إنشاء function `fetch_instagram_stories(username)`
- [ ] استخدام Apify Actor المناسب للستوريات
- [ ] معالجة الـ response واستخراج:
  - story_id
  - thumbnail_url
  - story_type (image/video)
  - posted_at
  - expires_at
- [ ] تحميل الـ thumbnail وحفظه في Supabase Storage
- [ ] إرجاع قائمة الستوريات الجديدة فقط (تجنب التكرار)

### Task 3.2: تحديث scraper.py - إضافة Posts Scraper
- [ ] إنشاء function `fetch_instagram_posts(username, limit=20)`
- [ ] جلب آخر 20 منشور
- [ ] استخراج:
  - post_id
  - post_url
  - thumbnail_url
  - likes_count
  - comments_count
  - caption
  - hashtags
  - posted_at
- [ ] إرجاع قائمة البوستات

### Task 3.3: إنشاء analytics_calculator.py
- [ ] إنشاء function `calculate_analytics(posts_data, followers_count)`
- [ ] حساب:
  - avg_likes
  - avg_comments
  - engagement_rate = (avg_likes + avg_comments) / followers * 100
  - posts_per_day
- [ ] إرجاع dictionary بالنتائج

---

## 📁 المرحلة 4: Backend - Scheduler

### Task 4.1: تحديث scheduler.py - Stories Queue
- [ ] إنشاء `stories_queue` جديد
- [ ] إضافة 3 workers للستوريات
- [ ] تشغيل كل 20 ساعة
- [ ] معالجة الأخطاء وإعادة المحاولة

### Task 4.2: إنشاء Stories Worker
- [ ] إنشاء function `process_stories_job(client_id)`
- [ ] جلب الستوريات من Instagram
- [ ] التحقق من التكرار (story_id موجود؟)
- [ ] حفظ الجديد فقط في قاعدة البيانات
- [ ] تحديث `activity_calendar`
- [ ] تحديث `last_story_date` في clients

### Task 4.3: إنشاء Analytics Worker
- [ ] إنشاء function `process_analytics_job(client_id)`
- [ ] جلب آخر 20 بوست
- [ ] حساب الـ Analytics
- [ ] حفظ snapshot يومي
- [ ] تحديث `activity_calendar`

### Task 4.4: إنشاء Inactivity Checker
- [ ] إنشاء function `check_inactivity_alerts()`
- [ ] فحص جميع العملاء
- [ ] إذا `stories_inactive_days >= 3`:
  - إنشاء alert جديد
  - تحديث `status_signal` إلى GREEN (فرصة)
- [ ] تشغيل مرة واحدة يومياً

---

## 📁 المرحلة 5: Backend - API Endpoints

### Task 5.1: إنشاء Client Details Endpoint
- [ ] `GET /api/client/{client_id}`
- [ ] إرجاع:
  - معلومات العميل الأساسية
  - آخر analytics snapshot
  - إجمالي الستوريات والبوستات
  - تاريخ بدء التتبع

### Task 5.2: إنشاء Heatmap Data Endpoint
- [ ] `GET /api/client/{client_id}/heatmap`
- [ ] Parameters: `year` (optional, default: current year)
- [ ] إرجاع:
  - قائمة بـ 365 يوم
  - كل يوم: `{date, stories_count, posts_count, level}`
  - level: 0 (no activity) to 4 (high activity)

### Task 5.3: إنشاء Day Activity Endpoint
- [ ] `GET /api/client/{client_id}/activity/{date}`
- [ ] إرجاع:
  - قائمة الستوريات لهذا اليوم (مع thumbnails)
  - قائمة البوستات لهذا اليوم (مع thumbnails)

### Task 5.4: إنشاء Analytics History Endpoint
- [ ] `GET /api/client/{client_id}/analytics`
- [ ] Parameters: `days` (default: 30)
- [ ] إرجاع:
  - قائمة snapshots للفترة المطلوبة
  - للاستخدام في Charts

### Task 5.5: إنشاء Stories Archive Endpoint
- [ ] `GET /api/client/{client_id}/stories`
- [ ] Parameters: `page`, `limit` (default: 20)
- [ ] إرجاع:
  - قائمة الستوريات مع pagination
  - thumbnails URLs

### Task 5.6: إنشاء Alerts Endpoint
- [ ] `GET /api/alerts`
- [ ] إرجاع التنبيهات غير المقروءة للمستخدم
- [ ] `PUT /api/alerts/{alert_id}/read`
- [ ] تحديث حالة القراءة

---

## 📁 المرحلة 6: Frontend - Client Page

### Task 6.1: إنشاء client.html
- [ ] إنشاء صفحة `/client/{id}`
- [ ] تحميل بيانات العميل عند الفتح
- [ ] التحقق من الـ authentication

### Task 6.2: Header Section
- [ ] صورة العميل (كبيرة، دائرية)
- [ ] اسم المستخدم + رابط Instagram
- [ ] Custom Label (badge)
- [ ] Lead Status (dropdown قابل للتعديل)
- [ ] تاريخ بدء التتبع
- [ ] زر الرجوع للـ Dashboard

### Task 6.3: Stats Cards Row
- [ ] إنشاء 6 بطاقات:
  1. Followers (رقم)
  2. Posts per Day (رقم)
  3. Avg Likes (رقم)
  4. Avg Comments (رقم)
  5. Engagement Rate (نسبة مئوية)
  6. Stories Archived (رقم)
- [ ] تصميم متجاوب (3 في صف على desktop، 2 على tablet، 1 على mobile)

### Task 6.4: Heatmap Calendar Component
- [ ] إنشاء grid مثل GitHub (52 أسبوع × 7 أيام)
- [ ] عرض أسماء الأشهر في الأعلى
- [ ] عرض أيام الأسبوع على اليسار (Mon, Wed, Fri)
- [ ] تلوين المربعات حسب مستوى النشاط:
  - Level 0: `#1e293b` (رمادي غامق - لا نشاط)
  - Level 1: `#064e3b` (أخضر خفيف)
  - Level 2: `#059669` (أخضر متوسط)
  - Level 3: `#10b981` (أخضر)
  - Level 4: `#34d399` (أخضر فاتح - نشاط عالي)
- [ ] المربعات قبل `tracking_started_at` تكون `#0f172a` (أغمق - غير متاح)
- [ ] Tooltip عند hover يعرض: التاريخ + عدد الستوريات + عدد البوستات
- [ ] Click يفتح popup التفاصيل

### Task 6.5: Day Activity Popup
- [ ] Modal يظهر عند الضغط على يوم
- [ ] Header: التاريخ الكامل
- [ ] قسم Stories:
  - عرض thumbnails في grid (4 في صف)
  - عدد الستوريات
  - إذا لا يوجد: "No stories this day"
- [ ] قسم Posts:
  - عرض thumbnails مع likes/comments
  - إذا لا يوجد: "No posts this day"
- [ ] زر إغلاق + إغلاق بالضغط خارج الـ Modal + ESC

### Task 6.6: Charts Section (ApexCharts)
- [ ] تثبيت/تضمين ApexCharts
- [ ] Chart 1: Engagement Trend (Line Chart)
  - المحور X: التواريخ (آخر 30 يوم)
  - المحور Y: Engagement Rate
  - لون أخضر متدرج
- [ ] Chart 2: Likes & Comments (Bar Chart)
  - مقارنة Likes vs Comments
  - آخر 30 يوم
- [ ] Chart 3: Activity Overview (Area Chart)
  - Stories count + Posts count
  - آخر 30 يوم
- [ ] جعل الـ Charts متجاوبة
- [ ] Dark theme متوافق مع التصميم

### Task 6.7: Stories Archive Section
- [ ] Grid عرض الـ thumbnails (6 في صف)
- [ ] Infinite scroll أو pagination
- [ ] عرض التاريخ تحت كل thumbnail
- [ ] Badge للنوع (image/video)

### Task 6.8: Notes & CRM Section
- [ ] عرض الملاحظات الحالية
- [ ] زر تعديل يفتح modal
- [ ] حفظ التعديلات

---

## 📁 المرحلة 7: Frontend - Dashboard Updates

### Task 7.1: تحديث Dashboard Table
- [ ] إزالة popup التفاصيل القديم
- [ ] جعل الصف كامل clickable
- [ ] عند الضغط: توجيه إلى `/client/{id}`
- [ ] إضافة عمود "Stories" يعرض عدد الستوريات المؤرشفة

### Task 7.2: إضافة Alerts Badge
- [ ] أيقونة الجرس في الـ Header
- [ ] Badge بعدد التنبيهات غير المقروءة
- [ ] Dropdown يعرض آخر 5 تنبيهات
- [ ] رابط "View All" للتنبيهات

### Task 7.3: تحديث Stats Cards
- [ ] إضافة بطاقة "Inactive (3+ days)"
- [ ] عدد العملاء المتوقفين عن الستوريات

---

## 📁 المرحلة 8: Styling & UX

### Task 8.1: تصميم صفحة العميل
- [ ] نفس الـ color scheme الحالي
- [ ] Dark theme
- [ ] خلفية: `#0f172a`
- [ ] Cards: `#1e293b`
- [ ] Borders: `#334155`
- [ ] Text: `#f1f5f9`
- [ ] Accent: `#3b82f6` (أزرق)

### Task 8.2: Responsive Design
- [ ] Desktop: كل الأقسام ظاهرة
- [ ] Tablet: Charts تحت بعض
- [ ] Mobile: كل شيء single column

### Task 8.3: Loading States
- [ ] Skeleton loaders للـ Cards
- [ ] Spinner للـ Heatmap
- [ ] Shimmer effect للـ thumbnails

### Task 8.4: Error States
- [ ] رسالة خطأ واضحة إذا فشل التحميل
- [ ] زر "Retry"
- [ ] رسالة "No data yet" للعملاء الجدد

---

## 📁 المرحلة 9: Testing & Optimization

### Task 9.1: اختبار قاعدة البيانات
- [ ] اختبار إنشاء الجداول
- [ ] اختبار العلاقات (Foreign Keys)
- [ ] اختبار الـ Indexes

### Task 9.2: اختبار الـ Scrapers
- [ ] اختبار جلب الستوريات
- [ ] اختبار جلب البوستات
- [ ] اختبار حفظ الـ thumbnails
- [ ] اختبار التعامل مع الأخطاء

### Task 9.3: اختبار الـ API
- [ ] اختبار كل endpoint
- [ ] اختبار الـ authentication
- [ ] اختبار الـ pagination

### Task 9.4: اختبار الـ Frontend
- [ ] اختبار تحميل الصفحة
- [ ] اختبار الـ Heatmap
- [ ] اختبار الـ Popup
- [ ] اختبار الـ Charts
- [ ] اختبار على أحجام شاشات مختلفة

### Task 9.5: تحسين الأداء
- [ ] Lazy loading للصور
- [ ] Caching للـ API responses
- [ ] تقليل حجم الـ thumbnails
- [ ] تحسين الـ database queries

---

## 📁 المرحلة 10: Deployment

### Task 10.1: تحديث Requirements
- [ ] إضافة أي مكتبات جديدة إلى `requirements.txt`

### Task 10.2: Environment Variables
- [ ] إضافة أي متغيرات جديدة للـ `.env`

### Task 10.3: Database Migration
- [ ] تشغيل SQL scripts على Supabase Production

### Task 10.4: اختبار نهائي
- [ ] اختبار شامل في بيئة Production
- [ ] التأكد من عمل الـ Scheduler
- [ ] التأكد من عمل الـ Storage

---

## ✅ Acceptance Criteria

### يجب أن يكون المستخدم قادراً على:
1. ✅ الضغط على أي عميل في الـ Dashboard والانتقال لصفحة تفاصيله
2. ✅ رؤية إحصائيات العميل (متابعين، engagement، إلخ)
3. ✅ رؤية Heatmap calendar لآخر سنة
4. ✅ الضغط على أي يوم ورؤية الستوريات والبوستات
5. ✅ رؤية Charts تفاعلية للـ trends
6. ✅ تصفح أرشيف الستوريات
7. ✅ تلقي تنبيهات عند توقف عميل عن النشر لـ 3 أيام

### المتطلبات التقنية:
1. ✅ الستوريات تُفحص كل 20 ساعة
2. ✅ الـ Thumbnails تُحفظ في Supabase Storage
3. ✅ لا يوجد تكرار في الستوريات (unique story_id)
4. ✅ الصفحة تعمل على جميع الأجهزة (responsive)
5. ✅ الـ API محمي بـ authentication

---

## 📊 تقدير الوقت

| المرحلة | الوقت المتوقع |
|---------|--------------|
| Database Schema | 1-2 ساعة |
| Storage Setup | 30 دقيقة |
| Scrapers | 3-4 ساعات |
| Scheduler | 2-3 ساعات |
| API Endpoints | 3-4 ساعات |
| Frontend Page | 6-8 ساعات |
| Dashboard Updates | 2-3 ساعات |
| Styling | 2-3 ساعات |
| Testing | 2-3 ساعات |
| **الإجمالي** | **22-31 ساعة** |

---

## 🚨 ملاحظات مهمة

1. **Apify Actor للستوريات**: تأكد من استخدام Actor يدعم جلب الستوريات
2. **Rate Limiting**: حافظ على تأخير 2-3 ثواني بين الطلبات
3. **Storage Cleanup**: فكر في حذف الـ thumbnails القديمة (أكثر من سنة)
4. **Error Handling**: معالجة حالة الحساب الخاص أو المحذوف
5. **Timezone**: استخدم UTC في جميع التواريخ

---

**آخر تحديث:** 8 ديسمبر 2025