import impit
from apify_client import ApifyClient
from tikhub import TikHub
from config import APIFY_API_TOKEN, TIKHUB_API_KEY, PROFILE_ACTOR


class TikTokScraper:
    """Scrape TikTok account stats (Apify) and hashtag data (TikHub).

    Args:
        api_token: Apify API token. Falls back to APIFY_API_TOKEN from .env.
        tikhub_key: TikHub API key. Falls back to TIKHUB_API_KEY from .env.
        proxy: Proxy URL (e.g. "http://127.0.0.1:7993"). None = direct connect.
    """

    def __init__(
        self,
        api_token: str | None = None,
        tikhub_key: str | None = None,
        proxy: str | None = None,
    ):
        token = api_token or APIFY_API_TOKEN
        if not token:
            raise ValueError(
                "Apify API token is required. Set APIFY_API_TOKEN in .env "
                "or pass api_token= to the constructor.\n"
                "Get your token at: https://console.apify.com/account#/integrations"
            )

        self.client = ApifyClient(token)
        self._proxy = proxy
        self._tikhub_key = tikhub_key or TIKHUB_API_KEY

        if proxy:
            self.client.http_client.impit_client = impit.Client(
                headers={"Authorization": f"Bearer {token}"},
                proxy=proxy,
                follow_redirects=True,
                timeout=360,
            )

    # ── account ──────────────────────────────────────────────────

    def get_account_stats(self, username: str) -> dict:
        """Fetch follower / like counts for a TikTok account.

        Uses novi/tiktok-user-info-api which accesses TikTok's internal API,
        returning precise (non-rounded) numbers.
        """
        run = self.client.actor(PROFILE_ACTOR).call(
            run_input={"username": username}
        )

        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return {"username": username, "error": "No data returned — account may be private or not exist"}

        data = items[0]
        return {
            "username": username,
            "nickname": data.get("nickname", ""),
            "followers": data.get("follower_count", 0),
            "likes": data.get("total_favorited", 0),
            "following": data.get("following_count", 0),
            "video_count": data.get("aweme_count", 0),
            "verified": bool(data.get("custom_verify", "")),
            "bio": data.get("signature", ""),
            "private": bool(data.get("secret", 0)),
        }

    # ── hashtag (TikHub) ────────────────────────────────────────

    def _get_tikhub(self) -> TikHub:
        if not self._tikhub_key:
            raise ValueError(
                "TikHub API key is required for hashtag data. "
                "Set TIKHUB_API_KEY in .env or pass tikhub_key= to the constructor."
            )
        return TikHub(api_key=self._tikhub_key, proxy=self._proxy)

    def get_hashtag_stats(self, hashtag: str) -> dict:
        """Fetch precise view / video counts for a TikTok hashtag via TikHub.

        Uses tiktok_web.fetch_tag_detail which returns exact statsV2
        (non-rounded viewCount and videoCount) from TikTok's web API.
        """
        tk = self._get_tikhub()
        tag_name = hashtag.strip("#")
        detail = tk.tiktok_web.fetch_tag_detail(tag_name=tag_name)
        data = detail.get("data", detail)
        ch_info = data.get("challengeInfo") or data.get("challenge_info") or {}

        # statsV2 has precise non-rounded values (as strings)
        stats = ch_info.get("statsV2") or ch_info.get("stats") or ch_info.get("challenge", {}).get("stats", {})
        view_count = int(stats.get("viewCount", 0))
        video_count = int(stats.get("videoCount", 0))

        challenge = ch_info.get("challenge", {})
        return {
            "hashtag": hashtag,
            "view_count": view_count,
            "video_count": video_count,
            "ch_id": challenge.get("id", ""),
            "name": challenge.get("title", hashtag),
        }

    # ── bulk ─────────────────────────────────────────────────────

    def get_multiple_accounts(self, usernames: list[str]) -> list[dict]:
        """Fetch stats for multiple accounts. Calls actor per username
        since novi/tiktok-user-info-api queries one user at a time."""
        results = []
        for u in usernames:
            try:
                r = self.get_account_stats(u)
            except Exception as e:
                r = {"username": u, "error": str(e)}
            results.append(r)
        return results

    def get_multiple_hashtags(self, hashtags: list[str]) -> list[dict]:
        """Fetch stats for multiple hashtags via TikHub (one search + detail per tag)."""
        results = []
        for h in hashtags:
            try:
                r = self.get_hashtag_stats(h)
            except Exception as e:
                r = {"hashtag": h, "error": str(e)}
            results.append(r)
        return results
