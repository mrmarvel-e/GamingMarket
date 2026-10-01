self.addEventListener("push", event => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(self.registration.showNotification(data.title || "GamingMarket", {
    body: data.body || "You have a new GamingMarket notification.",
    icon: "/static/icons/favicon.svg",
    data: {url: data.url || "/"}
  }));
});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url || "/";
  event.waitUntil(clients.matchAll({type:"window", includeUncontrolled:true}).then(list=>{
    for(const client of list){ if("focus" in client){ client.navigate(url); return client.focus(); } }
    return clients.openWindow(url);
  }));
});