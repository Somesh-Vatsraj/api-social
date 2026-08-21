import os
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
        },
    }

    # Pass cookies for both YouTube and Instagram
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
                "Platform blocked this request. Configure COOKIES_FILE with valid cookies.txt."
            )
        raise RuntimeError(f"Media extraction failed: {error}")

    # Username resolution with Instagram specific fallbacks
    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or info.get("user")
        or ""
    )

    # If yt-dlp returns a raw numeric ID for Instagram, clear or sanitize it
    if platform == "instagram" and username.isdigit():
        username = info.get("uploader") or ""

    caption = info.get("description") or info.get("title") or ""
    profile_image_uri = info.get("uploader_avatar") or info.get("avatar") or ""

    media_list = []
    seen_urls = set()

    # 1. Video extraction (Primary)
    video_url = info.get("url")
    formats = info.get("formats", [])

    # Find the best video format directly if info['url'] is missing or points to an image
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

    # 2. Thumbnail / Photo extraction
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
    audio_url = None
    audio_codec = "mp4a.40.5"
    audio_bitrate = "64"

    for f in formats:
        if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url"):
            audio_url = f.get("url")
            audio_codec = f.get("acodec", audio_codec)
            audio_bitrate = str(f.get("abr") or f.get("tbr") or "64")
            break

    if audio_url and audio_url not in seen_urls:
        seen_urls.add(audio_url)
        media_list.append({
            "type": "audio",
            "id": f"{info.get('id', '101')}audio",
            "url": audio_url,
            "quality": "AUDIO_QUALITY_MEDIUM",
            "container": "audio/m4a",
            "has_audio": True,
            "has_video": False,
            "has_photo": False,
            "bitrate": audio_bitrate,
            "codecs": audio_codec,
        })

    has_video = any(item["type"] == "video" for item in media_list)

    return {
        "success": True,
        "type": "video" if has_video else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
