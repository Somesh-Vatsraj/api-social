import json
import os
import re
import urllib.parse
import urllib.request
import yt_dlp


def resolve_instagram_identity(shortcode: str):
    """
    GraphQL and Web Query Fallback Engine for Instagram.
    Bypasses standard server blocks to extract exact @username & HD avatar.
    """
    username = ""
    profile_image = ""

    # Strategy A: Instagram GraphQL Direct Query
    # Shortcode to Media Hash / GraphQL variables
    gql_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055315a7b28016202db68012643a60&variables={urllib.parse.quote(json.dumps({'shortcode': shortcode}))}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        req = urllib.request.Request(gql_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            media_data = res_data.get("data", {}).get("shortcode_media", {})
            owner = media_data.get("owner", {})
            
            username = owner.get("username", "")
            profile_image = owner.get("profile_pic_url", "")
    except Exception:
        pass

    # Strategy B: Embed Scraper Page Regex Parsing (If GraphQL rate-limited)
    if not username or username.isdigit():
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        try:
            req = urllib.request.Request(embed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode("utf-8")

                # Match Username
                u_match = re.search(r'"username":"([^"]+)"', html) or re.search(r'class="UsernameText"[^>]*>([^<]+)</div>', html)
                if u_match:
                    found_user = u_match.group(1).strip()
                    if not found_user.isdigit():
                        username = found_user

                # Match Profile Pic
                p_match = re.search(r'"profile_pic_url":"([^"]+)"', html) or re.search(r'class="Avatar"[^>]*src="([^"]+)"', html)
                if p_match:
                    profile_image = p_match.group(1).replace("&amp;", "&").replace("\\/", "/")
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
        raise RuntimeError(f"Media extraction failed: {str(exc)}")

    username = (
        info.get("uploader_id")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )
    profile_image_uri = info.get("uploader_avatar") or ""
    caption = info.get("description") or info.get("title") or ""

    # --- Instagram Specific Identity Fix ---
    if platform == "instagram":
        # Extract shortcode from URL
        match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#&]+)", url)
        if match:
            shortcode = match.group(1)
            real_username, real_avatar = resolve_instagram_identity(shortcode)
            
            if real_username:
                username = real_username
            if real_avatar:
                profile_image_uri = real_avatar

    # If yt-dlp/API both fail to find avatar, clean up numeric username fallbacks
    if username.isdigit():
        username = info.get("uploader") or username

    media_list = []
    seen_urls = set()

    # Video extraction logic
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

    # Thumbnail / Cover Image
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

    return {
        "success": True,
        "type": "video" if any(i["type"] == "video" for i in media_list) else "photo",
        "username": username,
        "profile_image_uri": profile_image_uri,
        "caption": caption,
        "media": media_list,
    }
