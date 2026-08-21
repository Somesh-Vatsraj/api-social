const form = document.getElementById("form");
const urlInput = document.getElementById("url");
const result = document.getElementById("result");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  if (!result || !urlInput) return;
  
  result.classList.remove("hidden");
  result.innerHTML = "<p>Extracting media...</p>";

  const inputUrl = urlInput.value ? urlInput.value.trim() : "";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: inputUrl }),
    });

    const data = await res.json().catch(() => ({}));

    // FIXED: Strong Error Handling - Formats Object/Array error messages safely
    if (!res.ok) {
      let errorMsg = "Extraction failed";
      
      if (typeof data.detail === "string") {
        errorMsg = data.detail;
      } else if (typeof data.detail === "object" && data.detail !== null) {
        errorMsg = JSON.stringify(data.detail);
      } else if (typeof data.error === "string") {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
    }

    // Header info: Username & Caption (Safe Fallbacks)
    const username = data.username || "Media User";
    let html = `<h2>${escapeHtml(username)}</h2>`;
    
    if (data.caption) {
      html += `<p style="opacity: 0.8; font-size: 0.9em; margin-bottom: 15px;">${escapeHtml(data.caption)}</p>`;
    }

    const mediaList = Array.isArray(data.media) ? data.media : [];

    if (mediaList.length > 0) {
      
      // 1. Filter and Render Videos
      const videos = mediaList.filter((item) => item && item.type === "video");
      if (videos.length) {
        html += "<h3>Videos</h3>";
        for (const v of videos) {
          if (!v.url) continue;
          const resText = v.quality || (v.height ? `${v.height}p` : "1080p");
          html += `<div class="item" style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span>${escapeHtml(resText)} · MP4</span>
            <a href="${safeUrl(v.url)}" target="_blank" rel="noopener" download>Download Video</a>
          </div>`;
        }
      }

      // 2. Filter and Render Dedicated Audio
      const audios = mediaList.filter((item) => item && item.type === "audio");
      if (audios.length) {
        html += "<h3>Audio</h3>";
        for (const a of audios) {
          if (!a.url) continue;
          html += `<div class="item" style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span>${escapeHtml(a.quality || "Audio Track")}</span>
            <a href="${safeUrl(a.url)}" target="_blank" rel="noopener" download>Download Audio</a>
          </div>`;
        }
      }

      // 3. Filter and Render Cover Photos / Thumbnails
      const photos = mediaList.filter((item) => item && item.type === "photo");
      if (photos.length) {
        html += "<h3>Thumbnail / Photo</h3>";
        for (const img of photos) {
          if (!img.url) continue;
          const width = img.width || 1920;
          const height = img.height || 1440;
          html += `<div style="margin-top: 10px;">
            <img class="thumb" src="${safeUrl(img.url)}" alt="Thumbnail" loading="lazy" style="max-width: 100%; height: auto; border-radius: 8px; margin-bottom: 5px;">
            <div class="item" style="display: flex; justify-content: space-between; align-items: center;">
              <span>Cover Image (${width}x${height})</span>
              <a href="${safeUrl(img.url)}" target="_blank" rel="noopener" download>View Image</a>
            </div>
          </div>`;
        }
      }

    } else {
      html += "<p>No downloadable media found.</p>";
    }

    result.innerHTML = html;

  } catch (err) {
    const safeError = err && err.message ? err.message : "An unexpected error occurred";
    result.innerHTML = `<p><strong>Error:</strong> ${escapeHtml(safeError)}</p>`;
  }
});

// FIXED: String conversion safeguard prevents "undefined" output
function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  const str = typeof s === "string" ? s : String(s);
  return str.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

// FIXED: URL Validation safeguard
function safeUrl(s) {
  if (!s || typeof s !== "string") return "#";
  try {
    const u = new URL(s);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "#";
  } catch {
    return "#";
  }
}
