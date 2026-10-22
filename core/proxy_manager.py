from typing import Optional
from urllib.parse import quote


def _proxy_url(username: str, password: str, host: str, port: str) -> str:
    """Build a proxy URL while escaping URL characters in credentials."""
    user = quote(username.strip(), safe="")
    secret = quote(password.strip(), safe="")
    return f"http://{user}:{secret}@{host.strip()}:{port.strip()}"


def normalize_proxy(proxy_str: str) -> Optional[str]:
    """
    Normalize proxy input to the URL format accepted by httpx:
    - host:port
    - host:port:user:password
    - host:port@user:password
    - user:password@host:port
    - URLs that already include a scheme
    """
    if not proxy_str or not proxy_str.strip():
        return None

    raw = proxy_str.strip()

    if "://" in raw:
        return raw

    # Accept both host:port@user:password and user:password@host:port.
    if "@" in raw:
        left, right = raw.split("@", 1)
        if ":" in left and ":" in right:
            left_first, left_second = left.split(":", 1)
            right_first, right_second = right.split(":", 1)

            # host:port@user:password
            if left_second.isdigit():
                return _proxy_url(right_first, right_second, left_first, left_second)

            # user:password@host:port
            if right_second.isdigit():
                return _proxy_url(left_first, left_second, right_first, right_second)

        return f"http://{raw}"

    # Split only three times so passwords containing ':' remain intact.
    parts = raw.split(":", 3)
    if len(parts) == 4:
        host, port, username, password = parts
        return _proxy_url(username, password, host, port)

    if len(parts) == 2:
        host, port = parts
        return f"http://{host.strip()}:{port.strip()}"

    return f"http://{raw}"
