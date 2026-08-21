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
            "youtube": {
                "player_client": ["web", "android"],
            }
        },
    }

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if platform == "youtube" and cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        error = str(exc)
        if "Sign in to confirm" in error or "not a bot" in error:
            raise RuntimeError(
                "YouTube is blocking this server request. "
                "Configure YOUTUBE_COOKIES_FILE with a valid cookies.txt file."
            )
        raise RuntimeError(f"Media extraction failed: {error}")

    # Fallbacks for username/channel name
    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )

    # Caption extraction
    caption = info.get("description") or info.get("title") or ""

    # Profile Image fallback (yt-dlp rarely provides user avatars, uses thumbnail if unavailable)
    profile_image_uri = info.get("uploader_avatar") or ""

    media_list = []
    seen_urls = set()

    # 1. Process Thumbnail as "photo"
    thumbnail = info.get("thumbnail")
    if thumbnail and thumbnail not in seen_urls:
        seen_urls.add(thumbnail)
        media_list.append({
            "type": "photo",
            "id": f"POLARIS_{info.get('id', '100')}",
            "url": thumbnail,
            "width": info.get("width") or 640,
            "height": info.get("height") or 1136,
            "has_audio": False,
            "has_video": False,
            "has_photo": True
        })

    # 2. Extract best combined Video and Audio sources
    best_video_url = info.get("url")
    if best_video_url and best_video_url not in seen_urls:
        seen_urls.add(best_video_url)
        
        height = info.get("height")
        quality_str = f"{height}p" if height else "1080p"

        media_list.append({
            "type": "video",
            "id": str(info.get("id", "101")),
            "url": best_video_url,
            "quality": quality_str,
            "container": f"video/{info.get('ext', 'mp4')}",
            "has_audio": True,
            "has_video": True,
            "has_photo": False,
            "width": info.get("width"),
            "height": info.get("height"),
            "fps": info.get("fps"),
            "bitrate": info.get("tbr")
        })

    # 3. Separate Audio item
    requested_formats = info.get("requested_formats") or []
    audio_format = None

    for f in requested_formats:
        if f.get("vcodec") == "none" and f.get("acodec") != "none":
            audio_format = f
            break

    if audio_format and audio_format.get("url") not in seen_urls:
        a_url = audio_format.get("url")
        seen_urls.add(a_url)
        media_list.append({
            "type": "audio",
            "id": f"{info.get('id', '101')}audio",
            "url": a_url,
            "quality": "AUDIO_QUALITY_MEDIUM",
            "container": f"audio/{audio_format.get('ext', 'mp4')}",
            "has_audio": True,
            "has_video": False,
            "has_photo": False,
            "bitrate": str(audio_format.get("abr") or audio_format.get("tbr") or "66702"),
            "codecs": audio_format.get("acodec") or "mp4a.40.5"
        })

    return {
        "success": True,
        "type": "video" if any(m["type"] == "video" for m in media_list) else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
