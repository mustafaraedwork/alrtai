import os
import asyncio
import logging
import httpx
from typing import Dict, Any, List, Optional
from apify_client import ApifyClient
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)


class ApifyScraper:
    def __init__(self):
        token = os.getenv("APIFY_TOKEN")
        if not token:
            raise ValueError("APIFY_TOKEN not found in .env")
        self.client = ApifyClient(token)

        # Configuration
        self.MAX_RETRIES = 3
        self.TIMEOUT = 120  # seconds

        # Supabase client for storage
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            logger.warning("Supabase credentials not found - storage features disabled")
            self.supabase = None

    async def get_profile_data(self, username: str) -> Dict[str, Any]:
        """
        Get Instagram profile data with retry logic and timeout.
        Returns dict with status and data/message.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"📡 Attempt {attempt+1}: @{username}")

                # Run with timeout
                result = await asyncio.wait_for(
                    self._fetch_instagram_profile(username),
                    timeout=self.TIMEOUT
                )
                return result

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Timeout @{username}, attempt {attempt+1}")
                if attempt == self.MAX_RETRIES - 1:
                    return {"status": "error", "message": "Request timeout"}
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"❌ Error @{username}: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    return {"status": "error", "message": str(e)}
                await asyncio.sleep(5)

        return {"status": "error", "message": "Max retries exceeded"}

    async def _fetch_instagram_profile(self, username: str) -> Dict[str, Any]:
        """Internal method - actual Apify call"""

        # Step 1: Get Profile Details (Followers count + Profile Pic)
        followers_count = 0
        profile_pic_url = None
        try:
            profile_input = {
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsLimit": 1,
                "resultsType": "details",
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }

            run_profile = self.client.actor(
                "apify/instagram-scraper"
            ).call(run_input=profile_input, timeout_secs=60)

            if run_profile and "defaultDatasetId" in run_profile:
                profile_items = self.client.dataset(
                    run_profile["defaultDatasetId"]
                ).list_items().items
                if profile_items:
                    followers_count = profile_items[0].get("followersCount", 0)
                    profile_pic_url = profile_items[0].get("profilePicUrl") or profile_items[0].get("profilePicUrlHD")
                    logger.info(f"   👤 Followers: {followers_count}")
                    if profile_pic_url:
                        logger.info(f"   🖼️ Profile pic: {profile_pic_url[:50]}...")
        except Exception as e:
            logger.warning(f"   ⚠️ Profile details error: {e}")

        # Step 2: Get Posts
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsLimit": 12,
            "resultsType": "posts",
            "searchType": "hashtag",
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        run = self.client.actor("apify/instagram-scraper").call(
            run_input=run_input,
            timeout_secs=90
        )

        dataset_items = self.client.dataset(
            run["defaultDatasetId"]
        ).list_items().items

        if not dataset_items:
            if followers_count > 0:
                return {
                    "status": "error",
                    "message": "Profile found but no posts"
                }
            return {
                "status": "error",
                "message": "No data (private/empty profile)"
            }

        # Parse Posts Dates
        valid_posts = []
        for item in dataset_items:
            ts = item.get("timestamp") or item.get("takenAt")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    valid_posts.append({
                        "date": dt,
                        "url": item.get("url") or
                               f"https://instagram.com/p/{item.get('shortCode')}",
                        "is_pinned": item.get("isPinned", False)
                    })
                except:
                    continue

        if not valid_posts:
            return {"status": "warning", "message": "Could not parse dates"}

        # Sort DESC (Newest First)
        valid_posts.sort(key=lambda x: x["date"], reverse=True)

        latest_post = valid_posts[0]
        post_date = latest_post["date"]
        current_date = datetime.now(timezone.utc)
        days_inactive = (current_date - post_date).days

        # Calculate Average Interval
        avg_interval = 0
        if len(valid_posts) > 1:
            intervals = []
            max_i = min(len(valid_posts) - 1, 10)
            for i in range(max_i):
                diff = (valid_posts[i]["date"] - valid_posts[i+1]["date"]).days
                intervals.append(diff)
            if intervals:
                avg_interval = sum(intervals) / len(intervals)

        # Status Signal Logic
        signal = "RED"  # Default: Active
        threshold = max(avg_interval + 2, 5)

        if days_inactive > threshold:
            signal = "YELLOW"
        if days_inactive > 14:
            signal = "GREEN"

        return {
            "status": "success",
            "data": {
                "last_post_date": str(post_date.date()),
                "days_inactive": days_inactive,
                "followers_count": followers_count,
                "avg_posting_interval": round(avg_interval, 1),
                "status_signal": signal,
                "post_url": latest_post["url"],
                "profile_pic_url": profile_pic_url
            }
        }

    async def check_facebook_ads(self, fb_url: str) -> Dict[str, Any]:
        """Check Facebook Ads Library with retry"""
        for attempt in range(self.MAX_RETRIES):
            try:
                input_url = fb_url.replace(
                    "web.facebook.com", "www.facebook.com"
                )

                run_input = {
                    "urls": [{"url": input_url}],
                    "resultsLimit": 10,
                    "proxy": {"useApifyProxy": True}
                }

                run = self.client.actor(
                    "curious_coder/facebook-ads-library-scraper"
                ).call(run_input=run_input, timeout_secs=self.TIMEOUT)

                if not run:
                    return {"count": 0, "status": "error"}

                items = self.client.dataset(
                    run["defaultDatasetId"]
                ).list_items().items

                valid_count = len([
                    i for i in items
                    if "ADS_NOT_FOUND" not in str(i)
                ])

                return {"count": valid_count, "status": "success"}

            except Exception as e:
                logger.error(f"Ads check error: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    return {"count": 0, "status": "error", "message": str(e)}
                await asyncio.sleep(3)

        return {"count": 0, "status": "error"}

    async def fetch_instagram_stories(self, username: str) -> Dict[str, Any]:
        """
        Fetch Instagram stories using specialized Instagram Stories Downloader.
        Returns dict with status and list of REAL ACTIVE stories (last 24 hours).

        Uses: datavoyantlab/instagram-story-downloader
        - Only fetches public stories from the last 24 hours
        - No login/cookies required
        - Returns thumbnail URLs (no need to download full media)
        """
        try:
            logger.info(f"📖 Fetching ACTIVE stories for @{username} (specialized scraper)")

            run_input = {
                "usernames": [username],
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }

            run = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.actor("datavoyantlab/instagram-story-downloader").call,
                    run_input=run_input,
                    timeout_secs=120
                ),
                timeout=self.TIMEOUT
            )

            if not run or "defaultDatasetId" not in run:
                logger.warning(f"   ⚠️ No dataset returned for @{username}")
                return {"status": "success", "message": "No active stories", "stories": []}

            items = self.client.dataset(run["defaultDatasetId"]).list_items().items

            if not items:
                logger.info(f"   ℹ️ No active stories for @{username}")
                return {"status": "success", "message": "No active stories", "stories": []}

            # Parse stories from specialized scraper
            stories = []
            for item in items:
                # Extract data from specialized scraper output
                story_id = item.get("storyID")
                thumbnail = item.get("thumbnail")
                timestamp = item.get("timestamp")
                media_type = item.get("mediaType", "image")
                story_url = item.get("link")

                if not story_id or not thumbnail:
                    continue

                # Convert Unix timestamp to ISO format
                posted_at = None
                expires_at = None
                if timestamp:
                    try:
                        dt = datetime.fromtimestamp(timestamp)
                        posted_at = dt.isoformat()
                        # Stories expire after 24 hours
                        expires_dt = dt + timedelta(hours=24)
                        expires_at = expires_dt.isoformat()
                    except Exception as e:
                        logger.warning(f"   ⚠️ Timestamp parse error: {e}")

                story_data = {
                    "instagram_story_id": story_id,
                    "thumbnail_url": thumbnail,
                    "story_url": story_url,
                    "story_type": media_type,
                    "posted_at": posted_at,
                    "expires_at": expires_at
                }

                stories.append(story_data)

            logger.info(f"   ✅ Found {len(stories)} ACTIVE stories")
            return {"status": "success", "stories": stories}

        except asyncio.TimeoutError:
            logger.error(f"   ⏱️ Timeout fetching stories for @{username}")
            return {"status": "error", "message": "Request timeout", "stories": []}
        except Exception as e:
            logger.error(f"   ❌ Error fetching stories: {e}")
            return {"status": "error", "message": str(e), "stories": []}

    async def _fetch_instagram_stories_OLD_DEPRECATED(self, username: str) -> Dict[str, Any]:
        """
        OLD DEPRECATED CODE - Apify no longer supports real Instagram Stories.
        This code is kept for reference only.
        """
        try:
            run_input = {
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsLimit": 50,
                "resultsType": "stories",
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }

            run = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.actor("apify/instagram-scraper").call,
                    run_input=run_input,
                    timeout_secs=90
                ),
                timeout=self.TIMEOUT
            )

            if not run or "defaultDatasetId" not in run:
                return {"status": "error", "message": "No dataset returned", "stories": []}

            items = self.client.dataset(run["defaultDatasetId"]).list_items().items

            if not items:
                logger.info(f"   ℹ️ No stories found for @{username}")
                return {"status": "success", "message": "No active stories", "stories": []}

            # Parse stories
            stories = []
            for item in items:
                story_data = {
                    "instagram_story_id": item.get("id") or item.get("pk"),
                    "thumbnail_url": item.get("displayUrl") or item.get("imageUrl"),
                    "story_type": "video" if item.get("isVideo") else "image",
                    "posted_at": None,
                    "expires_at": None
                }

                # Parse timestamp
                ts = item.get("timestamp") or item.get("takenAt")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        story_data["posted_at"] = dt.isoformat()
                        # Stories expire after 24 hours
                        expires_dt = dt.replace(hour=dt.hour+24)
                        story_data["expires_at"] = expires_dt.isoformat()
                    except Exception as e:
                        logger.warning(f"   ⚠️ Date parse error: {e}")

                if story_data["instagram_story_id"] and story_data["thumbnail_url"]:
                    stories.append(story_data)

            logger.info(f"   ✅ Found {len(stories)} stories")
            return {"status": "success", "stories": stories}

        except asyncio.TimeoutError:
            logger.error(f"   ⏱️ Timeout fetching stories for @{username}")
            return {"status": "error", "message": "Request timeout", "stories": []}
        except Exception as e:
            logger.error(f"   ❌ Error fetching stories: {e}")
            return {"status": "error", "message": str(e), "stories": []}

    async def fetch_instagram_posts_detailed(self, username: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch Instagram posts with full details (likes, comments, captions).
        Returns dict with status and list of posts.
        """
        try:
            logger.info(f"📄 Fetching {limit} posts for @{username}")

            run_input = {
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsLimit": limit,
                "resultsType": "posts",
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }

            run = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.actor("apify/instagram-scraper").call,
                    run_input=run_input,
                    timeout_secs=120
                ),
                timeout=self.TIMEOUT
            )

            if not run or "defaultDatasetId" not in run:
                return {"status": "error", "message": "No dataset returned", "posts": []}

            items = self.client.dataset(run["defaultDatasetId"]).list_items().items

            if not items:
                return {"status": "success", "message": "No posts found", "posts": []}

            # Parse posts
            posts = []
            for item in items:
                post_data = {
                    "instagram_post_id": item.get("id") or item.get("shortCode"),
                    "post_url": item.get("url") or f"https://instagram.com/p/{item.get('shortCode')}",
                    "thumbnail_url": item.get("displayUrl") or item.get("imageUrl"),
                    "likes_count": item.get("likesCount", 0),
                    "comments_count": item.get("commentsCount", 0),
                    "caption": item.get("caption", ""),
                    "hashtags": [],
                    "posted_at": None
                }

                # Extract hashtags from caption
                if post_data["caption"]:
                    hashtags = [word for word in post_data["caption"].split() if word.startswith("#")]
                    post_data["hashtags"] = hashtags[:10]  # Limit to 10

                # Parse timestamp
                ts = item.get("timestamp") or item.get("takenAt")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        post_data["posted_at"] = dt.isoformat()
                    except Exception as e:
                        logger.warning(f"   ⚠️ Date parse error: {e}")

                if post_data["instagram_post_id"]:
                    posts.append(post_data)

            logger.info(f"   ✅ Found {len(posts)} posts")
            return {"status": "success", "posts": posts}

        except asyncio.TimeoutError:
            logger.error(f"   ⏱️ Timeout fetching posts for @{username}")
            return {"status": "error", "message": "Request timeout", "posts": []}
        except Exception as e:
            logger.error(f"   ❌ Error fetching posts: {e}")
            return {"status": "error", "message": str(e), "posts": []}

    async def download_and_store_thumbnail(
        self,
        url: str,
        client_id: int,
        story_id: str
    ) -> Optional[str]:
        """
        Download thumbnail image and store in Supabase Storage.
        Returns storage path or None if failed.
        """
        if not self.supabase:
            logger.warning("Supabase not configured - skipping thumbnail storage")
            return None

        try:
            # Download image
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.get(url)
                response.raise_for_status()
                image_data = response.content

            # Generate unique filename
            file_extension = "jpg"
            if "png" in url.lower():
                file_extension = "png"
            filename = f"{client_id}/{story_id}.{file_extension}"

            # Upload to Supabase Storage
            result = self.supabase.storage.from_("story-thumbnails").upload(
                path=filename,
                file=image_data,
                file_options={"content-type": f"image/{file_extension}"}
            )

            if result:
                logger.info(f"   💾 Stored thumbnail: {filename}")
                return filename
            else:
                logger.error(f"   ❌ Failed to store thumbnail: {filename}")
                return None

        except Exception as e:
            logger.error(f"   ❌ Error storing thumbnail: {e}")
            return None

    def calculate_engagement_rate(
        self,
        likes: float,
        comments: float,
        followers: int
    ) -> float:
        """
        Calculate engagement rate: ((likes + comments) / followers) * 100
        Returns percentage rounded to 2 decimals.
        """
        if followers == 0:
            return 0.0

        total_engagement = likes + comments
        rate = (total_engagement / followers) * 100
        return round(rate, 2)
