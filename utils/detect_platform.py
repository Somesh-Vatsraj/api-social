from urllib.parse import urlparse

DOMAINS = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "fb.watch": "facebook",
    "tiktok.com": "tiktok",
    "threads.net": "threads",
    "pinterest.com": "pinterest",
    "pin.it": "pinterest",
    "mojapp.in": "moj",
}

def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]

    for domain, platform in DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return platform
    return "unknown"
