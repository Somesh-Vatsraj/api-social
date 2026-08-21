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
    # yt-dlp supports many public media URLs. Platform-specific adapters
    # can be added later when a provider requires custom handling.
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    videos = []
    audio = None
    images = []

    for f in info.get("formats", []):
        direct = f.get("url")
        if not direct:
            continue

        ext = f.get("ext")
        height = f.get("height")
        acodec = f.get("acodec")
        vcodec = f.get("vcodec")

        if vcodec and vcodec != "none":
            quality = f"{height}p" if height else "video"
            videos.append({
                "quality": quality,
                "ext": ext or "mp4",
                "download_url": direct
            })

        if acodec and acodec != "none" and (not vcodec or vcodec == "none"):
            if audio is None:
                audio = {
                    "ext": ext or "m4a",
                    "download_url": direct
                }

    thumbnail = info.get("thumbnail")
    if thumbnail:
        images.append(thumbnail)

    # Remove duplicate video entries by quality/ext/url.
    unique = []
    seen = set()
    for item in videos:
        key = (item["quality"], item["ext"], item["download_url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return {
        "success": True,
        "platform": SUPPORTED.get(platform, platform.title()),
        "title": info.get("title") or "Untitled",
        "media": {
            "videos": unique,
            "audio": audio,
            "images": images
        }
    }
