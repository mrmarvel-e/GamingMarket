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
})();