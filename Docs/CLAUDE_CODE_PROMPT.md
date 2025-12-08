# 🤖 Claude Code Prompt - Client Analytics & Stories Archive Feature
## مشروع Alrt AI Enterprise

---

## 📋 السياق

أنت تعمل على مشروع **Alrt AI** - منصة لمراقبة وتحليل نشاط حسابات Instagram. المشروع مبني بـ:
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Frontend**: HTML + Tailwind CSS + Vanilla JavaScript
- **Scraping**: Apify API
- **Scheduler**: APScheduler

المشروع يعمل حالياً ويتتبع حسابات Instagram ويعرضها في Dashboard. الآن نريد إضافة ميزة جديدة شاملة.

---

## 🎯 المطلوب تنفيذه

### الميزة الجديدة: Client Analytics & Stories Archive

إنشاء نظام متكامل يشمل:

### 1. صفحة تفاصيل العميل (Client Details Page)
صفحة منفصلة تفتح عند الضغط على أي عميل في الـ Dashboard بدلاً من الـ popup الحالي.

**المسار:** `/client/{client_id}`

**المحتوى:**
- معلومات العميل الأساسية (صورة، اسم، متابعين، وسم، حالة)
- 6 بطاقات إحصائيات: Followers, Posts/Day, Avg Likes, Avg Comments, Engagement Rate, Stories Archived
- Heatmap Calendar (مثل GitHub contributions) يعرض نشاط آخر سنة
- Charts تفاعلية باستخدام ApexCharts
- أرشيف الستوريات (thumbnails)
- قسم الملاحظات

### 2. Heatmap Calendar
- Grid يعرض 52 أسبوع × 7 أيام
- تلوين حسب مستوى النشاط (0-4)
- الأيام قبل `tracking_started_at` تكون بلون مختلف (غير متاح)
- عند الضغط على يوم: popup يعرض الستوريات والبوستات لهذا اليوم
- Tooltip عند hover يعرض التاريخ وعدد النشاط

### 3. نظام أرشيف الستوريات
- فحص كل 20 ساعة لجلب الستوريات الجديدة
- حفظ thumbnail فقط (ليس الفيديو/الصورة الكاملة)
- تخزين الـ thumbnails في Supabase Storage
- تجنب التكرار (كل story_id يُحفظ مرة واحدة)
- عرض الستوريات في popup اليوم + قسم أرشيف منفصل

### 4. نظام التنبيهات
- فحص يومي للعملاء المتوقفين عن نشر ستوريات
- إذا توقف عميل لمدة 3 أيام أو أكثر: إنشاء تنبيه
- عرض التنبيهات في الـ Dashboard (أيقونة جرس + badge)

### 5. تحليلات متقدمة
- حساب: معدل النشر، متوسط اللايكات، التعليقات، Engagement Rate
- حفظ snapshot يومي للإحصائيات
- عرض في Charts: Engagement Trend, Likes vs Comments, Activity Overview

---

## 🗄️ قاعدة البيانات - الجداول الجديدة

### جدول posts
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

CREATE INDEX idx_posts_client_id ON posts(client_id);
CREATE INDEX idx_posts_posted_at ON posts(posted_at);
CREATE INDEX idx_posts_instagram_id ON posts(instagram_post_id);
```

### جدول stories
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

CREATE INDEX idx_stories_client_id ON stories(client_id);
CREATE INDEX idx_stories_posted_at ON stories(posted_at);
```

### جدول analytics_snapshots
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

CREATE INDEX idx_analytics_client_date ON analytics_snapshots(client_id, snapshot_date);
```

### جدول activity_calendar
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

CREATE INDEX idx_activity_client_date ON activity_calendar(client_id, activity_date);
```

### جدول inactivity_alerts
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

