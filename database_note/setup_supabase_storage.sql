-- =====================================================
-- Alrt AI - Supabase Storage Setup
-- Storage Policies for story-thumbnails bucket
-- تاريخ: 8 ديسمبر 2025
-- =====================================================

-- ملاحظة: إنشاء الـ Bucket يتم من Dashboard، وليس من SQL
-- اذهب إلى: Storage > Create new bucket > story-thumbnails

-- =====================================================
-- 1. Policy: السماح بالقراءة للجميع (Public Read)
-- =====================================================
CREATE POLICY "Public read access for story thumbnails"
ON storage.objects FOR SELECT
USING (bucket_id = 'story-thumbnails');

-- =====================================================
-- 2. Policy: السماح بالكتابة للمستخدمين المسجلين فقط
-- =====================================================
CREATE POLICY "Authenticated users can upload story thumbnails"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'story-thumbnails');

-- =====================================================
-- 3. Policy: السماح بالتحديث للمستخدمين المسجلين فقط
-- =====================================================
CREATE POLICY "Authenticated users can update story thumbnails"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'story-thumbnails')
WITH CHECK (bucket_id = 'story-thumbnails');

-- =====================================================
-- 4. Policy: السماح بالحذف للمستخدمين المسجلين فقط
-- =====================================================
CREATE POLICY "Authenticated users can delete story thumbnails"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'story-thumbnails');

-- =====================================================
-- التحقق من الـ Policies
-- =====================================================
SELECT schemaname, tablename, policyname, roles, qual, with_check
FROM pg_policies
WHERE tablename = 'objects'
AND policyname LIKE '%story%'
ORDER BY policyname;
