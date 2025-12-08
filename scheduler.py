import asyncio
import logging
from database import supabase
from scraper import ApifyScraper
from datetime import datetime, timedelta, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapeScheduler:
    def __init__(self):
        # Separate queues for different task types
        self.instagram_queue = asyncio.Queue(maxsize=1000)
        self.ads_queue = asyncio.Queue(maxsize=1000)
        self.stories_queue = asyncio.Queue(maxsize=1000)
        self.scraper = ApifyScraper()
        self.is_running = False
        self.scheduler = AsyncIOScheduler()

        # Configuration - EASY TO ADJUST
        self.INSTAGRAM_WORKERS = 10
        self.ADS_WORKERS = 5
        self.STORIES_WORKERS = 3
        self.INSTAGRAM_DELAY = 2  # seconds between requests per worker
        self.ADS_DELAY = 3
        self.STORIES_DELAY = 5

    async def start(self):
        """Start all workers and scheduler"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("🚀 Starting Scheduler...")

        # Start Instagram workers (10 parallel)
        for i in range(self.INSTAGRAM_WORKERS):
            asyncio.create_task(self.instagram_worker(i))
            logger.info(f"   ✅ Instagram Worker {i+1} started")

        # Start Ads workers (5 parallel)
        for i in range(self.ADS_WORKERS):
            asyncio.create_task(self.ads_worker(i))
            logger.info(f"   ✅ Ads Worker {i+1} started")

        # Start Stories workers (3 parallel)
        for i in range(self.STORIES_WORKERS):
            asyncio.create_task(self.stories_worker(i))
            logger.info(f"   ✅ Stories Worker {i+1} started")

        # Schedule automatic refresh every 12 hours
        self.scheduler.add_job(
            self.refresh_all_targets,
            'interval',
            hours=12,
            id='refresh_all'
        )

        # Schedule stories refresh every 20 hours
        self.scheduler.add_job(
            self.refresh_all_stories,
            'interval',
            hours=20,
            id='refresh_stories'
        )

        # Schedule inactivity alerts check daily at 6 AM
        self.scheduler.add_job(
            self.check_inactivity_alerts,
            'cron',
            hour=6,
            minute=0,
            id='inactivity_alerts'
        )

        # Schedule analytics snapshots daily at 3 AM
        self.scheduler.add_job(
            self.create_daily_analytics,
            'cron',
            hour=3,
            minute=0,
            id='daily_analytics'
        )

        self.scheduler.start()

        logger.info("🚀 Scheduler fully started with 18 workers!")

    async def add_instagram_task(self, client_id: int):
        """
        Add Instagram scraping task by CLIENT ID (not username).
        This prevents collisions when multiple users track same account.
        """
        try:
            # Fetch client from Supabase
            result = supabase.table('clients').select('*').eq('id', client_id).execute()
            if result.data and len(result.data) > 0:
                # Update status to queued
                supabase.table('clients').update(
                    {'last_check_status': 'queued'}
                ).eq('id', client_id).execute()

                await self.instagram_queue.put(client_id)
                logger.info(f"📥 Queued Instagram: client #{client_id}")
        except Exception as e:
            logger.error(f"Error queuing task: {e}")

    async def add_ads_task(self, client_id: int):
        """Add Facebook Ads check task"""
        await self.ads_queue.put(client_id)
        logger.info(f"📥 Queued Ads check: client #{client_id}")

    async def instagram_worker(self, worker_id: int):
        """Worker that processes Instagram scraping tasks"""
        while True:
            try:
                # Wait for task from queue
                client_id = await self.instagram_queue.get()
                logger.info(f"⚙️ Worker {worker_id}: client #{client_id}")

                try:
                    # Fetch client from Supabase
                    result = supabase.table('clients').select('*').eq('id', client_id).execute()

                    if not result.data or len(result.data) == 0:
                        logger.warning(f"Client {client_id} not found")
                        self.instagram_queue.task_done()
                        await asyncio.sleep(self.INSTAGRAM_DELAY)
                        continue

                    client = result.data[0]

                    # Update status to processing
                    supabase.table('clients').update(
                        {'last_check_status': 'processing'}
                    ).eq('id', client_id).execute()

                    # Call Apify scraper
                    scrape_result = await self.scraper.get_profile_data(
                        client['username']
                    )

                    # Update client with results
                    update_data = {}
                    if scrape_result["status"] == "success":
                        data = scrape_result["data"]
                        update_data = {
                            'last_post_date': data["last_post_date"],
                            'days_inactive': int(data["days_inactive"]),
                            'followers_count': int(data["followers_count"]),
                            'avg_posting_interval': int(float(data["avg_posting_interval"])),
                            'status_signal': data["status_signal"],
                            'post_url': data["post_url"],
                            'profile_pic_url': data.get("profile_pic_url"),
                            'last_check_status': 'success',
                            'last_check_date': datetime.utcnow().isoformat(),
                            'last_error_message': None
                        }
                        logger.info(f"✅ Success: @{client['username']}")
                    else:
                        update_data = {
                            'last_check_status': 'failed',
                            'last_error_message': scrape_result.get("message", "Unknown error")
                        }
                        logger.warning(f"❌ Failed: @{client['username']}")

                    supabase.table('clients').update(update_data).eq('id', client_id).execute()

                except Exception as e:
                    logger.error(f"Worker {worker_id} DB Error: {e}")

                self.instagram_queue.task_done()

                # Small delay to avoid rate limits
                await asyncio.sleep(self.INSTAGRAM_DELAY)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} Error: {e}")
                await asyncio.sleep(5)

    async def ads_worker(self, worker_id: int):
        """Worker that processes Facebook Ads checks"""
        while True:
            try:
                client_id = await self.ads_queue.get()
                logger.info(f"📢 Ads Worker {worker_id}: #{client_id}")

                try:
                    # Fetch client from Supabase
                    result = supabase.table('clients').select('*').eq('id', client_id).execute()

                    if not result.data or len(result.data) == 0:
                        self.ads_queue.task_done()
                        await asyncio.sleep(self.ADS_DELAY)
                        continue

                    client = result.data[0]

                    if not client.get('facebook_page_url'):
                        self.ads_queue.task_done()
                        await asyncio.sleep(self.ADS_DELAY)
                        continue

                    # Update status to checking
                    supabase.table('clients').update(
                        {'ads_status': 'CHECKING...'}
                    ).eq('id', client_id).execute()

                    # Call Apify for ads
                    ads_result = await self.scraper.check_facebook_ads(
                        client['facebook_page_url']
                    )

                    ads_count = ads_result.get("count", 0)
                    ads_status = "ACTIVE" if ads_count > 0 else "INACTIVE"

                    supabase.table('clients').update({
                        'ads_count': ads_count,
                        'ads_status': ads_status
                    }).eq('id', client_id).execute()

                    logger.info(f"✅ Ads check done: {ads_count}")

                except Exception as e:
                    logger.error(f"Ads Worker {worker_id} Error: {e}")

                self.ads_queue.task_done()
                await asyncio.sleep(self.ADS_DELAY)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ads Worker {worker_id} Error: {e}")
                await asyncio.sleep(5)

    async def refresh_all_targets(self):
        """Refresh all tracked clients every 12 hours"""
        logger.info("⏰ Starting 12H Global Refresh...")
        try:
            # Fetch all tracked clients from Supabase
            result = supabase.table('clients').select('*').eq('is_tracked', True).execute()
            clients = result.data if result.data else []

            for client in clients:
                await self.add_instagram_task(client['id'])
                if client.get('facebook_page_url'):
                    await self.add_ads_task(client['id'])

            logger.info(f"⏰ Queued {len(clients)} clients for refresh")
        except Exception as e:
            logger.error(f"Refresh error: {e}")

    async def stories_worker(self, worker_id: int):
        """Worker that processes Stories scraping and archiving"""
        while True:
            try:
                client_id = await self.stories_queue.get()
                logger.info(f"📖 Stories Worker {worker_id}: client #{client_id}")

                try:
                    # Fetch client from Supabase
                    result = supabase.table('clients').select('*').eq('id', client_id).execute()

                    if not result.data or len(result.data) == 0:
                        self.stories_queue.task_done()
                        await asyncio.sleep(self.STORIES_DELAY)
                        continue

                    client = result.data[0]

                    # Fetch stories using Apify
                    stories_result = await self.scraper.fetch_instagram_stories(client['username'])

                    if stories_result["status"] == "success":
                        stories = stories_result["stories"]
                        archived_count = 0

                        for story in stories:
                            try:
                                # Check if story already exists
                                existing = supabase.table('stories').select('id').eq(
                                    'client_id', client_id
                                ).eq(
                                    'instagram_story_id', story['instagram_story_id']
                                ).execute()

                                if existing.data and len(existing.data) > 0:
                                    continue  # Skip duplicate

                                # Download and store thumbnail
                                storage_path = None
                                if story.get('thumbnail_url'):
                                    storage_path = await self.scraper.download_and_store_thumbnail(
                                        story['thumbnail_url'],
                                        client_id,
                                        story['instagram_story_id']
                                    )

                                # Insert story to database
                                story_data = {
                                    'client_id': client_id,
                                    'instagram_story_id': story['instagram_story_id'],
                                    'thumbnail_url': story.get('thumbnail_url'),
                                    'thumbnail_storage_path': storage_path,
                                    'story_type': story.get('story_type', 'image'),
                                    'story_url': story.get('story_url'),  # Direct link to story media
                                    'posted_at': story.get('posted_at'),
                                    'expires_at': story.get('expires_at')
                                }

                                supabase.table('stories').insert(story_data).execute()
                                archived_count += 1

                                # Update activity calendar
                                if story.get('posted_at'):
                                    story_date = datetime.fromisoformat(story['posted_at']).date()
                                    self._update_activity_calendar(client_id, story_date, is_story=True)

                            except Exception as e:
                                logger.error(f"Error archiving story: {e}")

                        # Update client stats
                        update_data = {
                            'total_stories_archived': (client.get('total_stories_archived', 0) + archived_count)
                        }

                        if archived_count > 0:
                            update_data['last_story_date'] = datetime.utcnow().isoformat()
                            update_data['stories_inactive_days'] = 0

                        supabase.table('clients').update(update_data).eq('id', client_id).execute()
                        logger.info(f"✅ Archived {archived_count} new stories for @{client['username']}")

                except Exception as e:
                    logger.error(f"Stories Worker {worker_id} Error: {e}")

                self.stories_queue.task_done()
                await asyncio.sleep(self.STORIES_DELAY)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stories Worker {worker_id} Fatal Error: {e}")
                await asyncio.sleep(5)

    async def process_analytics_job(self, client_id: int):
        """Process and save analytics snapshot for a client"""
        try:
            # Fetch client
            result = supabase.table('clients').select('*').eq('id', client_id).execute()
            if not result.data or len(result.data) == 0:
                return

            client = result.data[0]

            # Fetch recent posts (last 20)
            posts_result = await self.scraper.fetch_instagram_posts_detailed(
                client['username'],
                limit=20
            )

            if posts_result["status"] == "success":
                posts = posts_result["posts"]

                # Save posts to database
                new_posts_count = 0
                total_likes = 0
                total_comments = 0

                for post in posts:
                    try:
                        # Check if post already exists
                        existing = supabase.table('posts').select('id').eq(
                            'instagram_post_id', post['instagram_post_id']
                        ).execute()

                        if not existing.data or len(existing.data) == 0:
                            # Insert new post
                            post_data = {
                                'client_id': client_id,
                                'instagram_post_id': post['instagram_post_id'],
                                'post_url': post.get('post_url'),
                                'thumbnail_url': post.get('thumbnail_url'),
                                'likes_count': post.get('likes_count', 0),
                                'comments_count': post.get('comments_count', 0),
                                'caption': post.get('caption'),
                                'hashtags': post.get('hashtags', []),
                                'posted_at': post.get('posted_at')
                            }
                            supabase.table('posts').insert(post_data).execute()
                            new_posts_count += 1

                            # Update activity calendar
                            if post.get('posted_at'):
                                post_date = datetime.fromisoformat(post['posted_at']).date()
                                self._update_activity_calendar(client_id, post_date, is_post=True)

                        total_likes += post.get('likes_count', 0)
                        total_comments += post.get('comments_count', 0)

                    except Exception as e:
                        logger.error(f"Error saving post: {e}")

                # Calculate analytics
                avg_likes = round(total_likes / len(posts), 2) if posts else 0
                avg_comments = round(total_comments / len(posts), 2) if posts else 0
                followers_count = client.get('followers_count', 0)
                engagement_rate = self.scraper.calculate_engagement_rate(
                    avg_likes, avg_comments, followers_count
                )

                # Log analytics for debugging
                logger.info(f"📊 Analytics for @{client['username']}:")
                logger.info(f"   Total posts analyzed: {len(posts)}")
                logger.info(f"   Total likes: {total_likes} (avg: {avg_likes})")
                logger.info(f"   Total comments: {total_comments} (avg: {avg_comments})")
                logger.info(f"   Followers: {followers_count}")
                logger.info(f"   Engagement Rate: {engagement_rate}%")

                # Calculate posts per day
                posts_per_day = 0
                if len(posts) >= 2:
                    first_post = datetime.fromisoformat(posts[0]['posted_at'])
                    last_post = datetime.fromisoformat(posts[-1]['posted_at'])
                    days_diff = (first_post - last_post).days or 1
                    posts_per_day = round(len(posts) / days_diff, 2)

                # Save analytics snapshot
                today = date.today()
                snapshot_data = {
                    'client_id': client_id,
                    'followers_count': followers_count,
                    'following_count': client.get('following_count', 0),
                    'posts_count': len(posts),
                    'avg_likes': avg_likes,
                    'avg_comments': avg_comments,
                    'engagement_rate': engagement_rate,
                    'posts_per_day': posts_per_day,
                    'snapshot_date': str(today)
                }

                # Upsert (update or insert)
                existing_snapshot = supabase.table('analytics_snapshots').select('id').eq(
                    'client_id', client_id
                ).eq(
                    'snapshot_date', str(today)
                ).execute()

                if existing_snapshot.data and len(existing_snapshot.data) > 0:
                    supabase.table('analytics_snapshots').update(snapshot_data).eq(
                        'id', existing_snapshot.data[0]['id']
                    ).execute()
                else:
                    supabase.table('analytics_snapshots').insert(snapshot_data).execute()

                # Update client stats
                supabase.table('clients').update({
                    'total_posts_tracked': client.get('total_posts_tracked', 0) + new_posts_count
                }).eq('id', client_id).execute()

                logger.info(f"✅ Analytics saved for @{client['username']}")

        except Exception as e:
            logger.error(f"Analytics job error for client {client_id}: {e}")

    def _update_activity_calendar(self, client_id: int, activity_date: date, is_story=False, is_post=False):
        """Update activity calendar for a specific date"""
        try:
            # Check if entry exists
            existing = supabase.table('activity_calendar').select('*').eq(
                'client_id', client_id
            ).eq(
                'activity_date', str(activity_date)
            ).execute()

            if existing.data and len(existing.data) > 0:
                # Update existing
                entry = existing.data[0]
                update_data = {
                    'stories_count': entry.get('stories_count', 0) + (1 if is_story else 0),
                    'posts_count': entry.get('posts_count', 0) + (1 if is_post else 0),
                    'has_activity': True
                }
                supabase.table('activity_calendar').update(update_data).eq(
                    'id', entry['id']
                ).execute()
            else:
                # Insert new
                insert_data = {
                    'client_id': client_id,
                    'activity_date': str(activity_date),
                    'stories_count': 1 if is_story else 0,
                    'posts_count': 1 if is_post else 0,
                    'has_activity': True
                }
                supabase.table('activity_calendar').insert(insert_data).execute()

        except Exception as e:
            logger.error(f"Error updating activity calendar: {e}")

    async def check_inactivity_alerts(self):
        """Check all clients for inactivity and create alerts"""
        logger.info("🔔 Checking inactivity alerts...")
        try:
            # Fetch all tracked clients
            result = supabase.table('clients').select('*').eq('is_tracked', True).execute()
            clients = result.data if result.data else []

            for client in clients:
                try:
                    # Calculate days since last story
                    last_story_date = client.get('last_story_date')
                    if last_story_date:
                        last_date = datetime.fromisoformat(last_story_date)
                        days_inactive = (datetime.utcnow() - last_date).days

                        # Update stories_inactive_days
                        supabase.table('clients').update({
                            'stories_inactive_days': days_inactive
                        }).eq('id', client['id']).execute()

                        # Create alert if inactive for 3+ days
                        if days_inactive >= 3:
                            # Check if alert already exists for today
                            today = date.today()
                            existing_alert = supabase.table('inactivity_alerts').select('id').eq(
                                'client_id', client['id']
                            ).eq(
                                'user_id', client['user_id']
                            ).gte(
                                'created_at', str(today)
                            ).execute()

                            if not existing_alert.data or len(existing_alert.data) == 0:
                                # Create new alert
                                alert_data = {
                                    'client_id': client['id'],
                                    'user_id': client['user_id'],
                                    'alert_type': 'STORIES_INACTIVE',
                                    'days_inactive': days_inactive,
                                    'is_read': False,
                                    'is_dismissed': False
                                }
                                supabase.table('inactivity_alerts').insert(alert_data).execute()
                                logger.info(f"🔔 Alert created: @{client['username']} inactive {days_inactive} days")

                except Exception as e:
                    logger.error(f"Error checking client {client['id']}: {e}")

            logger.info("✅ Inactivity alerts check completed")

        except Exception as e:
            logger.error(f"Inactivity alerts error: {e}")

    async def refresh_all_stories(self):
        """Refresh stories for all tracked clients every 20 hours"""
        logger.info("📖 Starting Stories Refresh...")
        try:
            result = supabase.table('clients').select('*').eq('is_tracked', True).execute()
            clients = result.data if result.data else []

            for client in clients:
                await self.stories_queue.put(client['id'])

            logger.info(f"📖 Queued {len(clients)} clients for stories refresh")
        except Exception as e:
            logger.error(f"Stories refresh error: {e}")

    async def create_daily_analytics(self):
        """Create analytics snapshots for all tracked clients"""
        logger.info("📊 Creating daily analytics snapshots...")
        try:
            result = supabase.table('clients').select('*').eq('is_tracked', True).execute()
            clients = result.data if result.data else []

            for client in clients:
                await self.process_analytics_job(client['id'])
                await asyncio.sleep(3)  # Small delay between clients

            logger.info(f"✅ Analytics snapshots created for {len(clients)} clients")
        except Exception as e:
            logger.error(f"Daily analytics error: {e}")

    def get_queue_status(self):
        """Get current queue sizes for monitoring"""
        return {
            "instagram_queue": self.instagram_queue.qsize(),
            "ads_queue": self.ads_queue.qsize(),
            "stories_queue": self.stories_queue.qsize()
        }


# Global instance
scheduler = ScrapeScheduler()