CREATE INDEX idx_alerts_user ON inactivity_alerts(user_id, is_read);
```

### تحديث جدول clients
```sql
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tracking_started_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_story_date TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS stories_inactive_days INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_stories_archived INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_posts_tracked INTEGER DEFAULT 0;
```

---

## 🔌 API Endpoints الجديدة

### 1. GET /api/client/{client_id}
إرجاع تفاصيل العميل الكاملة مع آخر analytics snapshot.

**Response:**
```json
{
    "client": {
        "id": 1,
        "username": "example",
        "profile_pic_url": "...",
        "custom_label": "Restaurant",
        "lead_status": "NEW_LEAD",
        "tracking_started_at": "2024-01-15T00:00:00Z",
        "followers_count": 9474,
        "total_stories_archived": 156,
        "total_posts_tracked": 45
    },
    "analytics": {
        "avg_likes": 380,
        "avg_comments": 8.7,
        "engagement_rate": 4.11,
        "posts_per_day": 0.3
    }
}
```

### 2. GET /api/client/{client_id}/heatmap?year=2025
إرجاع بيانات الـ Heatmap لسنة محددة.

**Response:**
```json
{
    "tracking_started_at": "2024-06-15",
    "data": [
        {"date": "2025-01-01", "stories": 0, "posts": 0, "level": 0},
        {"date": "2025-01-02", "stories": 5, "posts": 1, "level": 2},
        ...
    ]
}
```

**Level Calculation:**
- 0: no activity
- 1: 1-2 stories OR 1 post
- 2: 3-5 stories OR 2 posts
- 3: 6-9 stories OR 3+ posts
- 4: 10+ stories

### 3. GET /api/client/{client_id}/activity/{date}
إرجاع الستوريات والبوستات ليوم محدد.

**Response:**
```json
{
    "date": "2025-06-15",
    "stories": [
        {
            "id": 1,
            "thumbnail_url": "...",
            "story_type": "image",
            "posted_at": "2025-06-15T10:30:00Z"
        }
    ],
    "posts": [
        {
            "id": 1,
            "thumbnail_url": "...",
            "likes_count": 380,
            "comments_count": 12,
            "posted_at": "2025-06-15T14:00:00Z"
        }
    ]
}
```

### 4. GET /api/client/{client_id}/analytics?days=30
إرجاع تاريخ الـ Analytics للـ Charts.

**Response:**
```json
{
    "snapshots": [
        {
            "date": "2025-06-01",
            "engagement_rate": 4.11,
            "avg_likes": 380,
            "avg_comments": 8.7,
            "followers_count": 9400
        },
        ...
    ]
}
```

### 5. GET /api/client/{client_id}/stories?page=1&limit=20
إرجاع أرشيف الستوريات مع pagination.

**Response:**
```json
{
    "stories": [...],
    "total": 156,
    "page": 1,
    "pages": 8
}
```

### 6. GET /api/alerts
إرجاع التنبيهات غير المقروءة.

### 7. PUT /api/alerts/{alert_id}/read
تحديد التنبيه كمقروء.

---

## 🎨 Frontend - صفحة العميل (client.html)

### التصميم
- نفس الـ Dark theme الحالي
- خلفية: `#0f172a`
- Cards: `#1e293b`
- Borders: `#334155`
- Text: `#f1f5f9`
- Accent: `#3b82f6`

### الهيكل
```html
<!-- Header -->
<header>
    <!-- زر الرجوع -->
    <!-- صورة العميل + اسم + وسم -->
    <!-- Lead Status dropdown -->
</header>

<!-- Stats Cards (6 بطاقات) -->
<div class="grid grid-cols-6">
    <!-- Followers, Posts/Day, Avg Likes, Avg Comments, Engagement Rate, Stories -->
</div>

<!-- Heatmap Section -->
<section>
    <h2>Activity Heatmap</h2>
    <div id="heatmap-container">
        <!-- GitHub-style grid -->
    </div>
    <div class="legend">
        <!-- Less ... More -->
    </div>
</section>

<!-- Charts Section -->
<section class="grid grid-cols-2">
    <div id="engagement-chart"></div>
    <div id="likes-comments-chart"></div>
</section>

<!-- Stories Archive -->
<section>
    <h2>Stories Archive</h2>
    <div class="grid grid-cols-6">
        <!-- Thumbnails -->
    </div>
</section>

<!-- Notes Section -->
<section>
    <!-- ملاحظات + زر تعديل -->
</section>
```

### Heatmap Implementation
```javascript
// الألوان حسب المستوى
const colors = {
    unavailable: '#0f172a',  // قبل tracking_started_at
    level0: '#1e293b',       // لا نشاط
    level1: '#064e3b',       // نشاط قليل
    level2: '#059669',       // نشاط متوسط
    level3: '#10b981',       // نشاط جيد
    level4: '#34d399'        // نشاط عالي
};

// إنشاء الـ grid
function createHeatmap(data, trackingStartDate) {
    // 52 أسبوع × 7 أيام
    // tooltip on hover
    // click to open popup
}
```

