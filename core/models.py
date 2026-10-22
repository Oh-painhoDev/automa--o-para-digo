from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time

class AccountStatus(str, Enum):
    PENDING = "PENDING"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    EDUCATING = "EDUCATING"
    EDUCATED = "EDUCATED"
    COMMENTING = "COMMENTING"
    UNFOLLOWING = "UNFOLLOWING"
    AUTOLIKING = "AUTOLIKING"
    IDLE = "IDLE"
    RATE_LIMITED = "RATE_LIMITED"
    LOCKED = "LOCKED"
    SUSPENDED = "SUSPENDED"
    DEAD = "DEAD"
    ERROR = "ERROR"

@dataclass
class Account:
    id: int
    auth_token: str
    group: str = "Grupo 1"
    ct0: Optional[str] = None
    username: Optional[str] = None
    proxy: Optional[str] = None
    assigned_link: Optional[str] = None
    status: AccountStatus = AccountStatus.PENDING
    status_detail: str = "Aguardando início"
    likes_count: int = 0
    comments_count: int = 0
    education_likes: int = 0
    unfollowed_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    last_action: str = "Criado"
    last_update_ts: float = field(default_factory=time.time)
    is_alive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group": self.group,
            "auth_token_masked": self.auth_token[:6] + "..." + self.auth_token[-4:] if len(self.auth_token) > 10 else self.auth_token,
            "username": self.username or "Não identificado",
            "proxy": self.proxy or "Sem proxy (Direto)",
            "assigned_link": self.assigned_link or "Nenhum",
            "status": self.status.value,
            "status_detail": self.status_detail,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "education_likes": self.education_likes,
            "unfollowed_count": self.unfollowed_count,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "last_action": self.last_action,
            "is_alive": self.is_alive
        }

@dataclass
class AutomationConfig:
    min_education_likes: int = 3
    max_education_likes: int = 6
    min_action_delay: float = 3.0
    max_action_delay: float = 7.0
    like_probability_min: float = 0.40
    like_probability_max: float = 0.45
    comment_templates: List[str] = field(default_factory=lambda: [
        "Muito interessante isso aqui! {link}",
        "Acompanhando de perto as novidades: {link}",
        "Top demais essa informação! {link}",
        "Confira também essa recomendação: {link}"
    ])
    auto_like_keywords: List[str] = field(default_factory=lambda: [
        "telegram", "crypto", "web3", "ai", "brasil"
    ])
