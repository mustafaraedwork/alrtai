"""
اختبار سريع للميزات الجديدة
شغّل هذا السكريبت بعد إضافة client جديد لجلب البيانات فوراً
"""
import asyncio
from scheduler import scheduler

async def test_new_features(client_id: int):
    """اختبر جميع الميزات لـ client معين"""
    print(f"\n🧪 Testing features for client #{client_id}...\n")

    # 1. جلب Stories
    print("📖 Step 1: Fetching stories...")
    await scheduler.stories_queue.put(client_id)
    await asyncio.sleep(2)  # انتظر قليلاً لبدء المعالجة
    print("   ✅ Stories job queued\n")

    # 2. جلب Analytics
    print("📊 Step 2: Processing analytics...")
    await scheduler.process_analytics_job(client_id)
    print("   ✅ Analytics processed\n")

    print("🎉 Done! Now check the client page (📊 button) to see results\n")

if __name__ == "__main__":
    # استبدل 37 بـ ID الخاص بالـ client الجديد
    client_id = int(input("Enter client ID: "))
    asyncio.run(test_new_features(client_id))
