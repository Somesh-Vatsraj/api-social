import json
import os
import re
import urllib.parse
import urllib.request
import yt_dlp

# Fallback Official Logos for platforms when user avatar is blocked
PLATFORM_LOGOS = {
    "instagram": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/2048px-Instagram_logo_2016.svg.png",
    "facebook": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Facebook_Logo_%282019%29.png/1024px-Facebook_Logo_%282019%29.png",
    "youtube": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/1024px-YouTube_full-color_icon_%282017%29.svg.png",
    "tiktok": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/TikTok_logo.svg/1024px-TikTok_logo.svg.png",
    "threads": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Threads_%28app%29_logo.svg/1024px-Threads_%28app%29_logo.svg.png",
    "pinterest": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Pinterest-logo.org.svg/1024px-Pinterest-logo.org.svg.png",
}

def get_instagram_profile_avatar(url: str):
    """Fetches and cleans Instagram avatar link."""
    match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#&]+)", url)
    if not match:
        return ""

    shortcode = match.group(1)
    
    # Try OEmbed API
    try:
        oembed_url = f"https://api.instagram.com/oembed/?url=https://www.instagram.com/p/{shortcode}/"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("thumbnail_url"):
                return data["thumbnail_url"]
    except Exception:
        pass

    # Fallback to Embed HTML parsing
    try:
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        req = urllib.request.Request(embed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8")
            m = (
                re.search(r'"profile_pic_url":"([^"]+)"', html) or
                re.search(r'class="Avatar"[^>]*src="([^"]+)"', html)
            )
            if m and m.group(1):
                return m.group(1).replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&")
    except Exception:
        pass

    return ""


def extract_media(url: str, platform: str):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "format": "bestvideo+bestaudio/best",
        "extractor_args": {
            "youtube": {"player_client": ["web", "android"]},
            "instagram": {"get_comments": False},
            "facebook": {"get_comments": False},
        },
    }

    cookies_file = os.getenv("COOKIES_FILE") or os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Media extraction failed: {str(exc)}")

    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )
    profile_image_uri = info.get("uploader_avatar") or ""
    caption = info.get("description") or info.get("title") or ""

    # Instagram Profile Avatar Attempt
    if platform == "instagram":
        avatar = get_instagram_profile_avatar(url)
        if avatar:
            profile_image_uri = avatar

    # Fix numeric username fallback
    if username.isdigit() and info.get("uploader"):
        username = info.get("uploader")

    # FIX 1: Platform Logo Fallback if avatar is empty/blocked
    if not profile_image_uri or profile_image_uri.strip() == "":
        profile_image_uri = PLATFORM_LOGOS.get(platform.lower(), "")

    media_list = []
    seen_urls = set()

    # 1. Main Video Format
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

    # 2. Cover / Thumbnail Photo
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

    # FIX 2: Audio Stream Extraction (Robust for Facebook, Instagram & YouTube)
    for f in formats:
        a_url = f.get("url")
        # Matches audio-only formats or Facebook DASH audio tracks
        is_audio_only = (f.get("vcodec") == "none" or f.get("vcodec") is None) and f.get("acodec") not in (None, "none")
        
        if is_audio_only and a_url and a_url not in seen_urls:
            seen_urls.add(a_url)
            media_list.append({
                "type": "audio",
                "id": f"{info.get('id', '101')}audio",
                "url": a_url,
                "quality": "AUDIO_QUALITY_MEDIUM",
                "container": f"audio/{f.get('ext', 'm4a')}",
                "has_audio": True,
                "has_video": False,
                "has_photo": False,
                "bitrate": str(f.get("abr") or f.get("tbr") or "128"),
                "codecs": f.get("acodec", "mp4a.40.2"),
            })
            break  # Direct best audio added

    return {
        "success": True,
        "type": "video" if any(i["type"] == "video" for i in media_list) else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
