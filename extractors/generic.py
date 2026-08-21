import json
import os
import re
import urllib.parse
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


def fetch_instagram_profile_info(url: str):
    """
    Directly fetches exact handle (@username) and profile picture URL 
    using Instagram's public embed endpoint.
    """
    username = ""
    profile_image = ""

    # Extract Instagram post/reel shortcode from URL
    match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#&]+)", url)
    if not match:
        return username, profile_image

    shortcode = match.group(1)

    # 1. Primary Attempt: Use Instagram Embed Info Endpoint (Bypasses IP restrictions)
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
    try:
        req = urllib.request.Request(
            embed_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8")

            # Extract handle (@username)
            user_match = re.search(r'class="UsernameText"[^>]*>([^<]+)</div>', html) or \
                         re.search(r'"username":"([^"]+)"', html)
            if user_match:
                username = user_match.group(1).strip()

            # Extract avatar image URI
            avatar_match = re.search(r'class="Avatar"[^>]*src="([^"]+)"', html) or \
                           re.search(r'"profile_pic_url":"([^"]+)"', html) or \
                           re.search(r'class="Square--avatar"[^>]*src="([^"]+)"', html)
            if avatar_match:
                profile_image = avatar_match.group(1).replace("&amp;", "&").replace("\\/", "/")

    except Exception:
        pass

    # 2. Secondary Fallback: GraphQL endpoint if embed scraper is empty
    if not username or not profile_image:
        try:
            gql_url = (
                f"https://www.instagram.com/graphql/query/?doc_id=8833684803378311&variables="
                + urllib.parse.quote(json.dumps({"shortcode": shortcode}))
            )
            req = urllib.request.Request(
                gql_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "X-IG-App-ID": "936619743392459",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                owner = data.get("data", {}).get("xdt_shortcode_media", {}).get("owner", {})
                
                if not username:
                    username = owner.get("username", "")
                if not profile_image:
                    profile_image = owner.get("profile_pic_url", "")
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
            "youtube": {"player_client": ["web", "android"]},
            "instagram": {"get_comments": False},
        },
    }

    cookies_file = os.getenv("COOKIES_FILE") or os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        error = str(exc)
        if "Sign in to confirm" in error or "login" in error.lower():
            raise RuntimeError("Platform blocked request. Configure COOKIES_FILE.")
        raise RuntimeError(f"Media extraction failed: {error}")

    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )
    profile_image_uri = info.get("uploader_avatar") or ""
    caption = info.get("description") or info.get("title") or ""

    # FIX: Override Instagram profile metadata if numerical or empty
    if platform == "instagram":
        real_username, real_avatar = fetch_instagram_profile_info(url)
        
        if real_username:
            username = real_username
        elif username.isdigit() or " " in username:
            username = info.get("uploader_id") or ""

        if real_avatar:
            profile_image_uri = real_avatar

    media_list = []
    seen_urls = set()

    # 1. Primary Video
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

    # 2. Cover Photo / Thumbnail
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

    # 3. Audio Track
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

    return {
        "success": True,
        "type": "video" if any(i["type"] == "video" for i in media_list) else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
