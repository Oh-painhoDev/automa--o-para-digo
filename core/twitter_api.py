import json
import re
import secrets
from typing import Dict, Any, List, Optional, Tuple
import httpx
from core.models import Account, AccountStatus

BEARER_TOKEN = (
    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)

GRAPHQL_QUERY_IDS = {
    "SearchTimeline": "gkjsKepM6gl_HmFW7b5Q8Q",
    "FavoriteTweet": "lI07N6Otwv1PhnEgXILM7A",
    "CreateTweet": "xTflhVy0LgIRzsMix5Meazg",
    "UserTweets": "V7H0Ap3_Hh2FyS75OCDO3Q",
    "HomeTimeline": "W4tWvbmjxioEiQVhi8KUcA",
    "Following": "2v1Vsj94ewCV2L9XG7kSmA",
    "Followers": "k5v6k5B49p3r5iSj493g"
}

class TwitterSession:
    def __init__(self, account: Account, timeout: float = 20.0):
        self.account = account
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> Tuple[bool, str]:
        proxy = self.account.proxy
        
        cookies = {"auth_token": self.account.auth_token}
        if self.account.ct0:
            cookies["ct0"] = self.account.ct0

        headers = {
            "authorization": BEARER_TOKEN,
            "user-agent": DEFAULT_USER_AGENT,
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://x.com",
            "referer": "https://x.com/",
        }

        transport_kwargs = {}
        if proxy:
            transport_kwargs["proxy"] = proxy

        self.client = httpx.AsyncClient(
            cookies=cookies,
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
            **transport_kwargs
        )

        if not self.account.ct0:
            gen_ct0 = secrets.token_hex(16)
            self.client.cookies.set("ct0", gen_ct0, domain=".x.com")
            self.account.ct0 = gen_ct0

        self.client.headers["x-csrf-token"] = self.account.ct0
        return True, "Cliente inicializado com sucesso"

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def verify_credentials(self) -> Tuple[AccountStatus, str, Optional[Dict[str, Any]]]:
        """
        Verifies session health and retrieves account profile data.
        """
        try:
            url = "https://api.x.com/1.1/account/verify_credentials.json"
            resp = await self.client.get(url)
            
            if "ct0" in resp.cookies:
                self.account.ct0 = resp.cookies["ct0"]
                self.client.headers["x-csrf-token"] = self.account.ct0

            if resp.status_code == 200:
                data = resp.json()
                username = data.get("screen_name", "Unknown")
                self.account.username = username
                self.account.followers_count = data.get("followers_count", 0)
                self.account.following_count = data.get("friends_count", 0)
                return AccountStatus.ACTIVE, f"Online (@{username})", data

            if resp.status_code == 401:
                return AccountStatus.DEAD, "Auth token expirado / inválido (401)", None

            if resp.status_code == 403:
                try:
                    err_json = resp.json()
                    errors = err_json.get("errors", [])
                    if any(e.get("code") == 326 for e in errors):
                        return AccountStatus.LOCKED, "Conta bloqueada temporariamente (Código 326)", None
                    if any(e.get("code") == 64 for e in errors):
                        return AccountStatus.SUSPENDED, "Conta suspensa definitivamente (Código 64)", None
                except Exception:
                    pass
                return AccountStatus.LOCKED, "Acesso restrito / Bloqueio de segurança (403)", None

            if resp.status_code == 429:
                return AccountStatus.RATE_LIMITED, "Rate limit atingido (429)", None

            return AccountStatus.ERROR, f"Status HTTP inesperado ({resp.status_code})", None

        except httpx.ProxyError as e:
            return AccountStatus.ERROR, f"Falha de Proxy: {e}", None
        except httpx.ConnectTimeout:
            return AccountStatus.ERROR, "Timeout de conexão (Proxy/X)", None
        except Exception as e:
            return AccountStatus.ERROR, f"Erro inesperado: {str(e)}", None

    async def get_telegram_posts(self, count: int = 15) -> List[str]:
        tweet_ids = []
        search_url = f"https://api.x.com/1.1/search/tweets.json?q=telegram&count={count}&result_type=recent"
        try:
            resp = await self.client.get(search_url)
            if resp.status_code == 200:
                data = resp.json()
                for st in data.get("statuses", []):
                    tid = st.get("id_str")
                    if tid and tid not in tweet_ids:
                        tweet_ids.append(tid)
        except Exception:
            pass

        if not tweet_ids:
            tl_url = f"https://api.x.com/1.1/statuses/user_timeline.json?screen_name=telegram&count={count}"
            try:
                resp = await self.client.get(tl_url)
                if resp.status_code == 200:
                    for st in resp.json():
                        tid = st.get("id_str")
                        if tid and tid not in tweet_ids:
                            tweet_ids.append(tid)
            except Exception:
                pass

        return tweet_ids

    async def like_tweet(self, tweet_id: str) -> Tuple[bool, str]:
        gql_url = f"https://x.com/i/api/graphql/{GRAPHQL_QUERY_IDS['FavoriteTweet']}/FavoriteTweet"
        payload = {
            "variables": {"tweet_id": tweet_id},
            "queryId": GRAPHQL_QUERY_IDS["FavoriteTweet"]
        }
        
        try:
            resp = await self.client.post(gql_url, json=payload)
            if resp.status_code == 200:
                return True, "Curtido (GraphQL)"
            if resp.status_code in (401, 403):
                return False, f"Falha de permissão / Conta caiu ({resp.status_code})"
        except Exception:
            pass

        try:
            rest_url = "https://api.x.com/1.1/favorites/create.json"
            resp = await self.client.post(rest_url, data={"id": tweet_id})
            if resp.status_code == 200 or "already favorited" in resp.text:
                return True, "Curtido (REST)"
            return False, f"Falha REST: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Erro ao curtir: {e}"

    async def get_feed_posts(self, count: int = 20) -> List[str]:
        tweet_ids = []
        try:
            url = f"https://api.x.com/1.1/statuses/home_timeline.json?count={count}"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                for st in resp.json():
                    tid = st.get("id_str")
                    if tid and tid not in tweet_ids:
                        tweet_ids.append(tid)
        except Exception:
            pass

        if not tweet_ids:
            try:
                search_url = f"https://api.x.com/1.1/search/tweets.json?q=noticias OR tech OR brasil&count={count}&result_type=recent"
                resp = await self.client.get(search_url)
                if resp.status_code == 200:
                    for st in resp.json().get("statuses", []):
                        tid = st.get("id_str")
                        if tid and tid not in tweet_ids:
                            tweet_ids.append(tid)
            except Exception:
                pass

        return tweet_ids

    async def reply_tweet(self, tweet_id: str, text: str) -> Tuple[bool, str]:
        gql_url = f"https://x.com/i/api/graphql/{GRAPHQL_QUERY_IDS['CreateTweet']}/CreateTweet"
        payload = {
            "variables": {
                "tweet_text": text,
                "reply": { "in_reply_to_tweet_id": tweet_id },
                "media": { "media_entities": [], "possibly_sensitive": False },
                "semantic_annotation_ids": []
            },
            "features": {
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True
            },
            "queryId": GRAPHQL_QUERY_IDS["CreateTweet"]
        }

        try:
            resp = await self.client.post(gql_url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "errors" not in data:
                    return True, "Comentado (GraphQL)"
            if resp.status_code in (401, 403):
                return False, f"Conta bloqueada ao comentar ({resp.status_code})"
        except Exception:
            pass

        try:
            rest_url = "https://api.x.com/1.1/statuses/update.json"
            form_data = {
                "status": text,
                "in_reply_to_status_id": tweet_id,
                "auto_populate_reply_metadata": "true"
            }
            resp = await self.client.post(rest_url, data=form_data)
            if resp.status_code == 200:
                return True, "Comentado (REST)"
            return False, f"Falha ao comentar: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Erro ao comentar: {e}"

    # Conecta System: Unfollow Non-Followers
    async def get_non_followers(self) -> List[Dict[str, Any]]:
        """
        Fetches following list and followers list, and returns users who don't follow back.
        """
        following = []
        followers = set()

        # Get following
        try:
            url = "https://api.x.com/1.1/friends/list.json?count=200&skip_status=true"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                following = resp.json().get("users", [])
        except Exception:
            pass

        # Get followers IDs
        try:
            url = "https://api.x.com/1.1/followers/ids.json?stringify_ids=true"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                followers = set(resp.json().get("ids", []))
        except Exception:
            pass

        non_followers = []
        for u in following:
            uid = u.get("id_str")
            if uid and uid not in followers:
                non_followers.append({
                    "id": uid,
                    "screen_name": u.get("screen_name"),
                    "name": u.get("name")
                })
        return non_followers

    async def unfollow_user(self, user_id: str) -> Tuple[bool, str]:
        try:
            url = "https://api.x.com/1.1/friendships/destroy.json"
            resp = await self.client.post(url, data={"user_id": user_id})
            if resp.status_code == 200:
                return True, "Deixou de seguir"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)

    # Conecta System: Auto-Liker by Keywords
    async def search_and_like(self, query: str, limit: int = 10) -> int:
        liked_count = 0
        try:
            url = f"https://api.x.com/1.1/search/tweets.json?q={query}&count={limit}&result_type=recent"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                statuses = resp.json().get("statuses", [])
                for st in statuses:
                    tid = st.get("id_str")
                    if tid:
                        ok, _ = await self.like_tweet(tid)
                        if ok:
                            liked_count += 1
                            self.account.likes_count += 1
        except Exception:
            pass
        return liked_count

    # Conecta System: Video Downloader
    async def extract_video_download(self, tweet_id: str) -> List[Dict[str, Any]]:
        results = []
        try:
            url = f"https://api.x.com/1.1/statuses/show.json?id={tweet_id}&tweet_mode=extended"
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                extended = data.get("extended_entities", {})
                for m in extended.get("media", []):
                    variants = m.get("video_info", {}).get("variants", [])
                    for v in variants:
                        if v.get("content_type") == "video/mp4":
                            bitrate = v.get("bitrate", 0)
                            results.append({
                                "bitrate": bitrate,
                                "url": v.get("url")
                            })
                results.sort(key=lambda x: x["bitrate"], reverse=True)
        except Exception:
            pass
        return results
