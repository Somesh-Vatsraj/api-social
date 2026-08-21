const form = document.getElementById("form");
const urlInput = document.getElementById("url");
const result = document.getElementById("result");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  result.classList.remove("hidden");
  result.innerHTML = "<p>Extracting media...</p>";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput.value.trim() }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Extraction failed");

    // Header info: Username & Caption
    let html = `<h2>${escapeHtml(data.username || "Media User")}</h2>`;
    if (data.caption) {
      html += `<p style="opacity: 0.8; font-size: 0.9em; margin-bottom: 15px;">${escapeHtml(data.caption)}</p>`;
    }

    if (data.media && Array.isArray(data.media) && data.media.length > 0) {
      
      // 1. Filter and Render Videos
      const videos = data.media.filter((item) => item.type === "video");
      if (videos.length) {
        html += "<h3>Videos</h3>";
        for (const v of videos) {
          const resText = v.quality || (v.height ? `${v.height}p` : "1080p");
          html += `<div class="item" style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span>${escapeHtml(resText)} · MP4</span>
            <a href="${safeUrl(v.url)}" target="_blank" rel="noopener" download>Download Video</a>
          </div>`;
        }
      }

      // 2. Filter and Render Dedicated Audio (if present)
      const audios = data.media.filter((item) => item.type === "audio");
      if (audios.length) {
        html += "<h3>Audio</h3>";
        for (const a of audios) {
          html += `<div class="item" style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span>${escapeHtml(a.quality || "Audio Track")}</span>
            <a href="${safeUrl(a.url)}" target="_blank" rel="noopener" download>Download Audio</a>
          </div>`;
        }
      }

      // 3. Filter and Render Cover Photos / Thumbnails
      const photos = data.media.filter((item) => item.type === "photo");
      if (photos.length) {
        html += "<h3>Thumbnail / Photo</h3>";
        for (const img of photos) {
          html += `<div style="margin-top: 10px;">
            <img class="thumb" src="${safeUrl(img.url)}" alt="Thumbnail" loading="lazy" style="max-width: 100%; height: auto; border-radius: 8px; margin-bottom: 5px;">
            <div class="item" style="display: flex; justify-content: space-between; align-items: center;">
              <span>Cover Image (${img.width || 1920}x${img.height || 1440})</span>
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
    result.innerHTML = `<p><strong>Error:</strong> ${escapeHtml(err.message)}</p>`;
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function safeUrl(s) {
  try {
    const u = new URL(s);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "#";
  } catch {
    return "#";
  }
}
