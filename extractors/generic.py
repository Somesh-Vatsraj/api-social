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

    media_list = []
    seen_urls = set()

    # 1. Process Thumbnail (Photo)
    thumbnail = info.get("thumbnail")
    if thumbnail and thumbnail not in seen_urls:
        seen_urls.add(thumbnail)
        media_list.append({
            "type": "photo",
            "id": f"photo_{info.get('id', '1')}",
            "url": thumbnail,
            "width": info.get("width"),
            "height": info.get("height"),
            "has_audio": False,
            "has_video": False,
            "has_photo": True
        })

    # 2. Process Video and Audio Formats
    for f in info.get("formats", []):
        direct = f.get("url")
        if not direct or direct in seen_urls:
            continue

        acodec = f.get("acodec")
        vcodec = f.get("vcodec")
        height = f.get("height")
        width = f.get("width")
        ext = f.get("ext", "mp4")

        is_video = vcodec and vcodec != "none"
        is_audio = acodec and acodec != "none"

        # Video Entry
        if is_video:
            seen_urls.add(direct)
            media_list.append({
                "type": "video",
                "id": str(f.get("format_id", "101")),
                "url": direct,
                "quality": f"{height}p" if height else "default",
                "container": f"video/{ext}",
                "has_audio": is_audio,
                "has_video": True,
                "has_photo": False,
                "width": width,
                "height": height,
                "fps": f.get("fps"),
                "bitrate": f.get("tbr")
            })

        # Separate Audio-only Entry
        elif is_audio and not is_video:
            seen_urls.add(direct)
            media_list.append({
                "type": "audio",
                "id": str(f.get("format_id", "audio_1")),
                "url": direct,
                "quality": "AUDIO_QUALITY_MEDIUM",
                "container": f"audio/{ext}",
                "has_audio": True,
                "has_video": False,
                "has_photo": False,
                "bitrate": str(f.get("abr") or f.get("tbr") or ""),
                "codecs": acodec
            })

    # Determine overall content type
    content_type = "video" if any(item["type"] == "video" for item in media_list) else "photo"

    return {
        "success": True,
        "type": content_type,
        "username": info.get("uploader_id") or info.get("uploader") or "",
        "profile_image_uri": info.get("uploader_url") or "",
        "caption": info.get("description") or info.get("title") or "",
        "media": media_list
    }