### Day Popup
```html
<div id="day-popup" class="modal">
    <div class="modal-content">
        <h3>📅 {date}</h3>
        
        <div class="stories-section">
            <h4>📸 Stories ({count})</h4>
            <div class="grid grid-cols-4">
                <!-- thumbnails -->
            </div>
        </div>
        
        <div class="posts-section">
            <h4>📱 Posts ({count})</h4>
            <div class="grid">
                <!-- thumbnails with likes/comments -->
            </div>
        </div>
    </div>
</div>
```

### ApexCharts Setup
```javascript
// Engagement Trend Chart
const engagementChart = new ApexCharts(document.querySelector("#engagement-chart"), {
    chart: { type: 'line', height: 300, background: 'transparent' },
    theme: { mode: 'dark' },
    colors: ['#10b981'],
    series: [{ name: 'Engagement Rate', data: [...] }],
    xaxis: { categories: [...dates] }
});

// Likes vs Comments Chart
const likesChart = new ApexCharts(document.querySelector("#likes-chart"), {
    chart: { type: 'bar', height: 300 },
    colors: ['#3b82f6', '#f59e0b'],
    series: [
        { name: 'Likes', data: [...] },
        { name: 'Comments', data: [...] }
    ]
});
```

---

## ⚙️ Backend - Scraper Updates

### إضافة إلى scraper.py

```python
async def fetch_instagram_stories(username: str) -> list:
    """
    جلب ستوريات حساب Instagram باستخدام Apify
    Returns: قائمة الستوريات مع thumbnails
    """
    # استخدم Apify Instagram Story Scraper
    # أرجع: story_id, thumbnail_url, story_type, posted_at
    pass

async def fetch_instagram_posts_detailed(username: str, limit: int = 20) -> list:
    """
    جلب آخر منشورات مع تفاصيل كاملة
    Returns: قائمة المنشورات مع likes, comments, caption, hashtags
    """
    pass

async def download_and_store_thumbnail(url: str, client_id: int, story_id: str) -> str:
    """
    تحميل thumbnail وحفظه في Supabase Storage
    Returns: storage path
    """
    pass

def calculate_engagement_rate(likes: float, comments: float, followers: int) -> float:
    """
    حساب Engagement Rate
    Formula: (avg_likes + avg_comments) / followers * 100
    """
    if followers == 0:
        return 0
    return round((likes + comments) / followers * 100, 2)
```

---

## ⏰ Scheduler Updates

### إضافة إلى scheduler.py

```python
# Stories Queue
stories_queue = asyncio.Queue(maxsize=1000)

# Workers للستوريات
async def stories_worker(worker_id: int):
    """Worker لمعالجة جلب الستوريات"""
    while True:
        job = await stories_queue.get()
        try:
            await process_stories_job(job)
        except Exception as e:
            logging.error(f"Stories worker {worker_id} error: {e}")
        finally:
            stories_queue.task_done()
        await asyncio.sleep(3)  # تأخير بين الطلبات

async def process_stories_job(client_id: int):
    """معالجة جلب ستوريات عميل"""
    # 1. جلب الستوريات من Instagram
    # 2. التحقق من التكرار (story_id)
    # 3. تحميل وحفظ thumbnails الجديدة
    # 4. حفظ في قاعدة البيانات
    # 5. تحديث activity_calendar
    # 6. تحديث last_story_date في clients
    pass

# Inactivity Checker (يعمل مرة يومياً)
async def check_inactivity():
    """فحص العملاء المتوقفين عن النشر"""
    # 1. جلب جميع العملاء
    # 2. حساب stories_inactive_days لكل عميل
    # 3. إذا >= 3 أيام: إنشاء alert
    # 4. تحديث status_signal إلى GREEN (فرصة)
    pass

# جدولة المهام
scheduler.add_job(refresh_stories, 'interval', hours=20)
scheduler.add_job(check_inactivity, 'cron', hour=6)  # كل يوم الساعة 6 صباحاً
```

---

## 📁 هيكل الملفات

