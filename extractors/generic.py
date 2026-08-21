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

        # Prefer formats that can be directly played/downloaded.
        "format": "bestvideo+bestaudio/best",

        # Avoid unnecessary playlist/channel extraction.
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
            }
        },
    }

    # Optional YouTube cookies.
    # Set YOUTUBE_COOKIES_FILE in Render environment variables
    # to the path of a valid cookies.txt file.
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")

    if platform == "youtube" and cookies_file:
        if os.path.isfile(cookies_file):
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

        # Video formats
        if vcodec and vcodec != "none":
            quality = f"{height}p" if height else "video"

            videos.append({
                "quality": quality,
                "ext": ext or "mp4",
                "download_url": direct,
            })

        # Audio-only formats
        if (
            acodec
            and acodec != "none"
            and (not vcodec or vcodec == "none")
        ):
            if audio is None:
                audio = {
                    "ext": ext or "m4a",
                    "download_url": direct,
                }

    thumbnail = info.get("thumbnail")

    if thumbnail:
        images.append(thumbnail)

    # Remove duplicates
    unique = []
    seen = set()

    for item in videos:
        key = (
            item["quality"],
            item["ext"],
            item["download_url"],
        )

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
            "images": images,
        },
    }