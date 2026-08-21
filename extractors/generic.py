import os
import re
import urllib.request
import yt_dlp

SUPPORTED = {
    "youtube": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "threads": "Threads",
    "pinterest": "Pinterest",
    "moj": "Moj",
}


def get_instagram_meta(url: str):
    """Fallback scraper to get exact handle and profile image from public Instagram metadata."""
    username = ""
    profile_image = ""

    try:
        # Extract username handle directly from URL path (e.g. instagram.com/username/reel/...)
        match = re.search(r"instagram\.com/([^/?#&]+)", url)
        if match and match.group(1) not in ["reel", "p", "reels", "tv", "stories"]:
            username = match.group(1)

        # Request page HTML to grab profile image / user meta tags
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8")

            # Extract profile pic from JSON payload or OpenGraph meta tags
            img_match = (
                re.search(r'"profile_pic_url":"([^"]+)"', html)
                or re.search(r'"profile_pic_url_hd":"([^"]+)"', html)
                or re.search(r'property="og:image"\s+content="([^"]+)"', html)
            )
            if img_match:
                profile_image = img_match.group(1).replace("\\u0026", "&").replace("\\/", "/")

            # Fallback for username if URL didn't contain it
            if not username:
                user_match = re.search(r'"owner":\s*{\s*"username":\s*"([^"]+)"', html)
                if user_match:
                    username = user_match.group(1)

    except Exception:
        pass

    return username, profile_image


def extract_media(url: str, platform: str):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "format": "bestvideo+bestaudio/best",
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
            },
            "instagram": {
                "get_comments": False,
            },
        },
    }

    # Load Cookies file if available (Render / Server environment variable)
    cookies_file = os.getenv("COOKIES_FILE") or os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        error = str(exc)
        if "Sign in to confirm" in error or "not a bot" in error or "login" in error.lower():
            raise RuntimeError(
                "Platform blocked this request. Configure COOKIES_FILE with a valid cookies.txt."
            )
        raise RuntimeError(f"Media extraction failed: {error}")

    # Initial extraction from yt-dlp
    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or info.get("user")
        or ""
    )
    profile_image_uri = info.get("uploader_avatar") or info.get("avatar") or ""
    caption = info.get("description") or info.get("title") or ""

    # Fix: If username is a raw numeric ID, display name, or profile picture is missing (Instagram specific)
    if platform == "instagram" and (
        not profile_image_uri or username.isdigit() or " " in username
    ):
        scraped_user, scraped_avatar = get_instagram_meta(url)

        if scraped_user:
            username = scraped_user
        elif username.isdigit() or " " in username:
            username = info.get("uploader_id") or ""

        if scraped_avatar:
            profile_image_uri = scraped_avatar

    media_list = []
    seen_urls = set()

    # 1. Primary Video extraction
    video_url = info.get("url")
    formats = info.get("formats", [])

    if not video_url or ".jpg" in video_url or ".png" in video_url:
        for f in reversed(formats):
            if f.get("vcodec") != "none" and f.get("url"):
                video_url = f.get("url")
                break

    if video_url and video_url not in seen_urls and ".jpg" not in video_url:
        seen_urls.add(video_url)
        height = info.get("height")
        media_list.append({
            "type": "video",
            "id": str(info.get("id", "101")),
            "url": video_url,
            "quality": f"{height}p" if height else "1080p",
            "container": f"video/{info.get('ext', 'mp4')}",
            "has_audio": True,
            "has_video": True,
            "has_photo": False,
            "width": info.get("width"),
            "height": info.get("height"),
            "fps": info.get("fps"),
            "bitrate": info.get("tbr"),
        })

    # 2. Thumbnail / Cover Photo extraction
    thumbnail = info.get("thumbnail")
    if thumbnail and thumbnail not in seen_urls:
        seen_urls.add(thumbnail)
        media_list.append({
            "type": "photo",
            "id": f"POLARIS_{info.get('id', '100')}",
            "url": thumbnail,
            "width": info.get("width") or 720,
            "height": info.get("height") or 1280,
            "has_audio": False,
            "has_video": False,
            "has_photo": True,
        })

    # 3. Audio extraction
    for f in formats:
        a_url = f.get("url")
        if f.get("vcodec") == "none" and f.get("acodec") != "none" and a_url and a_url not in seen_urls:
            seen_urls.add(a_url)
            media_list.append({
                "type": "audio",
                "id": f"{info.get('id', '101')}audio",
                "url": a_url,
                "quality": "AUDIO_QUALITY_MEDIUM",
                "container": "audio/m4a",
                "has_audio": True,
                "has_video": False,
                "has_photo": False,
                "bitrate": str(f.get("abr") or f.get("tbr") or "64"),
                "codecs": f.get("acodec", "mp4a.40.5"),
            })
            break

    has_video = any(item["type"] == "video" for item in media_list)

    return {
        "success": True,
        "type": "video" if has_video else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
