
import os
import asyncio
from typing import Dict, Any
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

class ApifyScraper:
    def __init__(self):
        token = os.getenv("APIFY_TOKEN")
        if not token:
            print("❌ Error: APIFY_TOKEN not found in .env")
        self.client = ApifyClient(token)

    async def get_profile_data(self, username: str) -> Dict[str, Any]:
        """
        Calls Apify Actor `apify/instagram-scraper` to get latest posts + profile info.
        Calculates: Last Post Date, Avg Interval, Followers.
        """
        print(f"📡 Apify: Requesting data for @{username}...")
        
        # Step 1: Get Profile Details (Followers count)
        followers_count = 0
        try:
            # Use directUrls for details too, it's more reliable with this actor
            profile_input = {
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsLimit": 1,
                "resultsType": "details", # Explicitly ask for profile details
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }
            # Add timeout to prevent hanging
            run_profile = self.client.actor("apify/instagram-scraper").call(run_input=profile_input)
            
            # Check for dataset
            if run_profile and "defaultDatasetId" in run_profile:
                profile_items = self.client.dataset(run_profile["defaultDatasetId"]).list_items().items
                if profile_items:
                    # Structure: item['followersCount']
                    followers_count = profile_items[0].get("followersCount", 0)
                    print(f"   👤 Followers: {followers_count}")
        except Exception as e:
            print(f"   ⚠️ Could not fetch profile details: {e}")

        # Step 2: Get Posts (Dates)
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsLimit": 12, # Fetch top 12 to calculate average over ~10 intervals
            "resultsType": "posts",
            "searchType": "hashtag",
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        try:
            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)
            dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items
            
            if not dataset_items:
                if followers_count > 0:
                     return {"status": "error", "message": "Found profile but no posts returned."}
                return {"status": "error", "message": "No data returned (Profile private/empty)."}

            # Parse Posts Dates
            from datetime import datetime, timezone
            
            valid_posts = []

            for item in dataset_items:
                ts = item.get("timestamp") or item.get("takenAt")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        valid_posts.append({
                            "date": dt,
                            "url": item.get("url") or f"https://instagram.com/p/{item.get('shortCode')}",
                            "is_pinned": item.get("isPinned", False)
                        })
                    except:
                        continue
            
            if not valid_posts:
                return {"status": "warning", "message": "Could not parse dates."}
            
            # Sort DESC (Newest First)
            valid_posts.sort(key=lambda x: x["date"], reverse=True)
            
            latest_post = valid_posts[0]
            post_date = latest_post["date"]
            current_date = datetime.now(timezone.utc)
            days_inactive = (current_date - post_date).days

            # --- Calculate Average Interval ---
            avg_interval = 0
            if len(valid_posts) > 1:
                intervals = []
                # limit to latest 10 gaps (so we need 11 posts)
                max_i = min(len(valid_posts)-1, 10)
                
                for i in range(max_i):
                    diff = (valid_posts[i]["date"] - valid_posts[i+1]["date"]).days
                    intervals.append(diff)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)

            # --- V2 Status Logic ---
            signal = "RED" # Default: Active / Normal
            threshold = max(avg_interval + 2, 5) # At least 5 days allowance
            
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
                    "post_url": latest_post["url"]
                }
            }

        except Exception as e:
            print(f"❌ Apify Error: {e}")
            return {"status": "error", "message": str(e)}
