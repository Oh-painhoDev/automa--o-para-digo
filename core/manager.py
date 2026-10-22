import asyncio
import random
import time
import csv
import io
import json
from typing import List, Dict, Any, Optional
from core.models import Account, AccountStatus, AutomationConfig
from core.twitter_api import TwitterSession
from core.proxy_manager import normalize_proxy

class AutomationManager:
    def __init__(self):
        self.accounts: List[Account] = []
        self.proxies: List[str] = []
        self.links: List[str] = []
        self.config = AutomationConfig()
        
        self.is_running = False
        self._tasks: List[asyncio.Task] = []
        self._event_subscribers: List[asyncio.Queue] = []
        self.logs: List[Dict[str, Any]] = []

    async def subscribe_events(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._event_subscribers.append(q)
        return q

    def unsubscribe_events(self, q: asyncio.Queue):
        if q in self._event_subscribers:
            self._event_subscribers.remove(q)

    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        timestamp = time.strftime("%H:%M:%S")
        event = {
            "type": event_type,
            "timestamp": timestamp,
            "data": data
        }
        
        self.logs.append(event)
        if len(self.logs) > 250:
            self.logs.pop(0)

        for q in list(self._event_subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass

    def import_data(self, raw_tokens: str, raw_proxies: str, raw_links: str, raw_comments: Optional[str] = None):
        token_entries = []
        group_number = 1
        group_has_tokens = False
        for raw_line in raw_tokens.splitlines():
            line = raw_line.strip()
            if not line:
                if group_has_tokens:
                    group_number += 1
                    group_has_tokens = False
                continue
            if line.startswith("#"):
                continue
            token_entries.append((line, f"Grupo {group_number}"))
            group_has_tokens = True

        proxy_lines = [line.strip() for line in raw_proxies.strip().splitlines() if line.strip()]
        link_lines = [line.strip() for line in raw_links.strip().splitlines() if line.strip()]

        if raw_comments and raw_comments.strip():
            cmts = [line.strip() for line in raw_comments.strip().splitlines() if line.strip()]
            if cmts:
                self.config.comment_templates = cmts

        self.accounts.clear()
        self.proxies = proxy_lines
        self.links = link_lines

        for idx, (line, group_name) in enumerate(token_entries):
            token = line
            ct0 = None
            if ":" in line:
                parts = line.split(":")
                if len(parts) == 3:
                    token = parts[2]
                elif len(parts) == 2:
                    token, ct0 = parts[0], parts[1]

            assigned_proxy = None
            if idx < len(proxy_lines):
                assigned_proxy = normalize_proxy(proxy_lines[idx])

            assigned_link = None
            if idx < len(link_lines):
                assigned_link = link_lines[idx]

            acc = Account(
                id=idx + 1,
                auth_token=token,
                group=group_name,
                ct0=ct0,
                proxy=assigned_proxy,
                assigned_link=assigned_link,
                status=AccountStatus.PENDING,
                status_detail="Configurado e pronto"
            )
            self.accounts.append(acc)

    def update_proxies(self, raw_proxies: str) -> int:
        """Apply one normalized proxy per already imported account."""
        proxy_lines = [line.strip() for line in raw_proxies.splitlines() if line.strip()]
        self.proxies = proxy_lines

        for index, account in enumerate(self.accounts):
            account.proxy = normalize_proxy(proxy_lines[index]) if index < len(proxy_lines) else None

        return len(proxy_lines)

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.accounts)
        active = sum(1 for a in self.accounts if a.status in (AccountStatus.ACTIVE, AccountStatus.EDUCATING, AccountStatus.EDUCATED, AccountStatus.COMMENTING, AccountStatus.UNFOLLOWING, AccountStatus.AUTOLIKING))
        fallen = sum(1 for a in self.accounts if a.status in (AccountStatus.DEAD, AccountStatus.LOCKED, AccountStatus.SUSPENDED))
        educated = sum(1 for a in self.accounts if a.status == AccountStatus.EDUCATED or a.education_likes > 0)
        total_likes = sum(a.likes_count for a in self.accounts)
        total_comments = sum(a.comments_count for a in self.accounts)
        total_unfollows = sum(a.unfollowed_count for a in self.accounts)

        return {
            "total_accounts": total,
            "active_accounts": active,
            "fallen_accounts": fallen,
            "educated_accounts": educated,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_unfollows": total_unfollows,
            "is_running": self.is_running,
            "accounts": [a.to_dict() for a in self.accounts]
        }

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._tasks.clear()

        await self.emit_event("SYSTEM", {"message": f"Iniciando automação principal para {len(self.accounts)} contas."})

        for acc in self.accounts:
            t = asyncio.create_task(self._run_account_pipeline(acc))
            self._tasks.append(t)

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()

        for acc in self.accounts:
            if acc.is_alive and acc.status not in (AccountStatus.DEAD, AccountStatus.SUSPENDED, AccountStatus.LOCKED):
                acc.status = AccountStatus.IDLE
                acc.status_detail = "Interrompido pelo operador"

        await self.emit_event("SYSTEM", {"message": "Operação pausada."})

    async def _trigger_account_death_alert(self, account: Account, reason: str, status: AccountStatus):
        account.status = status
        account.status_detail = reason
        account.is_alive = False
        
        await self.emit_event("ACCOUNT_FALLEN", {
            "id": account.id,
            "username": account.username or f"Conta #{account.id}",
            "status": status.value,
            "reason": reason,
            "proxy": account.proxy
        })

    async def _run_account_pipeline(self, account: Account):
        session = TwitterSession(account)
        try:
            account.status = AccountStatus.INITIALIZING
            account.status_detail = "Iniciando sessão e proxy..."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            ok, msg = await session.initialize()
            if not ok:
                await self._trigger_account_death_alert(account, msg, AccountStatus.ERROR)
                return

            # Verify credentials & load profile metrics
            status, detail, user_data = await session.verify_credentials()
            if status in (AccountStatus.DEAD, AccountStatus.LOCKED, AccountStatus.SUSPENDED):
                await self._trigger_account_death_alert(account, detail, status)
                return
            elif status != AccountStatus.ACTIVE:
                account.status = status
                account.status_detail = detail
                await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
                return

            account.status = AccountStatus.ACTIVE
            account.status_detail = f"Online (@{account.username} - {account.followers_count} seg)"
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            # Phase 1: Educar Contas (Telegram)
            account.status = AccountStatus.EDUCATING
            account.status_detail = "Educando conta (Buscando página Telegram)..."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            telegram_posts = await session.get_telegram_posts(count=15)
            if telegram_posts:
                target_likes = random.randint(self.config.min_education_likes, min(self.config.max_education_likes, len(telegram_posts)))
                liked_in_edu = 0

                for post_id in telegram_posts[:target_likes]:
                    if not self.is_running:
                        break

                    liked, like_msg = await session.like_tweet(post_id)
                    if liked:
                        account.likes_count += 1
                        account.education_likes += 1
                        liked_in_edu += 1
                        account.last_action = f"Curtiu post Telegram ({post_id})"
                        account.status_detail = f"Educando: {liked_in_edu}/{target_likes} posts curtidos"
                        await self.emit_event("ACTION_LIKE", {
                            "account_id": account.id,
                            "username": account.username,
                            "target": "telegram",
                            "post_id": post_id
                        })
                    else:
                        if "Conta caiu" in like_msg or "bloqueada" in like_msg:
                            await self._trigger_account_death_alert(account, like_msg, AccountStatus.LOCKED)
                            return

                    delay = random.uniform(self.config.min_action_delay, self.config.max_action_delay)
                    await asyncio.sleep(delay)

                account.status = AccountStatus.EDUCATED
                account.status_detail = f"Conta educada ({account.education_likes} curtidas no Telegram)"
                await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            await asyncio.sleep(random.uniform(3.0, 5.0))

            # Phase 2: Feed Commenting & 40-45% like ratio
            account.status = AccountStatus.COMMENTING
            account.status_detail = "Comentando no feed com link atribuído..."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            while self.is_running and account.is_alive:
                feed_posts = await session.get_feed_posts(count=10)
                if not feed_posts:
                    account.status_detail = "Feed vazio ou aguardando timeline. Aguardando 10s..."
                    await asyncio.sleep(10)
                    continue

                for post_id in feed_posts:
                    if not self.is_running:
                        break

                    template = random.choice(self.config.comment_templates)
                    link_to_use = account.assigned_link or "https://t.me"
                    comment_text = template.replace("{link}", link_to_use)

                    replied, reply_msg = await session.reply_tweet(post_id, comment_text)
                    if replied:
                        account.comments_count += 1
                        account.last_action = f"Comentou no post {post_id}"
                        account.status_detail = f"Comentários: {account.comments_count} | Curtidas: {account.likes_count}"
                        
                        await self.emit_event("ACTION_COMMENT", {
                            "account_id": account.id,
                            "username": account.username,
                            "post_id": post_id,
                            "comment": comment_text,
                            "link": link_to_use
                        })

                        # 40-45% ratio like
                        target_prob = random.uniform(self.config.like_probability_min, self.config.like_probability_max)
                        if random.random() <= target_prob:
                            await asyncio.sleep(random.uniform(1.5, 3.0))
                            liked, _ = await session.like_tweet(post_id)
                            if liked:
                                account.likes_count += 1
                                await self.emit_event("ACTION_LIKE", {
                                    "account_id": account.id,
                                    "username": account.username,
                                    "target": "feed_post",
                                    "post_id": post_id,
                                    "reason": "40-45% ratio like"
                                })

                        await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
                    else:
                        if "Conta bloqueada" in reply_msg or "permissão" in reply_msg:
                            await self._trigger_account_death_alert(account, reply_msg, AccountStatus.LOCKED)
                            return

                    delay = random.uniform(self.config.min_action_delay * 2, self.config.max_action_delay * 3)
                    await asyncio.sleep(delay)

                await asyncio.sleep(random.uniform(15.0, 30.0))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            account.status = AccountStatus.ERROR
            account.status_detail = f"Erro no worker: {str(e)}"
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
        finally:
            await session.close()

    # Batch Action: Unfollow Non-Followers
    async def run_unfollow_non_followers_batch(self):
        await self.emit_event("SYSTEM", {"message": "Iniciando remoção em massa de quem não segue de volta..."})
        for acc in self.accounts:
            if not acc.is_alive:
                continue
            asyncio.create_task(self._unfollow_worker(acc))

    async def _unfollow_worker(self, account: Account):
        session = TwitterSession(account)
        try:
            await session.initialize()
            account.status = AccountStatus.UNFOLLOWING
            account.status_detail = "Verificando quem não segue de volta..."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            non_followers = await session.get_non_followers()
            account.status_detail = f"Encontrados {len(non_followers)} perfis que não seguem de volta."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            for target in non_followers[:30]: # safety batch cap
                ok, msg = await session.unfollow_user(target["id"])
                if ok:
                    account.unfollowed_count += 1
                    account.last_action = f"Deixou de seguir @{target['screen_name']}"
                    await self.emit_event("SYSTEM", {
                        "message": f"@{account.username} deixou de seguir @{target['screen_name']}"
                    })
                    await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
                await asyncio.sleep(random.uniform(2.0, 4.0))

            account.status = AccountStatus.IDLE
            account.status_detail = f"Unfollow concluído ({account.unfollowed_count} removidos)"
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
        except Exception as e:
            account.status_detail = f"Erro unfollow: {e}"
        finally:
            await session.close()

    # Batch Action: Auto-Liker by Keywords
    async def run_auto_liker_batch(self, keywords: List[str], count_per_account: int = 15):
        query = " OR ".join(keywords) if keywords else "telegram OR crypto OR ai"
        await self.emit_event("SYSTEM", {"message": f"Ativando Curtidor Automático para '{query}'..."})
        for acc in self.accounts:
            if not acc.is_alive:
                continue
            asyncio.create_task(self._auto_liker_worker(acc, query, count_per_account))

    async def _auto_liker_worker(self, account: Account, query: str, limit: int):
        session = TwitterSession(account)
        try:
            await session.initialize()
            account.status = AccountStatus.AUTOLIKING
            account.status_detail = f"Curtindo posts por palavra-chave..."
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())

            liked = await session.search_and_like(query, limit)
            account.status = AccountStatus.IDLE
            account.status_detail = f"Auto-Liker finalizado (+{liked} curtidas)"
            await self.emit_event("ACCOUNT_UPDATE", account.to_dict())
        finally:
            await session.close()

    # Video Downloader helper
    async def get_video_stream(self, tweet_id_or_url: str) -> List[Dict[str, Any]]:
        tweet_id = tweet_id_or_url
        if "status/" in tweet_id_or_url:
            tweet_id = tweet_id_or_url.split("status/")[1].split("?")[0].split("/")[0]

        # Use first active account or throwaway session
        acc = self.accounts[0] if self.accounts else Account(id=0, auth_token="")
        session = TwitterSession(acc)
        await session.initialize()
        try:
            return await session.extract_video_download(tweet_id)
        finally:
            await session.close()

    def export_accounts_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Group", "Username", "Status", "Proxy", "Assigned Link", "Likes", "Comments", "Unfollows", "Followers", "Following"])
        for a in self.accounts:
            writer.writerow([
                a.id, a.group, a.username or "Unknown", a.status.value, a.proxy or "", a.assigned_link or "",
                a.likes_count, a.comments_count, a.unfollowed_count, a.followers_count, a.following_count
            ])
        return output.getvalue()
