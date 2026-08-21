const form=document.getElementById("form");
const urlInput=document.getElementById("url");
const result=document.getElementById("result");

form.addEventListener("submit", async (e)=>{
  e.preventDefault();
  result.classList.remove("hidden");
  result.innerHTML="<p>Extracting media...</p>";

  try{
    const res=await fetch("/api/download",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({url:urlInput.value.trim()})
    });
    const data=await res.json();
    if(!res.ok) throw new Error(data.detail || data.error || "Extraction failed");

    let html=`<h2>${escapeHtml(data.title)}</h2><p>${escapeHtml(data.platform)}</p>`;

    if(data.media?.videos?.length){
      html+="<h3>Videos</h3>";
      for(const v of data.media.videos){
        html+=`<div class="item"><span>${escapeHtml(v.quality)} · ${escapeHtml(v.ext)}</span><a href="${safeUrl(v.download_url)}" target="_blank" rel="noopener">Download</a></div>`;
      }
    }

    if(data.media?.audio){
      const a=data.media.audio;
      html+=`<h3>Audio</h3><div class="item"><span>${escapeHtml(a.ext)}</span><a href="${safeUrl(a.download_url)}" target="_blank" rel="noopener">Download</a></div>`;
    }

    if(data.media?.images?.length){
      html+="<h3>Images</h3>";
      for(const image of data.media.images){
        html+=`<img class="thumb" src="${safeUrl(image)}" alt="Media thumbnail" loading="lazy"><div class="item"><span>Image</span><a href="${safeUrl(image)}" target="_blank" rel="noopener">Open</a></div>`;
      }
    }

    result.innerHTML=html;
  }catch(err){
    result.innerHTML=`<p><strong>Error:</strong> ${escapeHtml(err.message)}</p>`;
  }
});

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function safeUrl(s){
  try{
    const u=new URL(s);
    return ["http:","https:"].includes(u.protocol) ? u.href : "#";
  }catch{return "#"}
}