```
project/
├── main.py                 # إضافة API endpoints الجديدة
├── scraper.py              # إضافة stories & posts scrapers
├── scheduler.py            # إضافة stories workers & inactivity checker
├── database.py             # لا تغيير
├── templates/
│   ├── dashboard.html      # تحديث: إزالة popup, إضافة alerts
│   ├── client.html         # جديد: صفحة تفاصيل العميل
│   └── login.html          # لا تغيير
├── static/
│   └── js/
│       ├── heatmap.js      # جديد: Heatmap component
│       └── charts.js       # جديد: ApexCharts setup
└── requirements.txt        # لا تغيير (ApexCharts من CDN)
```

---

## 🔧 Supabase Storage Setup

### إنشاء Bucket
```sql
-- في Supabase Dashboard > Storage
-- إنشاء bucket: story-thumbnails
-- Settings: Public bucket = true
```

### Storage Policies
```sql
-- السماح بالقراءة للجميع
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'story-thumbnails');

-- السماح بالكتابة للمستخدمين المسجلين
CREATE POLICY "Authenticated upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'story-thumbnails');
```

---

## ✅ قائمة التحقق للتنفيذ

### المرحلة 1: Database
- [ ] إنشاء جدول posts
- [ ] إنشاء جدول stories
- [ ] إنشاء جدول analytics_snapshots
- [ ] إنشاء جدول activity_calendar
- [ ] إنشاء جدول inactivity_alerts
- [ ] تحديث جدول clients
- [ ] إنشاء Indexes
- [ ] إعداد Supabase Storage bucket

### المرحلة 2: Backend
- [ ] إضافة fetch_instagram_stories إلى scraper.py
- [ ] إضافة fetch_instagram_posts_detailed إلى scraper.py
- [ ] إضافة download_and_store_thumbnail إلى scraper.py
- [ ] إضافة stories_queue و workers إلى scheduler.py
- [ ] إضافة check_inactivity إلى scheduler.py
- [ ] إضافة جميع API endpoints إلى main.py

### المرحلة 3: Frontend
- [ ] إنشاء client.html
- [ ] تنفيذ Header section
- [ ] تنفيذ Stats cards
- [ ] تنفيذ Heatmap calendar
- [ ] تنفيذ Day popup
- [ ] تنفيذ ApexCharts
- [ ] تنفيذ Stories archive
- [ ] تنفيذ Notes section
- [ ] تحديث dashboard.html (إزالة popup, إضافة navigation)
- [ ] إضافة Alerts badge في Dashboard

### المرحلة 4: Testing
- [ ] اختبار جميع API endpoints
- [ ] اختبار Heatmap على بيانات حقيقية
- [ ] اختبار Popup
- [ ] اختبار Charts
- [ ] اختبار Responsive design
- [ ] اختبار Inactivity alerts

---

## ⚠️ ملاحظات مهمة

1. **Apify Actor**: استخدم `apify/instagram-story-scraper` للستوريات أو Actor مناسب يدعم جلب الستوريات

2. **Rate Limiting**: حافظ على تأخير 3 ثواني بين طلبات الستوريات

3. **Error Handling**: تعامل مع:
   - الحساب خاص (لا يمكن جلب الستوريات)
   - لا توجد ستوريات حالياً
   - فشل تحميل الـ thumbnail

4. **Timezone**: استخدم UTC لجميع التواريخ وحوّل للعرض في الـ Frontend

5. **Thumbnail Size**: اضغط الصور إلى max 100KB قبل الحفظ

6. **Heatmap Performance**: استخدم CSS Grid وتجنب DOM manipulation ثقيل

7. **Charts**: حمّل ApexCharts من CDN:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
   ```

---

## 🚀 ابدأ التنفيذ

ابدأ بالترتيب التالي:
1. أولاً: إنشاء جداول قاعدة البيانات وتشغيل SQL
2. ثانياً: إعداد Supabase Storage
3. ثالثاً: تحديث scraper.py
4. رابعاً: تحديث scheduler.py
5. خامساً: إضافة API endpoints في main.py
6. سادساً: إنشاء client.html
7. سابعاً: تحديث dashboard.html
8. أخيراً: الاختبار الشامل

---

**تاريخ الإنشاء:** 8 ديسمبر 2025
**المشروع:** Alrt AI Enterprise
**الميزة:** Client Analytics & Stories Archive