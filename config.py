import os
from dotenv import load_dotenv

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
TIKHUB_API_KEY = os.getenv("TIKHUB_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
PROXY_URL = os.getenv("PROXY_URL", "")

# Apify actor ID for account stats
PROFILE_ACTOR = "novi/tiktok-user-info-api"

# Hashtag data is fetched via TikHub (tiktok_app_v3.fetch_hashtag_search_result)

TRACKING_ACCOUNTS = [
    "heartopia_en",
    "heartopia_th",
    "heartopia_jp",
    "heartopia_tw",
]

TRACKING_HASHTAGS = [
    "heartopia",
    "heartopiagame",
]

CSV_FILE = "tracking_data.csv"
HASHTAG_CSV_FILE = "tracking_hashtags.csv"
