---
title: Social Downloader
emoji: 📥
colorFrom: cyan
colorTo: blue
sdk: docker
app_port: 7860
---

# Social Downloader

FastAPI-based public-media extraction starter for Hugging Face Spaces.

## Supported platform detection

Instagram, Facebook, TikTok, Threads, YouTube, Pinterest and Moj.

## API

`POST /api/download`

```json
{"url":"https://www.youtube.com/watch?v=EXAMPLE"}
```

The extractor uses `yt-dlp` where supported by the current extractor/runtime. Some platforms or URLs may require a dedicated provider/API or may not be extractable.

Only use this application for public content you own or are authorized to download. Do not use it to bypass authentication, CAPTCHA, DRM, private-content controls, or platform security measures.
