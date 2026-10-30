(function(){
  const vapid = window.GM_VAPID_PUBLIC_KEY;
  if (!vapid || !("serviceWorker" in navigator) || !("PushManager" in window)) return;
  async function init(){
    try{
      const reg = await navigator.serviceWorker.register("/static/sw.js");
      if(Notification.permission === "default"){
        const permission = await Notification.requestPermission();
        if(permission !== "granted") return;
      }
      if(Notification.permission !== "granted") return;
      let sub = await reg.pushManager.getSubscription();
      if(!sub) sub = await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:urlBase64ToUint8Array(vapid)});
      await fetch("/api/push/subscribe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(sub.toJSON())});
    }catch(e){console.debug("Push setup unavailable",e)}
  }
  function urlBase64ToUint8Array(base64String){
    const padding = "=".repeat((4-base64String.length%4)%4);
    const raw = atob((base64String+padding).replace(/-/g,"+").replace(/_/g,"/"));
    return Uint8Array.from([...raw].map(c=>c.charCodeAt(0)));
  }
  init();

  // Sharing uses the browser's native share sheet when available.
  document.addEventListener("click", async function(event){
    const shareButton = event.target.closest("[data-share-button]");
    if(shareButton){
      const title = shareButton.dataset.shareTitle || "GamingMarket";
      const text = shareButton.dataset.shareText || "Discover GamingMarket!";
      const url = shareButton.dataset.shareUrl || window.location.href;
      if(navigator.share){
        try{
          await navigator.share({title, text, url});
          return;
        }catch(error){
          if(error && error.name === "AbortError") return;
        }
      }
      const message = `${text} ${url}`;
      window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
      return;
    }

    const copyButton = event.target.closest("[data-copy-share-url]");
    if(copyButton){
      const url = copyButton.dataset.copyShareUrl || window.location.href;
      const originalText = copyButton.textContent;
      try{
        if(navigator.clipboard && window.isSecureContext){
          await navigator.clipboard.writeText(url);
        }else{
          const field = document.createElement("textarea");
          field.value = url;
          field.setAttribute("readonly", "");
          field.style.position = "absolute";
          field.style.left = "-9999px";
          document.body.appendChild(field);
          field.select();
          const copied = document.execCommand("copy");
          field.remove();
          if(!copied) throw new Error("Clipboard unavailable");
        }
        copyButton.textContent = "Copied!";
      }catch(error){
        window.prompt("Copy this GamingMarket link:", url);
      }
      window.setTimeout(() => { copyButton.textContent = originalText; }, 1800);
    }
  });
})();
